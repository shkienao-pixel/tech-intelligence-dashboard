"""X (Twitter) data fetcher using twikit — no paid API required."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from twikit import Client as TwikitClient
    TWIKIT_OK = True
except ImportError:
    TWIKIT_OK = False

COOKIES_FILE = Path(__file__).parent / "x_cookies.json"
TWEET_DATE_FMT = "%a %b %d %H:%M:%S %z %Y"   # "Mon Feb 19 14:30:00 +0000 2025"


class XClientError(Exception):
    pass


class XClient:
    def __init__(self) -> None:
        if not TWIKIT_OK:
            raise XClientError("twikit not installed. Run: pip install twikit")
        self._client = TwikitClient("en-US")
        self._ready = False

    # ── Authentication ────────────────────────────────────────────────────────
    async def connect(self) -> None:
        auth_token = os.getenv("X_AUTH_TOKEN", "").strip()
        ct0        = os.getenv("X_CT0", "").strip()
        username   = os.getenv("X_USERNAME", "").strip()
        email      = os.getenv("X_EMAIL", username).strip()
        password   = os.getenv("X_PASSWORD", "").strip()

        # ── 方式 A：浏览器 Cookie（优先，无需密码）──────────────────────────
        if auth_token and ct0:
            print("[X] 使用浏览器 Cookie 认证…")
            import json
            # twikit 要求 {name: value} 字典格式
            cookies = {"auth_token": auth_token, "ct0": ct0}
            COOKIES_FILE.write_text(json.dumps(cookies), "utf-8")
            self._client.load_cookies(str(COOKIES_FILE))
            self._ready = True
            print("[X] Cookie 认证成功。")
            return

        # ── 方式 B：尝试加载已保存的 Session ───────────────────────────────
        if COOKIES_FILE.exists():
            try:
                self._client.load_cookies(str(COOKIES_FILE))
                self._ready = True
                print("[X] 已加载保存的 Session。")
                return
            except Exception:
                print("[X] Session 已过期，重新登录…")

        # ── 方式 C：账号密码登录 ────────────────────────────────────────────
        if not username or not password:
            raise XClientError(
                "请在 server/.env 中填写认证信息：\n"
                "  方式A（推荐）：填写 X_AUTH_TOKEN 和 X_CT0\n"
                "  方式B：填写 X_USERNAME 和 X_PASSWORD"
            )

        print(f"[X] 密码登录 @{username}…")
        await self._client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
        self._client.save_cookies(str(COOKIES_FILE))
        self._ready = True
        print("[X] 登录成功，Session 已保存。")

    # ── Data Fetching ─────────────────────────────────────────────────────────
    async def fetch_recent_tweets(
        self,
        usernames: list[str],
        hours: int = 24,
        max_per_user: int = 20,
        delay: float = 1.0,
    ) -> dict[str, list[dict]]:
        """
        Fetch tweets posted within the last `hours` hours for each username.
        Returns {username: [tweet_dict, ...]}
        """
        if not self._ready:
            raise XClientError("Call connect() first.")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result: dict[str, list[dict]] = {}

        for idx, username in enumerate(usernames, 1):
            try:
                user = await self._client.get_user_by_screen_name(username)
                raw_tweets = await self._client.get_user_tweets(
                    user_id=user.id,
                    tweet_type="Tweets",
                    count=max_per_user,
                )

                recent: list[dict] = []
                for t in raw_tweets:
                    created = _parse_date(t.created_at)
                    if created and created >= cutoff:
                        recent.append({
                            "username":     username,
                            "display_name": user.name,
                            "followers":    getattr(user, "followers_count", 0) or 0,
                            "text":         t.text or "",
                            "created_at":   t.created_at,
                            "likes":        getattr(t, "favorite_count", 0) or 0,
                            "retweets":     getattr(t, "retweet_count", 0) or 0,
                            "replies":      getattr(t, "reply_count", 0) or 0,
                        })

                result[username] = recent
                status = f"{len(recent)} posts" if recent else "no new posts"
                print(f"  [{idx:>3}/{len(usernames)}] @{username}: {status}")

            except Exception as exc:
                print(f"  [{idx:>3}/{len(usernames)}] @{username}: ⚠ {exc}")
                result[username] = []

            await asyncio.sleep(delay)

        return result


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, TWEET_DATE_FMT)
    except ValueError:
        return None
