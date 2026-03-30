"""
Nepal Government News Tracker — AI Report Generator
Uses Google Gemini (FREE) to generate structured, summarized news reports.
Includes Gold Prices, Tech News, Instagram sources, and full article links.
"""

import re
import logging
from datetime import datetime
from google import genai

import config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates AI-powered news reports using Google Gemini (free)."""

    def __init__(self):
        key = config.GEMINI_API_KEY
        if key == "your-gemini-api-key" or not key:
            logger.error("GEMINI_API_KEY is NOT set! Add it to Railway Variables.")
            logger.error("Get a FREE key at: https://aistudio.google.com/apikey")
            self.client = None
        else:
            masked = key[:8] + "..." + key[-4:]
            logger.info(f"Gemini API key loaded: {masked}")
            logger.info(f"Using model: {config.GEMINI_MODEL}")
            self.client = genai.Client(api_key=key)

    def generate(self, articles: list[dict]) -> dict:
        if not articles:
            return self._empty_report()

        grouped = self._group_by_category(articles)
        articles_text = self._format_articles_for_prompt(articles)
        timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")

        prompt = f"""You are a Nepal news analyst. Analyze these recent articles and create a comprehensive briefing report.

ARTICLES:
{articles_text}

Create a report with these sections:

1. **HEADLINE SUMMARY** — 2-3 sentence overview of the most important developments across all categories

2. **GOVERNMENT & POLITICS** — Major government actions, policy changes, parliamentary proceedings, cabinet changes

3. **GOLD & SILVER PRICES** — Today's gold and silver rates in Nepal (Hallmark, Tajabi, Fine gold per tola). Show exact prices if available.

4. **TECH & DIGITAL** — Technology news, startups, digital Nepal initiatives, telecom updates

5. **TRENDING ON SOCIAL MEDIA** — Key stories from Instagram news portals like RONB (Routine of Nepal Banda), Nepal Live Today

6. **ECONOMIC OUTLOOK** — Budget, trade, NEPSE, remittance, exchange rate updates

7. **WATCH LIST** — Things to monitor based on current trends

Rules:
- Be factual and concise
- Cite the source name for each point
- If a section has no relevant news, write "No updates this hour"
- Keep the total report under 700 words
- Use professional, neutral tone
- For gold prices, show the actual numbers if available in the data"""

        try:
            if not self.client:
                raise ValueError("Gemini client not initialized — API key missing")

            logger.info(f"Calling Gemini API (model: {config.GEMINI_MODEL})...")
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
            )
            report_text = response.text
            logger.info(f"Gemini API success! Report length: {len(report_text)} chars")
        except Exception as e:
            logger.error(f"GEMINI API FAILED: {type(e).__name__}: {e}")
            logger.error("Possible fixes:\n"
                        "  1. Get a FREE key at https://aistudio.google.com/apikey\n"
                        "  2. Set GEMINI_API_KEY in Railway Variables\n"
                        "  3. No credit card needed — it's completely free")
            report_text = self._fallback_report(articles)

        # Build article links section
        article_links = self._build_article_links(articles)

        subject = f"Nepal News Briefing — {timestamp}"

        return {
            "subject": subject,
            "timestamp": timestamp,
            "article_count": len(articles),
            "articles": articles,
            "plain_text": report_text + "\n\n" + article_links["plain"],
            "html": self._to_html(report_text, article_links["html"], timestamp, len(articles)),
            "slack_blocks": self._to_slack_blocks(report_text, article_links["slack"], timestamp, len(articles)),
        }

    def _group_by_category(self, articles: list[dict]) -> dict:
        groups = {}
        for a in articles:
            cat = a.get("category", "general")
            groups.setdefault(cat, []).append(a)
        return groups

    def _format_articles_for_prompt(self, articles: list[dict]) -> str:
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(
                f"[{i}] Category: {a.get('category', 'general').upper()}\n"
                f"    Source: {a['source']}\n"
                f"    Title: {a['title']}\n"
                f"    Summary: {a.get('summary', 'N/A')[:300]}\n"
                f"    Published: {a.get('published', 'Unknown')}\n"
                f"    URL: {a['url']}\n"
            )
        return "\n".join(lines)

    def _build_article_links(self, articles: list[dict]) -> dict:
        """Build 'Read Full Article' links grouped by category."""
        categories = {
            "government": "Government & Politics",
            "politics": "Government & Politics",
            "general": "General News",
            "gold": "Gold & Silver Prices",
            "tech": "Tech News",
            "instagram": "Trending (Social Media)",
        }

        grouped = {}
        for a in articles:
            cat = a.get("category", "general")
            label = categories.get(cat, "Other")
            grouped.setdefault(label, []).append(a)

        # Plain text
        plain_lines = ["\n--- READ FULL ARTICLES ---\n"]
        for section, items in grouped.items():
            plain_lines.append(f"\n{section}:")
            for a in items[:5]:
                url = a.get("full_article_url", a["url"])
                plain_lines.append(f"  - {a['title'][:80]}")
                plain_lines.append(f"    Read: {url}")

        # HTML
        html_lines = []
        for section, items in grouped.items():
            html_lines.append(
                f'<h3 style="color:#1a1a2e;margin:18px 0 8px;font-size:15px;'
                f'border-left:3px solid #6c5ce7;padding-left:10px;">{section}</h3>'
            )
            for a in items[:5]:
                url = a.get("full_article_url", a["url"])
                ig_url = a.get("instagram_url", "")
                ig_badge = (f' <a href="{ig_url}" style="color:#E1306C;font-size:11px;'
                           f'text-decoration:none;">IG</a>') if ig_url else ""
                html_lines.append(
                    f'<div style="margin:6px 0;padding:8px 12px;background:#f8f9fa;'
                    f'border-radius:6px;font-size:13px;">'
                    f'<strong>{a["title"][:80]}</strong>'
                    f' <span style="color:#888;">— {a["source"]}</span>{ig_badge}<br>'
                    f'<a href="{url}" style="color:#6c5ce7;text-decoration:none;'
                    f'font-size:12px;">Read full article &rarr;</a>'
                    f'</div>'
                )

        # Slack
        slack_lines = ["\n*--- Read Full Articles ---*\n"]
        for section, items in grouped.items():
            slack_lines.append(f"\n*{section}:*")
            for a in items[:3]:
                url = a.get("full_article_url", a["url"])
                slack_lines.append(f"  <{url}|{a['title'][:60]}>")

        return {
            "plain": "\n".join(plain_lines),
            "html": "\n".join(html_lines),
            "slack": "\n".join(slack_lines),
        }

    def _to_html(self, report_text: str, article_links_html: str, timestamp: str, count: int) -> str:
        html_body = report_text
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)

        lines = html_body.split('\n')
        formatted_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list:
                    formatted_lines.append('<ul style="margin:8px 0;padding-left:20px;">')
                    in_list = True
                formatted_lines.append(f'<li style="margin:4px 0;color:#333;">{stripped[2:]}</li>')
            else:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                if stripped.startswith('#'):
                    stripped = stripped.lstrip('# ')
                    formatted_lines.append(
                        f'<h3 style="color:#1a1a2e;margin:16px 0 8px;border-bottom:2px solid #6c5ce7;'
                        f'padding-bottom:4px;">{stripped}</h3>'
                    )
                elif stripped:
                    formatted_lines.append(f'<p style="margin:8px 0;color:#333;line-height:1.6;">{stripped}</p>')
        if in_list:
            formatted_lines.append('</ul>')

        body = '\n'.join(formatted_lines)

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:680px;margin:0 auto;padding:20px;background:#f5f5f5;">
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:24px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="margin:0;font-size:22px;">Nepal News Briefing</h1>
    <p style="margin:8px 0 0;opacity:0.8;font-size:14px;">{timestamp} | {count} articles analyzed</p>
    <p style="margin:4px 0 0;opacity:0.6;font-size:11px;">Gov &bull; Gold &bull; Tech &bull; Social Media</p>
  </div>
  <div style="background:white;padding:24px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
    {body}
  </div>
  <div style="background:white;padding:20px 24px;border-top:1px solid #eee;">
    <h2 style="color:#1a1a2e;font-size:16px;margin:0 0 12px;">Read Full Articles</h2>
    {article_links_html}
  </div>
  <div style="background:white;padding:16px 24px;border-radius:0 0 12px 12px;border-top:1px solid #eee;text-align:center;">
    <p style="color:#888;font-size:12px;margin:0;">
      Automated report by Nepal News Tracker | Powered by Gemini AI<br>
      <span style="font-size:11px;">Sources: Kathmandu Post, Republica, Himalayan Times, RONB, Ashesh Gold, Techmandu &amp; more</span>
    </p>
  </div>
</body>
</html>"""

    def _to_slack_blocks(self, report_text: str, article_links_slack: str, timestamp: str, count: int) -> dict:
        return {
            "text": f"Nepal News Briefing — {timestamp}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Nepal News Briefing"}
                },
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": (f":newspaper: *{count} articles* | :clock1: {timestamp}\n"
                                f":coin: Gold | :computer: Tech | :camera: Social Media | :classical_building: Government")
                    }]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": report_text[:2500]}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": article_links_slack[:2500]}
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": ":robot_face: _Nepal News Tracker | Powered by Gemini AI_"
                    }]
                }
            ]
        }

    def _empty_report(self) -> dict:
        timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")
        msg = "No new articles found this cycle. The tracker will check again in the next scheduled run."
        return {
            "subject": f"Nepal News Briefing — {timestamp} (No updates)",
            "timestamp": timestamp,
            "article_count": 0,
            "articles": [],
            "plain_text": msg,
            "html": f"<html><body><p>{msg}</p></body></html>",
            "slack_blocks": {
                "text": msg,
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f":sleeping: {msg}"}}]
            }
        }

    def _fallback_report(self, articles: list[dict]) -> str:
        """Categorized report if Gemini API fails."""
        categories = {
            "government": [], "politics": [], "gold": [],
            "tech": [], "instagram": [], "general": [],
        }
        for a in articles:
            cat = a.get("category", "general")
            categories.setdefault(cat, []).append(a)

        lines = ["# Nepal News Summary\n",
                 f"*{len(articles)} articles collected (AI summary unavailable)*\n"]

        section_names = {
            "government": "Government & Politics",
            "politics": "Government & Politics",
            "gold": "Gold & Silver Prices",
            "tech": "Tech News",
            "instagram": "Trending (Social Media)",
            "general": "General News",
        }

        seen_sections = set()
        for cat, items in categories.items():
            if not items:
                continue
            section = section_names.get(cat, "Other")
            if section in seen_sections:
                continue
            seen_sections.add(section)
            lines.append(f"\n## {section}")
            for a in items[:5]:
                url = a.get("full_article_url", a["url"])
                lines.append(f"- **{a['title']}** ({a['source']})")
                lines.append(f"  {a.get('summary', '')[:150]}")
                lines.append(f"  Read: {url}\n")

        return "\n".join(lines)
