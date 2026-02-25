"""Tech Intelligence API — FastAPI backend."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

from analyzer import Analyzer
from influencers import TOP_TECH_INFLUENCERS
from x_client import XClient, XClientError

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).parent
DATA_DIR         = BASE_DIR / "data"
REPORTS_DIR      = DATA_DIR / "reports"
INFLUENCERS_FILE = DATA_DIR / "influencers.json"
SETTINGS_FILE    = DATA_DIR / "settings.json"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Tech Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = BASE_DIR.parent
app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# ── In-memory job store ───────────────────────────────────────────────────────
jobs: dict[str, dict] = {}


# ── Influencer helpers ────────────────────────────────────────────────────────
def _load_influencers() -> list[str]:
    if INFLUENCERS_FILE.exists():
        return json.loads(INFLUENCERS_FILE.read_text("utf-8"))
    return list(TOP_TECH_INFLUENCERS)


def _save_influencers(lst: list[str]) -> None:
    INFLUENCERS_FILE.write_text(json.dumps(lst, ensure_ascii=False, indent=2), "utf-8")


# ── Settings helpers ──────────────────────────────────────────────────────────
_SETTINGS_DEFAULTS: dict[str, Any] = {"fetch_hours": 24, "max_per_user": 20}


def _load_settings() -> dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            return {**_SETTINGS_DEFAULTS, **json.loads(SETTINGS_FILE.read_text("utf-8"))}
        except Exception:
            pass
    return dict(_SETTINGS_DEFAULTS)


def _save_settings(data: dict) -> None:
    current = _load_settings()
    allowed = {"fetch_hours", "max_per_user"}
    current.update({k: v for k, v in data.items() if k in allowed})
    SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), "utf-8")


# ── Report helpers ────────────────────────────────────────────────────────────
def _load_latest_report() -> dict | None:
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    return json.loads(files[0].read_text("utf-8")) if files else None


def _list_reports(limit: int = 20) -> list[dict]:
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)[:limit]
    result = []
    for f in files:
        try:
            d = json.loads(f.read_text("utf-8"))
            result.append({
                "id":          d.get("id", f.stem),
                "title":       d.get("title", "Daily Intel Report"),
                "subtitle":    d.get("subtitle", ""),
                "date":        (d.get("generated_at") or "")[:10],
                "total_posts": d.get("total_posts", 0),
                "score":       "HIGH INTEL",
            })
        except Exception:
            continue
    return result


def _save_report(data: dict) -> str:
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_id = f"{ts}_{uuid.uuid4().hex[:6]}"
    data["id"] = report_id
    path = REPORTS_DIR / f"{report_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    return report_id


# ── Background Task ───────────────────────────────────────────────────────────
async def _run_pipeline(job_id: str) -> None:
    job = jobs[job_id]
    t_pipeline = time.perf_counter()

    def _phase(name: str, t0: float) -> float:
        elapsed = time.perf_counter() - t0
        print(f"[Pipeline] ✓ {name}: {elapsed:.1f}s")
        return elapsed

    try:
        # ── Phase 1: Connect ──────────────────────────────────────────────────
        t0 = time.perf_counter()
        job.update(status="running", progress=5, message="Connecting to X…")
        x = XClient()
        await x.connect()
        _phase("connect", t0)

        # ── Phase 2: Fetch tweets (concurrent) ───────────────────────────────
        t0          = time.perf_counter()
        influencers = _load_influencers()
        settings    = _load_settings()
        job.update(
            progress=15,
            message=f"Fetching posts from {len(influencers)} influencers…",
        )

        def _on_fetch_progress(done: int, total: int) -> None:
            # Map fetch progress onto 15-62% of the overall job
            pct = 15 + int(done / max(total, 1) * 47)
            job.update(
                progress=pct,
                message=f"Fetching influencers: {done}/{total}…",
            )

        tweets_by_user = await x.fetch_recent_tweets(
            usernames=influencers,
            hours=settings["fetch_hours"],
            max_per_user=settings["max_per_user"],
            progress_cb=_on_fetch_progress,
        )
        active_users = sum(1 for v in tweets_by_user.values() if v)
        total_posts  = sum(len(v) for v in tweets_by_user.values())
        t_fetch = _phase(
            f"fetch ({total_posts:,} posts from {active_users} active accounts)", t0
        )

        job.update(
            progress=65,
            message=f"Collected {total_posts:,} posts · Analyzing with Claude…",
        )

        # ── Phase 3: Analyze with Claude ─────────────────────────────────────
        t0       = time.perf_counter()
        analyzer = Analyzer()
        report   = await analyzer.analyze(tweets_by_user)
        _phase("analyze (Claude)", t0)

        # ── Phase 4: Save ─────────────────────────────────────────────────────
        t0 = time.perf_counter()
        report["generated_at"]     = datetime.now().isoformat()
        report["total_posts"]      = total_posts
        report["total_influencers"] = active_users
        report_id = _save_report(report)
        _phase("save report", t0)

        total_wall = time.perf_counter() - t_pipeline
        print(f"[Pipeline] ── TOTAL WALL TIME: {total_wall:.1f}s ──")

        job.update(
            status="completed",
            progress=100,
            message=f"Report ready! (generated in {total_wall:.0f}s)",
            report_id=report_id,
        )

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[Pipeline ERROR]\n{tb}")
        job.update(status="failed", progress=0, message=f"{type(exc).__name__}: {exc}\n\n{tb}")
        raise


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/api/status")
async def api_status():
    has_x      = bool(os.getenv("X_USERNAME") and os.getenv("X_PASSWORD"))
    has_claude = bool(os.getenv("ANTHROPIC_API_KEY"))
    latest     = _load_latest_report()
    return {
        "ok":               True,
        "x_configured":     has_x,
        "claude_configured": has_claude,
        "ready":            has_x and has_claude,
        "last_report":      (latest or {}).get("generated_at"),
        "influencer_count": len(TOP_TECH_INFLUENCERS),
    }


@app.post("/api/generate")
async def api_generate(background_tasks: BackgroundTasks):
    if not os.getenv("X_USERNAME"):
        raise HTTPException(400, "X_USERNAME not configured. Edit server/.env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(400, "ANTHROPIC_API_KEY not configured. Edit server/.env")

    job_id = uuid.uuid4().hex
    jobs[job_id] = {"status": "pending", "progress": 0, "message": "Queued…"}
    background_tasks.add_task(_run_pipeline, job_id)
    return {"job_id": job_id}


@app.get("/api/job/{job_id}")
async def api_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.get("/api/dashboard")
async def api_dashboard():
    latest = _load_latest_report()
    if not latest:
        raise HTTPException(404, "No report yet. Click 'Generate Daily Report'.")

    return {
        "stats": {
            "influencers":   latest.get("total_influencers", len(TOP_TECH_INFLUENCERS)),
            "posts":         latest.get("total_posts", 0),
            "trends":        len(latest.get("trending_topics", [])),
            "last_updated":  latest.get("generated_at", ""),
        },
        "trending_topics":   latest.get("trending_topics", []),
        "recent_reports":    _list_reports(10),
    }


@app.get("/api/reports")
async def api_reports():
    return _list_reports(20)


@app.get("/api/report/latest")
async def api_report_latest():
    latest = _load_latest_report()
    if not latest:
        raise HTTPException(404, "No reports yet.")
    return latest


@app.get("/api/report/{report_id}")
async def api_report_by_id(report_id: str):
    path = REPORTS_DIR / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Report '{report_id}' not found.")
    return json.loads(path.read_text("utf-8"))


@app.delete("/api/report/{report_id}")
async def api_delete_report(report_id: str):
    if not re.match(r'^[A-Za-z0-9_]+$', report_id):
        raise HTTPException(400, "Invalid report ID.")
    path = REPORTS_DIR / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Report '{report_id}' not found.")
    path.unlink()
    return {"ok": True}


# ── Influencer endpoints ──────────────────────────────────────────────────────
@app.get("/api/influencers")
async def api_get_influencers():
    lst = _load_influencers()
    return {"influencers": lst, "total": len(lst)}


@app.post("/api/influencers")
async def api_add_influencer(body: dict):
    username = body.get("username", "").strip().lstrip("@")
    if not username or not re.match(r'^[A-Za-z0-9_]{1,50}$', username):
        raise HTTPException(400, "Invalid username — only letters, numbers and underscores allowed.")
    lst = _load_influencers()
    if username.lower() in {u.lower() for u in lst}:
        raise HTTPException(409, f"@{username} is already in the list.")
    lst.append(username)
    _save_influencers(lst)
    return {"ok": True, "influencers": lst, "total": len(lst)}


@app.delete("/api/influencers/{username}")
async def api_delete_influencer(username: str):
    lst = _load_influencers()
    new_lst = [u for u in lst if u.lower() != username.lower()]
    if len(new_lst) == len(lst):
        raise HTTPException(404, f"@{username} not found.")
    _save_influencers(new_lst)
    return {"ok": True, "influencers": new_lst, "total": len(new_lst)}


# ── Settings endpoints ────────────────────────────────────────────────────────
@app.get("/api/settings")
async def api_get_settings():
    s = _load_settings()
    return {
        **s,
        "x_configured":     bool(os.getenv("X_USERNAME")),
        "claude_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "x_username":       os.getenv("X_USERNAME", ""),
        "report_count":     len(list(REPORTS_DIR.glob("*.json"))),
        "influencer_count": len(_load_influencers()),
    }


@app.post("/api/settings")
async def api_save_settings(body: dict):
    _save_settings(body)
    return {"ok": True}


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
