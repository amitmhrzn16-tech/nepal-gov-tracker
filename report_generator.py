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
            "ai_summary": ai_summary,  # Raw AI text for audio generator
            "plain_text": self._to_plain(ai_summary, grouped, timestamp),
            "html": self._to_html(ai_summary, grouped, timestamp, len(articles)),
            "slack_blocks": self._to_slack(ai_summary, grouped, timestamp, len(articles)),
        }

    def _get_ai_summary(self, articles: list[dict]) -> str:
        """Get AI-generated detailed news report."""
        articles_text = self._format_articles_for_prompt(articles)
        prompt = f"""You are a senior Nepal news analyst delivering a detailed daily briefing. Analyze ALL of these articles and write a comprehensive report.

ARTICLES:
{articles_text}

Structure your report EXACTLY like this:

**TOP STORY**
Write 2-3 sentences about the single most important news of the day.

**GOVERNMENT & POLITICS**
Summarize all government/politics developments in 3-4 sentences. Name key figures and decisions.

**STOCK MARKET & NEPSE**
Summarize NEPSE performance, key movers, and market sentiment in 2-3 sentences with numbers.

**GOLD & SILVER PRICES**
Report exact prices if available. Compare with trends.

**TECH NEWS**
Summarize tech developments in 2-3 sentences.

**TRENDING ON SOCIAL MEDIA**
Summarize what's viral on Instagram/TikTok in Nepal in 2-3 sentences.

**BUSINESS & LINKEDIN**
Summarize any business/economy developments in 1-2 sentences.

Rules:
- Be factual, cite source names in parentheses
- Include specific numbers, prices, percentages where available
- Skip any section that has no articles
- Professional but engaging tone
- Total length: 250-400 words"""

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
                f'<div style="background:#f0f4ff;border-left:4px solid #6c5ce7;padding:18px 20px;'
                f'margin:0 0 24px;border-radius:0 8px 8px 0;">'
                f'<h3 style="margin:0 0 10px;color:#6c5ce7;font-size:15px;">'
                f'&#x1F9E0; AI Detailed Report</h3>'
                f'<div style="margin:0;color:#333;line-height:1.8;font-size:13px;">'
                f'{self._md_to_html_inline(ai_summary)}</div>'
                f'<div style="margin-top:12px;padding-top:10px;border-top:1px solid #ddd;'
                f'font-size:11px;color:#888;">&#x1F50A; Audio briefing attached — listen to this report</div>'
                f'</div>'
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

            # News cards — show ALL articles with social media links
            for a in items:
                url = a.get("full_article_url", a["url"])
                summary = a.get("summary", "")[:200]
                source = a.get("source", "")
                social_url = a.get("social_url", "")
                platform = a.get("platform", "")

                summary_text = f'<p style="margin:6px 0 8px;color:#555;font-size:12px;line-height:1.6;">{summary}</p>' if summary else ""

                # Build social media badge + link
                social_badge = ""
                if platform == "instagram" or social_url and "instagram.com" in social_url:
                    social_badge = (
                        f'<a href="{social_url}" style="display:inline-block;background:#E1306C;color:white;'
                        f'font-size:10px;padding:2px 8px;border-radius:10px;text-decoration:none;'
                        f'margin-left:6px;vertical-align:middle;">&#x1F4F7; Instagram</a>'
                    )
                elif platform == "tiktok" or social_url and "tiktok.com" in social_url:
                    social_badge = (
                        f'<a href="{social_url}" style="display:inline-block;background:#010101;color:white;'
                        f'font-size:10px;padding:2px 8px;border-radius:10px;text-decoration:none;'
                        f'margin-left:6px;vertical-align:middle;">&#x1F3B5; TikTok</a>'
                    )
                elif platform == "linkedin" or social_url and "linkedin.com" in social_url:
                    social_badge = (
                        f'<a href="{social_url}" style="display:inline-block;background:#0077b5;color:white;'
                        f'font-size:10px;padding:2px 8px;border-radius:10px;text-decoration:none;'
                        f'margin-left:6px;vertical-align:middle;">&#x1F4BC; LinkedIn</a>'
                    )

                # Build social view link separately (can't use backslash in f-string)
                social_link = ""
                if social_url and platform:
                    plat_name = platform.capitalize()
                    social_link = (
                        f'<a href="{social_url}" style="color:#E1306C;text-decoration:none;'
                        f'font-size:12px;">View on {plat_name} &#x2192;</a>'
                    )

                sections_html += (
                    f'<div style="background:#fff;border:1px solid #eee;border-radius:8px;'
                    f'padding:14px 16px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                    f'<div style="font-size:14px;font-weight:600;color:#1a1a2e;line-height:1.4;">'
                    f'{a["title"][:120]}</div>'
                    f'<div style="font-size:11px;color:#999;margin-top:4px;">'
                    f'{source}{social_badge}</div>'
                    f'{summary_text}'
                    f'<div style="margin-top:6px;">'
                    f'<a href="{url}" style="color:#6c5ce7;text-decoration:none;'
                    f'font-size:12px;font-weight:500;margin-right:12px;">Read full article &#x2192;</a>'
                    f'{social_link}'
                    f'</div>'
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
    <p style="margin:10px 0 0;opacity:0.6;font-size:12px;">{count} articles analyzed from 29 sources</p>
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

            for a in items:
                url = a.get("full_article_url", a["url"])
                summary = a.get("summary", "")[:150]
                social_url = a.get("social_url", "")
                platform = a.get("platform", "")
                lines.append(f"\n  {a['title'][:100]}")
                lines.append(f"  Source: {a.get('source', '')}")
                if summary:
                    lines.append(f"  {summary}")
                lines.append(f"  Read: {url}")
                if social_url and platform:
                    lines.append(f"  {platform.capitalize()}: {social_url}")

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
            for a in items:
                url = a.get("full_article_url", a["url"])
                summary = a.get("summary", "")[:100]
                social_url = a.get("social_url", "")
                platform = a.get("platform", "")
                text += f"\n> *<{url}|{a['title'][:80]}>*"
                text += f"\n> _{a.get('source', '')}_"
                if social_url and platform:
                    text += f" | <{social_url}|View on {platform.capitalize()}>"
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
