"""Tech Intelligence API — FastAPI backend."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

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
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
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


# ── Helpers ───────────────────────────────────────────────────────────────────
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
    try:
        # 1. Connect to X
        job.update(status="running", progress=5, message="Connecting to X…")
        x = XClient()
        await x.connect()

        # 2. Fetch tweets
        job.update(progress=15, message=f"Fetching posts from {len(TOP_TECH_INFLUENCERS)} influencers…")
        tweets_by_user = await x.fetch_recent_tweets(
            usernames=TOP_TECH_INFLUENCERS,
            hours=24,
            max_per_user=20,
            delay=0.8,
        )
        active_users = sum(1 for v in tweets_by_user.values() if v)
        total_posts  = sum(len(v) for v in tweets_by_user.values())

        job.update(
            progress=65,
            message=f"Collected {total_posts:,} posts from {active_users} accounts · Analyzing with Claude…",
        )

        # 3. Analyze
        analyzer = Analyzer()
        report = await analyzer.analyze(tweets_by_user)

        # 4. Enrich & save
        report["generated_at"]      = datetime.now().isoformat()
        report["total_posts"]        = total_posts
        report["total_influencers"]  = active_users
        report_id = _save_report(report)

        job.update(
            status="completed",
            progress=100,
            message="Report ready!",
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


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
