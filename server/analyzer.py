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

# ── Pass 1: English analysis (原始 prompt，保持质量和速度) ─────────────────────
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

# ── Pass 2: Chinese translation (轻量翻译，用快速模型) ─────────────────────────
_TRANSLATE_SYSTEM = (
    "You are a professional Chinese translator. "
    "Translate the given JSON fields to Chinese. "
    "Return valid JSON only — no markdown, no extra text. "
    "CRITICAL: When the Chinese translation contains double-quote characters (\"), "
    "you MUST escape them as \\\" inside JSON string values. "
    "Use Chinese quotation marks \u300c\u300d or \u201c\u201d instead of ASCII \" "
    "whenever possible to avoid escaping issues."
)


def _build_translate_prompt(report: dict) -> str:
    """用字符串拼接构建翻译 prompt，避免 .format() 在内容含 { } 时崩溃。"""
    es = report.get("executive_summary", {})
    vi = report.get("visual_insight", {})
    trends = report.get("strategic_trends", [])
    highlights = report.get("influencer_highlights", [])

    subtitle       = report.get("subtitle", "")
    paragraph1     = es.get("paragraph1", "")
    paragraph2     = es.get("paragraph2", "")
    vi_title       = vi.get("title", "")
    vi_description = vi.get("description", "")

    trends_text = "\n".join(
        f"{i+1}. name: {t.get('name','')}\n   description: {t.get('description','')}"
        for i, t in enumerate(trends)
    )
    highlights_text = "\n".join(
        f"{i+1}. role: {h.get('role','')}\n   quote: {h.get('quote','')}"
        for i, h in enumerate(highlights)
    )

    # 拼接代替 .format()，防止内容里的 { } 触发 KeyError
    return (
        'Translate the following English texts to Chinese. '
        'Return a JSON object with exactly these keys:\n\n'
        '{\n'
        '  "zh_subtitle": "<translated subtitle>",\n'
        '  "zh_paragraph1": "<translated paragraph1>",\n'
        '  "zh_paragraph2": "<translated paragraph2>",\n'
        '  "zh_visual_insight_title": "<translated visual insight title>",\n'
        '  "zh_visual_insight_description": "<translated visual insight description>",\n'
        '  "zh_trends": [\n'
        '    {"zh_name": "<translated name>", "zh_description": "<translated description>"}\n'
        '  ],\n'
        '  "zh_highlights": [\n'
        '    {"zh_role": "<translated role>", "zh_quote": "<translated quote>"}\n'
        '  ]\n'
        '}\n\n'
        '=== TEXTS TO TRANSLATE ===\n'
        'subtitle: ' + subtitle + '\n\n'
        'paragraph1: ' + paragraph1 + '\n\n'
        'paragraph2: ' + paragraph2 + '\n\n'
        'visual_insight title: ' + vi_title + '\n\n'
        'visual_insight description: ' + vi_description + '\n\n'
        'strategic_trends:\n' + trends_text + '\n\n'
        'influencer_highlights:\n' + highlights_text + '\n'
    )


def _merge_translations(report: dict, trans: dict) -> dict:
    """将翻译结果合并到报告 dict 中（不修改原始 report，返回新 dict）。"""
    result = dict(report)
    result["zh_subtitle"] = trans.get("zh_subtitle", "")

    es = dict(result.get("executive_summary", {}))
    es["zh_paragraph1"] = trans.get("zh_paragraph1", "")
    es["zh_paragraph2"] = trans.get("zh_paragraph2", "")
    result["executive_summary"] = es

    vi = dict(result.get("visual_insight", {}))
    vi["zh_title"] = trans.get("zh_visual_insight_title", "")
    vi["zh_description"] = trans.get("zh_visual_insight_description", "")
    result["visual_insight"] = vi

    zh_trends = trans.get("zh_trends", [])
    trends = [dict(t) for t in result.get("strategic_trends", [])]
    for i, t in enumerate(trends):
        if i < len(zh_trends):
            t["zh_name"] = zh_trends[i].get("zh_name", "")
            t["zh_description"] = zh_trends[i].get("zh_description", "")
    result["strategic_trends"] = trends

    zh_highlights = trans.get("zh_highlights", [])
    highlights = [dict(h) for h in result.get("influencer_highlights", [])]
    for i, h in enumerate(highlights):
        if i < len(zh_highlights):
            h["zh_role"] = zh_highlights[i].get("zh_role", "")
            h["zh_quote"] = zh_highlights[i].get("zh_quote", "")
    result["influencer_highlights"] = highlights

    return result


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

        # ── Pass 1: 英文分析 ───────────────────────────────────────────────────
        print(f"[Claude] Pass 1 — analyzing {len(lines)} posts (~{total_chars:,} chars)…")
        msg = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw_lines = raw.splitlines()
            end = -1 if raw_lines[-1].strip() == "```" else len(raw_lines)
            raw = "\n".join(raw_lines[1:end])

        try:
            report = json.loads(raw)
        except json.JSONDecodeError as exc:
            stop_reason = getattr(msg, "stop_reason", "unknown")
            raise ValueError(
                f"Claude 返回的 JSON 无法解析（stop_reason={stop_reason!r}）。"
                f"可能输出被截断。原始响应末尾：…{raw[-200:]!r}"
            ) from exc

        print(f"[Claude] Pass 1 complete (stop_reason={msg.stop_reason}).")

        # ── Pass 2: 中文翻译（用 Haiku，快且省钱）─────────────────────────────
        print("[Claude] Pass 2 — translating to Chinese…")
        try:
            trans_prompt = _build_translate_prompt(report)
            trans_msg = await self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=_TRANSLATE_SYSTEM,
                messages=[{"role": "user", "content": trans_prompt}],
            )
            trans_raw = trans_msg.content[0].text.strip()
            if trans_raw.startswith("```"):
                trans_lines = trans_raw.splitlines()
                end = -1 if trans_lines[-1].strip() == "```" else len(trans_lines)
                trans_raw = "\n".join(trans_lines[1:end])
            try:
                trans = json.loads(trans_raw)
            except json.JSONDecodeError as je:
                # 记录详细错误帮助调试，然后抛出让外层 except 捕获
                print(f"[Claude] Pass 2 JSON parse error: {je}")
                print(f"[Claude] Pass 2 raw (first 300): {trans_raw[:300]!r}")
                raise
            report = _merge_translations(report, trans)
            print(f"[Claude] Pass 2 complete (stop_reason={trans_msg.stop_reason}).")
        except Exception as e:
            # 翻译失败不影响主报告，只记录警告
            print(f"[Claude] Pass 2 translation failed (non-fatal): {e}")

        return report
