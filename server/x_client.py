"""
X (Twitter) data fetcher — concurrent, cached, rate-limited.

Optimization summary vs. original serial implementation:
  - Concurrent fetch via asyncio.Semaphore (CONCURRENCY=5)
  - Persistent user-ID + metadata cache → skips get_user_by_screen_name on warm runs
  - Per-request jitter replaces hard sleep(0.8) between all users
  - Exponential backoff + jitter on rate-limit / transient errors
  - Per-run stats: p50/p95 latency, success rate, 429 count, cache hit rate

Expected speedup:
  First run  (cold cache): ~5x  (serial ~220s → ~44s for 100 users)
  Warm runs  (hot  cache): ~8x  (skip 100 user-lookup calls → ~25s)
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from twikit import Client as TwikitClient
    TWIKIT_OK = True
except ImportError:
    TWIKIT_OK = False

COOKIES_FILE   = Path(__file__).parent / "x_cookies.json"
_DATA_DIR      = Path(__file__).parent / "data"
UID_CACHE_FILE = _DATA_DIR / "uid_cache.json"
TWEET_DATE_FMT = "%a %b %d %H:%M:%S %z %Y"

# ── Tuning knobs (change here only) ──────────────────────────────────────────
CONCURRENCY   = 5     # simultaneous user fetches; raise carefully (rate-limit risk)
REQ_JITTER    = 0.10  # base jitter (seconds) per HTTP call; keeps total spread 0.05-0.15s
REQ_TIMEOUT   = 15.0  # seconds before a single twikit call is cancelled
MAX_RETRIES   = 3     # per-user retry attempts on transient/rate errors
BASE_BACKOFF  = 2.0   # first retry wait (seconds)
MAX_BACKOFF   = 60.0  # cap on any single backoff


# ── Per-run metrics ───────────────────────────────────────────────────────────
@dataclass
class FetchStats:
    total: int        = 0
    success: int      = 0
    empty: int        = 0
    rate_limited: int = 0
    failed: int       = 0
    cache_hits: int   = 0
    latencies_ms: list[float] = field(default_factory=list)
    _wall_start: float = field(default_factory=time.perf_counter)

    def _ptile(self, pct: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return s[max(0, int(len(s) * pct) - 1)]

    def log(self) -> None:
        wall = time.perf_counter() - self._wall_start
        sr   = self.success / max(self.total, 1) * 100
        print(
            f"[Fetch] ── Stats ──────────────────────────────────\n"
            f"[Fetch]   wall={wall:.1f}s  users={self.total}  "
            f"success={self.success}({sr:.0f}%)  empty={self.empty}\n"
            f"[Fetch]   p50={self._ptile(.50):.0f}ms  "
            f"p95={self._ptile(.95):.0f}ms  "
            f"p99={self._ptile(.99):.0f}ms\n"
            f"[Fetch]   rate_limit_hits={self.rate_limited}  "
            f"hard_failures={self.failed}  "
            f"uid_cache_hits={self.cache_hits}\n"
            f"[Fetch] ───────────────────────────────────────────"
        )


# ── Client ────────────────────────────────────────────────────────────────────
class XClientError(Exception):
    pass


class XClient:
    def __init__(self) -> None:
        if not TWIKIT_OK:
            raise XClientError("twikit not installed. Run: pip install twikit")
        self._client    = TwikitClient("en-US")
        self._ready     = False
        self._uid_cache = self._load_uid_cache()

    # ── Authentication ────────────────────────────────────────────────────────
    async def connect(self) -> None:
        auth_token = os.getenv("X_AUTH_TOKEN", "").strip()
        ct0        = os.getenv("X_CT0",        "").strip()
        username   = os.getenv("X_USERNAME",   "").strip()
        email      = os.getenv("X_EMAIL", username).strip()
        password   = os.getenv("X_PASSWORD",   "").strip()

        # Method A: Browser cookies (no password needed)
        if auth_token and ct0:
            print("[X] Authenticating with browser cookies…")
            import json as _json
            COOKIES_FILE.write_text(_json.dumps({"auth_token": auth_token, "ct0": ct0}), "utf-8")
            self._client.load_cookies(str(COOKIES_FILE))
            self._ready = True
            print("[X] Cookie auth OK.")
            return

        # Method B: Load saved session
        if COOKIES_FILE.exists():
            try:
                self._client.load_cookies(str(COOKIES_FILE))
                self._ready = True
                print("[X] Loaded saved session.")
                return
            except Exception:
                print("[X] Session expired, re-logging in…")

        # Method C: Username + password
        if not username or not password:
            raise XClientError(
                "Fill in server/.env:\n"
                "  Option A (recommended): X_AUTH_TOKEN + X_CT0\n"
                "  Option B: X_USERNAME + X_PASSWORD"
            )
        print(f"[X] Logging in as @{username}…")
        await self._client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
        self._client.save_cookies(str(COOKIES_FILE))
        self._ready = True
        print("[X] Login OK, session saved.")

    # ── Public fetch entry point ──────────────────────────────────────────────
    async def fetch_recent_tweets(
        self,
        usernames: list[str],
        hours: int       = 24,
        max_per_user: int = 20,
        delay: float     = 0.0,        # legacy param; ignored
        progress_cb      = None,       # optional callable(done: int, total: int)
    ) -> dict[str, list[dict]]:
        """
        Fetch tweets posted within the last `hours` hours for every username.

        Runs up to CONCURRENCY=5 users simultaneously.
        User IDs are cached to disk — second run skips get_user_by_screen_name
        entirely, cutting ~30% off wall time.

        Returns {username: [tweet_dict, ...]}
        """
        if not self._ready:
            raise XClientError("Call connect() first.")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stats  = FetchStats()
        sem    = asyncio.Semaphore(CONCURRENCY)
        done   = [0]   # mutable counter; asyncio is single-threaded → no lock needed
        total  = len(usernames)

        print(
            f"[Fetch] Starting: {total} users, concurrency={CONCURRENCY}, "
            f"uid_cache={len(self._uid_cache)} entries"
        )
        t_start = time.perf_counter()

        tasks = [
            self._fetch_one(u, cutoff, max_per_user, sem, stats, done, total, progress_cb)
            for u in usernames
        ]
        pairs = await asyncio.gather(*tasks)

        self._flush_uid_cache()
        stats.log()
        print(f"[Fetch] Wall time: {time.perf_counter() - t_start:.1f}s")

        return dict(pairs)

    # ── Per-user worker ───────────────────────────────────────────────────────
    async def _fetch_one(
        self,
        username: str,
        cutoff: datetime,
        max_per_user: int,
        sem: asyncio.Semaphore,
        stats: FetchStats,
        done: list[int],
        total: int,
        progress_cb=None,
    ) -> tuple[str, list[dict]]:
        async with sem:
            stats.total += 1
            t0       = time.perf_counter()
            last_exc: Exception | None = None

            for attempt in range(MAX_RETRIES + 1):
                if attempt > 0:
                    # Exponential backoff with full jitter
                    cap     = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
                    backoff = random.uniform(0, cap)
                    print(
                        f"  ↻ @{username}: retry {attempt}/{MAX_RETRIES} "
                        f"backoff={backoff:.1f}s"
                    )
                    await asyncio.sleep(backoff)

                try:
                    tweets = await self._do_fetch(username, cutoff, max_per_user, stats)

                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    stats.latencies_ms.append(elapsed_ms)
                    stats.success += 1
                    if not tweets:
                        stats.empty += 1

                    done[0] += 1
                    if progress_cb:
                        progress_cb(done[0], total)
                    label = f"{len(tweets)} posts" if tweets else "quiet"
                    print(
                        f"  [{done[0]:>3}/{total}] @{username}: "
                        f"{label} ({elapsed_ms:.0f}ms)"
                    )
                    return username, tweets

                except Exception as exc:
                    last_exc  = exc
                    exc_lower = str(exc).lower()
                    is_rate   = any(k in exc_lower for k in
                                    ("rate limit", "429", "too many request", "ratelimit"))
                    is_transient = is_rate or any(k in exc_lower for k in
                                                  ("timeout", "connection", "503", "502",
                                                   "timedout", "timed out"))

                    if is_rate:
                        stats.rate_limited += 1

                    # Retry transient errors; bail immediately on auth/404/etc.
                    if attempt < MAX_RETRIES and is_transient:
                        continue

                    # Hard failure
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    stats.latencies_ms.append(elapsed_ms)
                    stats.failed += 1
                    done[0] += 1
                    if progress_cb:
                        progress_cb(done[0], total)
                    print(
                        f"  [{done[0]:>3}/{total}] ✗ @{username}: "
                        f"{type(exc).__name__}: {exc} ({elapsed_ms:.0f}ms)"
                    )
                    return username, []

            # Exhausted retries
            elapsed_ms = (time.perf_counter() - t0) * 1000
            stats.latencies_ms.append(elapsed_ms)
            stats.failed += 1
            done[0] += 1
            if progress_cb:
                progress_cb(done[0], total)
            print(
                f"  [{done[0]:>3}/{total}] ✗ @{username}: "
                f"exhausted retries ({elapsed_ms:.0f}ms)"
            )
            return username, []

    # ── Inner HTTP fetch (called inside semaphore slot) ───────────────────────
    async def _do_fetch(
        self,
        username: str,
        cutoff: datetime,
        max_per_user: int,
        stats: FetchStats,
    ) -> list[dict]:
        cached = self._uid_cache.get(username.lower())

        if cached:
            # Cache hit: skip get_user_by_screen_name entirely
            stats.cache_hits += 1
            user_id      = cached["id"]
            display_name = cached["name"]
            followers    = cached["followers"]
        else:
            # Cache miss: one extra HTTP call, then persist result
            await asyncio.sleep(REQ_JITTER * random.uniform(0.5, 1.5))
            try:
                user = await asyncio.wait_for(
                    self._client.get_user_by_screen_name(username),
                    timeout=REQ_TIMEOUT,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"get_user_by_screen_name timed out after {REQ_TIMEOUT}s"
                )
            user_id      = user.id
            display_name = user.name
            followers    = getattr(user, "followers_count", 0) or 0
            self._uid_cache[username.lower()] = {
                "id":        user_id,
                "name":      display_name,
                "followers": followers,
            }

        # Small jitter before tweet fetch
        await asyncio.sleep(REQ_JITTER * random.uniform(0.5, 1.5))

        try:
            raw_tweets = await asyncio.wait_for(
                self._client.get_user_tweets(
                    user_id=user_id,
                    tweet_type="Tweets",
                    count=max_per_user,
                ),
                timeout=REQ_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"get_user_tweets timed out after {REQ_TIMEOUT}s"
            )

        recent: list[dict] = []
        for t in raw_tweets:
            created = _parse_date(t.created_at)
            if created and created >= cutoff:
                recent.append({
                    "username":     username,
                    "display_name": display_name,
                    "followers":    followers,
                    "text":         t.text or "",
                    "created_at":   t.created_at,
                    "likes":        getattr(t, "favorite_count", 0) or 0,
                    "retweets":     getattr(t, "retweet_count", 0) or 0,
                    "replies":      getattr(t, "reply_count", 0) or 0,
                })
        return recent

    # ── UID cache I/O ─────────────────────────────────────────────────────────
    def _load_uid_cache(self) -> dict:
        _DATA_DIR.mkdir(exist_ok=True)
        if UID_CACHE_FILE.exists():
            try:
                return json.loads(UID_CACHE_FILE.read_text("utf-8"))
            except Exception as e:
                print(f"[Cache] Failed to load UID cache: {e}")
        return {}

    def _flush_uid_cache(self) -> None:
        try:
            UID_CACHE_FILE.write_text(
                json.dumps(self._uid_cache, ensure_ascii=False, indent=2), "utf-8"
            )
            print(f"[Cache] Saved {len(self._uid_cache)} UID entries.")
        except Exception as e:
            print(f"[Cache] Failed to save UID cache: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, TWEET_DATE_FMT)
    except ValueError:
        return None
