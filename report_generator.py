"""
Nepal Government News Tracker — AI Report Generator
Uses Google Gemini (FREE) to generate structured, summarized news reports.
Beautiful card-based layout with category sections, summaries, and full article links.
"""

import re
import logging
from datetime import datetime
from google import genai

import config

logger = logging.getLogger(__name__)

# ─── Category Config ──────────────────────────────────────────
CATEGORY_CONFIG = {
    "government": {
        "label": "Government & Politics",
        "icon": "&#x1F3DB;",
        "color": "#2d3436",
        "bg": "#dfe6e9",
    },
    "politics": {
        "label": "Government & Politics",
        "icon": "&#x1F3DB;",
        "color": "#2d3436",
        "bg": "#dfe6e9",
    },
    "gold": {
        "label": "Gold & Silver Prices",
        "icon": "&#x1F4B0;",
        "color": "#b58900",
        "bg": "#fef9e7",
    },
    "tech": {
        "label": "Tech News",
        "icon": "&#x1F4BB;",
        "color": "#6c5ce7",
        "bg": "#ede7f6",
    },
    "stock": {
        "label": "Stock Market / NEPSE",
        "icon": "&#x1F4C8;",
        "color": "#00b894",
        "bg": "#e0f7e9",
    },
    "instagram": {
        "label": "Trending (Instagram)",
        "icon": "&#x1F4F7;",
        "color": "#e84393",
        "bg": "#fce4ec",
    },
    "tiktok": {
        "label": "Trending (TikTok)",
        "icon": "&#x1F3B5;",
        "color": "#010101",
        "bg": "#e8e8e8",
    },
    "linkedin": {
        "label": "Business (LinkedIn)",
        "icon": "&#x1F4BC;",
        "color": "#0077b5",
        "bg": "#e1f0fa",
    },
    "general": {
        "label": "General News",
        "icon": "&#x1F4F0;",
        "color": "#636e72",
        "bg": "#f0f0f0",
    },
}


class ReportGenerator:
    """Generates AI-powered news reports using Google Gemini (free)."""

    def __init__(self):
        key = config.GEMINI_API_KEY
        if key == "your-gemini-api-key" or not key:
            logger.error("GEMINI_API_KEY is NOT set! Get FREE key at https://aistudio.google.com/apikey")
            self.client = None
        else:
            masked = key[:8] + "..." + key[-4:]
            logger.info(f"Gemini API key loaded: {masked} | Model: {config.GEMINI_MODEL}")
            self.client = genai.Client(api_key=key)

    def generate(self, articles: list[dict]) -> dict:
        if not articles:
            return self._empty_report()

        timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")

        # Get AI summary
        ai_summary = self._get_ai_summary(articles)

        # Build category-based article cards
        grouped = self._group_articles(articles)

        subject = f"Nepal News Briefing — {timestamp}"

        return {
            "subject": subject,
            "timestamp": timestamp,
            "article_count": len(articles),
            "articles": articles,
            "plain_text": self._to_plain(ai_summary, grouped, timestamp),
            "html": self._to_html(ai_summary, grouped, timestamp, len(articles)),
            "slack_blocks": self._to_slack(ai_summary, grouped, timestamp, len(articles)),
        }

    def _get_ai_summary(self, articles: list[dict]) -> str:
        """Get AI-generated headline summary."""
        articles_text = self._format_articles_for_prompt(articles)
        prompt = f"""You are a Nepal news analyst. Analyze these articles and write a SHORT executive summary (4-5 sentences max) covering the most important developments today across government, economy, gold prices, tech, and stock market.

ARTICLES:
{articles_text}

Rules:
- Maximum 5 sentences
- Cover the top highlights across all categories
- Mention exact gold prices if available
- Be factual, cite source names
- Professional tone"""

        try:
            if not self.client:
                raise ValueError("Gemini client not initialized")
            logger.info(f"Calling Gemini API...")
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
            )
            logger.info(f"Gemini API success!")
            return response.text
        except Exception as e:
            logger.error(f"GEMINI API FAILED: {type(e).__name__}: {e}")
            return ""

    def _group_articles(self, articles: list[dict]) -> dict:
        """Group articles by category, merging politics into government."""
        grouped = {}
        for a in articles:
            cat = a.get("category", "general")
            # Merge politics into government
            if cat == "politics":
                cat = "government"
            grouped.setdefault(cat, []).append(a)
        return grouped

    def _format_articles_for_prompt(self, articles: list[dict]) -> str:
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(
                f"[{i}] [{a.get('category','general').upper()}] {a['source']}: "
                f"{a['title']} — {a.get('summary', '')[:200]}"
            )
        return "\n".join(lines)

    # ─── HTML Report (Email) ──────────────────────────────────
    def _to_html(self, ai_summary: str, grouped: dict, timestamp: str, count: int) -> str:

        # AI Summary section
        if ai_summary:
            summary_html = (
                f'<div style="background:#f0f4ff;border-left:4px solid #6c5ce7;padding:16px 20px;'
                f'margin:0 0 24px;border-radius:0 8px 8px 0;">'
                f'<h3 style="margin:0 0 8px;color:#6c5ce7;font-size:14px;">AI Summary</h3>'
                f'<p style="margin:0;color:#333;line-height:1.7;font-size:14px;">'
                f'{self._md_to_html_inline(ai_summary)}</p></div>'
            )
        else:
            summary_html = ""

        # Build category sections with news cards
        sections_html = ""
        # Define display order
        order = ["government", "stock", "gold", "tech", "instagram", "tiktok", "linkedin", "general"]
        for cat in order:
            items = grouped.get(cat, [])
            if not items:
                continue

            cfg = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["general"])

            # Section header
            sections_html += (
                f'<div style="margin:24px 0 12px;">'
                f'<div style="display:inline-block;background:{cfg["bg"]};color:{cfg["color"]};'
                f'padding:6px 14px;border-radius:20px;font-size:13px;font-weight:600;">'
                f'{cfg["icon"]} {cfg["label"]}'
                f'</div></div>\n'
            )

            # News cards
            for a in items[:6]:
                url = a.get("full_article_url", a["url"])
                summary = a.get("summary", "")[:120]
                source = a.get("source", "")
                ig_url = a.get("instagram_url", "")

                summary_text = f'<p style="margin:6px 0 8px;color:#666;font-size:12px;line-height:1.5;">{summary}</p>' if summary else ""
                ig_badge = (f'<span style="color:#E1306C;font-size:10px;margin-left:6px;">IG</span>') if ig_url else ""

                sections_html += (
                    f'<div style="background:#fff;border:1px solid #eee;border-radius:8px;'
                    f'padding:14px 16px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                    f'<div style="font-size:14px;font-weight:600;color:#1a1a2e;line-height:1.4;">'
                    f'{a["title"][:100]}</div>'
                    f'<div style="font-size:11px;color:#999;margin-top:4px;">'
                    f'{source}{ig_badge}</div>'
                    f'{summary_text}'
                    f'<a href="{url}" style="color:#6c5ce7;text-decoration:none;'
                    f'font-size:12px;font-weight:500;">Read full article &#x2192;</a>'
                    f'</div>\n'
                )

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:640px;margin:0 auto;padding:0;background:#f5f5f5;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);color:white;padding:28px 24px;text-align:center;">
    <h1 style="margin:0;font-size:24px;font-weight:700;letter-spacing:-0.5px;">Nepal News Briefing</h1>
    <p style="margin:8px 0 0;opacity:0.8;font-size:13px;">{timestamp}</p>
    <div style="margin:12px auto 0;display:inline-block;">
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F3DB; Gov</span>
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F4B0; Gold</span>
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F4BB; Tech</span>
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F4C8; Stock</span>
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F4F1; Social</span>
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F3B5; TikTok</span>
      <span style="background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:12px;font-size:11px;margin:0 3px;">&#x1F4BC; LinkedIn</span>
    </div>
    <p style="margin:10px 0 0;opacity:0.6;font-size:12px;">{count} articles analyzed from 19 sources</p>
  </div>

  <!-- Content -->
  <div style="background:#f9f9fb;padding:20px 24px;">
    {summary_html}
    {sections_html}
  </div>

  <!-- Footer -->
  <div style="background:#1a1a2e;color:rgba(255,255,255,0.6);padding:16px 24px;text-align:center;font-size:11px;">
    Nepal News Tracker &bull; Powered by Gemini AI &bull; Hourly Updates<br>
    Sources: KTM Post, Republica, Himalayan Times, RONB, Ashesh, ShareSansar, Techmandu &amp; more
  </div>

</body>
</html>"""

    # ─── Plain Text Report ────────────────────────────────────
    def _to_plain(self, ai_summary: str, grouped: dict, timestamp: str) -> str:
        lines = [
            f"NEPAL NEWS BRIEFING — {timestamp}",
            "=" * 50,
        ]

        if ai_summary:
            lines.append(f"\nAI SUMMARY:\n{ai_summary}\n")

        order = ["government", "stock", "gold", "tech", "instagram", "tiktok", "linkedin", "general"]
        for cat in order:
            items = grouped.get(cat, [])
            if not items:
                continue

            cfg = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["general"])
            lines.append(f"\n{'─' * 40}")
            lines.append(f"{cfg['label'].upper()}")
            lines.append(f"{'─' * 40}")

            for a in items[:6]:
                url = a.get("full_article_url", a["url"])
                summary = a.get("summary", "")[:120]
                lines.append(f"\n  {a['title'][:90]}")
                lines.append(f"  Source: {a.get('source', '')}")
                if summary:
                    lines.append(f"  {summary}")
                lines.append(f"  Read: {url}")

        return "\n".join(lines)

    # ─── Slack Report ─────────────────────────────────────────
    def _to_slack(self, ai_summary: str, grouped: dict, timestamp: str, count: int) -> dict:
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "Nepal News Briefing"}},
            {"type": "context", "elements": [{"type": "mrkdwn",
                "text": f":newspaper: *{count} articles* | :clock1: {timestamp}"}]},
            {"type": "divider"},
        ]

        if ai_summary:
            blocks.append({"type": "section", "text": {"type": "mrkdwn",
                "text": f"*:brain: AI Summary*\n{ai_summary[:500]}"}})
            blocks.append({"type": "divider"})

        order = ["government", "stock", "gold", "tech", "instagram", "tiktok", "linkedin", "general"]
        emojis = {
            "government": ":classical_building:", "stock": ":chart_with_upwards_trend:",
            "gold": ":coin:", "tech": ":computer:", "instagram": ":camera:",
            "tiktok": ":musical_note:", "linkedin": ":briefcase:",
            "general": ":newspaper:",
        }

        for cat in order:
            items = grouped.get(cat, [])
            if not items:
                continue
            cfg = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["general"])
            emoji = emojis.get(cat, ":newspaper:")

            text = f"*{emoji} {cfg['label']}*\n"
            for a in items[:4]:
                url = a.get("full_article_url", a["url"])
                summary = a.get("summary", "")[:80]
                text += f"\n> *<{url}|{a['title'][:70]}>*"
                text += f"\n> _{a.get('source', '')}_"
                if summary:
                    text += f"\n> {summary}"
                text += "\n"

            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}})

        blocks.append({"type": "divider"})
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": ":robot_face: _Nepal News Tracker | Powered by Gemini AI_"}]})

        return {"text": f"Nepal News Briefing — {timestamp}", "blocks": blocks}

    # ─── Helpers ──────────────────────────────────────────────
    def _md_to_html_inline(self, text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = text.replace('\n', '<br>')
        return text

    def _empty_report(self) -> dict:
        timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")
        msg = "No new articles found this cycle. Next check in 1 hour."
        return {
            "subject": f"Nepal News Briefing — {timestamp} (No updates)",
            "timestamp": timestamp, "article_count": 0, "articles": [],
            "plain_text": msg,
            "html": f"<html><body><p>{msg}</p></body></html>",
            "slack_blocks": {"text": msg, "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f":sleeping: {msg}"}}]},
        }
