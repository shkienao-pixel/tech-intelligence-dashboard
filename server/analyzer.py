"""Claude-powered intelligence analyzer for X posts."""
from __future__ import annotations

import json
import os
from datetime import datetime

from anthropic import AsyncAnthropic

# 每条推文最大字符数（避免单条超长推文撑爆 prompt）
_MAX_TWEET_CHARS = 280
# 发给 Claude 的最大推文条数
_MAX_TWEETS = 80
# posts_text 最大总字符数（约 20 000 tokens 的安全上限）
_MAX_POSTS_CHARS = 60_000

_SYSTEM = (
    "You are an elite technology intelligence analyst specializing in AI and Silicon Valley trends. "
    "Analyze X posts from top tech influencers and extract structured intelligence. "
    "Always respond with valid JSON only — no markdown, no code blocks, no extra text."
)

_PROMPT = """\
Analyze these X posts from top tech/AI influencers collected in the last 24 hours.
Today's date: {today}

=== POSTS ===
{posts_text}
=============

Return a JSON object with EXACTLY this structure (all fields required):

{{
  "title": "Daily Tech Intelligence Report — {today}",
  "subtitle": "One-sentence summary of the single most important theme today",
  "executive_summary": {{
    "paragraph1": "150-200 words. Cover the single biggest story dominating influencer discourse — cite specific people, companies, or products mentioned in the posts.",
    "paragraph2": "150-200 words. Cover secondary trends, provide strategic context, and note any surprising or contrarian signals from the data."
  }},
  "trending_topics": [
    {{
      "tag": "#TopicName",
      "change": "+XX%" or "NEW" or "-XX%",
      "is_new": false,
      "velocity": 85
    }}
  ],
  "strategic_trends": [
    {{
      "name": "Trend Name (3-5 words)",
      "velocity_label": "High Velocity",
      "change": "+XX%",
      "direction": "up",
      "description": "2-3 sentences grounded in specific posts. Name actual accounts or products."
    }}
  ],
  "influencer_highlights": [
    {{
      "username": "handle_without_at",
      "display_name": "Full Display Name",
      "role": "Job Title / Company",
      "quote": "The most notable or quotable line from their post (paraphrase if needed, keep under 200 chars)",
      "likes": 12400,
      "shares": 3200
    }}
  ],
  "visual_insight": {{
    "title": "3-5 word catchy title for today's dominant technical metaphor",
    "description": "2-3 sentences describing the key technical shift as a vivid visual concept"
  }}
}}

Rules:
- trending_topics: exactly 7 items, sorted by velocity (0-100) descending
- strategic_trends: exactly 3 items — the three most significant patterns in the data
- influencer_highlights: exactly 4 items — the four most impactful/viral posts
- velocity_label options: "High Velocity", "Emerging", "Critical", "Stable"
- direction options: "up", "steady", "down"
- Base EVERYTHING on the actual post content above — no hallucination
- For likes/shares use the actual numbers from the data
"""


class Analyzer:
    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        self._client = AsyncAnthropic(api_key=api_key)

    async def analyze(self, tweets_by_user: dict[str, list[dict]]) -> dict:
        # Flatten all tweets
        all_tweets: list[dict] = []
        for tweets in tweets_by_user.values():
            all_tweets.extend(tweets)

        if not all_tweets:
            raise ValueError("No posts collected — nothing to analyze.")

        # Sort by engagement (likes + 3× retweets) and take top tweets
        all_tweets.sort(
            key=lambda t: t.get("likes", 0) + t.get("retweets", 0) * 3,
            reverse=True,
        )
        top = all_tweets[:_MAX_TWEETS]

        # 构建 posts_text，截断单条推文文本，并设置总字符上限
        lines: list[str] = []
        total_chars = 0
        for t in top:
            text = (t["text"] or "")[:_MAX_TWEET_CHARS]
            block = (
                f"@{t['username']} ({t.get('followers', 0):,} followers)\n"
                f"❤️ {t.get('likes', 0):,}  🔁 {t.get('retweets', 0):,}  💬 {t.get('replies', 0):,}\n"
                f"{text}"
            )
            if total_chars + len(block) > _MAX_POSTS_CHARS:
                print(f"[Claude] posts_text 已达字符上限，仅使用前 {len(lines)} 条推文")
                break
            lines.append(block)
            total_chars += len(block)

        posts_text = "\n\n".join(lines)

        today = datetime.now().strftime("%B %d, %Y")
        prompt = _PROMPT.format(posts_text=posts_text, today=today)

        print(f"[Claude] Sending {len(lines)} posts for analysis (prompt ~{total_chars:,} chars)…")
        msg = await self._client.messages.create(
            model="claude-opus-4-6",
            max_tokens=16000,   # 从 4096 提升到 16000，确保完整 JSON 输出不被截断
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = msg.content[0].text.strip()
        # Strip accidental markdown code fences (```json ... ``` 或 ``` ... ```)
        if raw.startswith("```"):
            raw_lines = raw.splitlines()
            # 去掉首行（```json 或 ```）和末行（```）
            end = -1 if raw_lines[-1].strip() == "```" else len(raw_lines)
            raw = "\n".join(raw_lines[1:end])

        # 检测截断：如果响应不是完整 JSON，给出明确错误
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            stop_reason = getattr(msg, "stop_reason", "unknown")
            raise ValueError(
                f"Claude 返回的 JSON 无法解析（stop_reason={stop_reason!r}）。"
                f"可能输出被截断。原始响应末尾：…{raw[-200:]!r}"
            ) from exc

        print(f"[Claude] Analysis complete (stop_reason={msg.stop_reason}).")
        return result
