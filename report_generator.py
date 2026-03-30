"""
Nepal Government News Tracker — AI Report Generator
Uses Claude API to generate structured, summarized news reports.
"""

import logging
from datetime import datetime
from anthropic import Anthropic

import config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates AI-powered news reports using Claude."""

    def __init__(self):
        # Log API key status for debugging
        key = config.ANTHROPIC_API_KEY
        if key == "your-anthropic-api-key" or not key:
            logger.error("ANTHROPIC_API_KEY is NOT set! Add it to Railway Variables.")
        else:
            masked = key[:10] + "..." + key[-4:]
            logger.info(f"Anthropic API key loaded: {masked}")
            logger.info(f"Using model: {config.CLAUDE_MODEL}")

        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def generate(self, articles: list[dict]) -> dict:
        """
        Generate a structured report from articles.
        Returns dict with 'subject', 'html', 'plain_text', and 'slack_blocks'.
        """
        if not articles:
            return self._empty_report()

        # Build context for Claude
        articles_text = self._format_articles_for_prompt(articles)
        timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")

        prompt = f"""You are a Nepal government news analyst. Analyze these recent news articles and create a structured briefing report.

ARTICLES:
{articles_text}

Create a report with these sections:
1. **HEADLINE SUMMARY** — 2-3 sentence overview of the most important developments
2. **KEY DEVELOPMENTS** — Bullet points of major government actions, policy changes, or political events
3. **ECONOMIC & BUDGET** — Any economic, trade, or budget-related updates
4. **POLITICAL LANDSCAPE** — Party dynamics, parliamentary proceedings, cabinet changes
5. **UPCOMING / WATCH LIST** — Things to monitor based on current trends

Rules:
- Be factual and concise
- Cite the source name for each point
- If a section has no relevant news, write "No updates this hour"
- Keep the total report under 500 words
- Use professional, neutral tone"""

        try:
            logger.info(f"Calling Claude API (model: {config.CLAUDE_MODEL})...")
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            report_text = response.content[0].text
            logger.info(f"Claude API success! Report length: {len(report_text)} chars")
        except Exception as e:
            logger.error(f"CLAUDE API FAILED: {type(e).__name__}: {e}")
            logger.error("Possible fixes:\n"
                        "  1. Check ANTHROPIC_API_KEY is correct in Railway Variables\n"
                        "  2. Make sure your API account has credits at console.anthropic.com\n"
                        "  3. The key should start with 'sk-ant-'")
            report_text = self._fallback_report(articles)

        subject = f"Nepal Gov Update — {timestamp}"

        return {
            "subject": subject,
            "timestamp": timestamp,
            "article_count": len(articles),
            "plain_text": report_text,
            "html": self._to_html(report_text, timestamp, len(articles)),
            "slack_blocks": self._to_slack_blocks(report_text, timestamp, len(articles)),
        }

    def _format_articles_for_prompt(self, articles: list[dict]) -> str:
        lines = []
        for i, a in enumerate(articles, 1):
            lines.append(
                f"[{i}] Source: {a['source']}\n"
                f"    Title: {a['title']}\n"
                f"    Summary: {a.get('summary', 'N/A')[:300]}\n"
                f"    Published: {a.get('published', 'Unknown')}\n"
                f"    URL: {a['url']}\n"
            )
        return "\n".join(lines)

    def _to_html(self, report_text: str, timestamp: str, count: int) -> str:
        """Convert the plain text report to a styled HTML email."""
        # Convert markdown-style formatting to HTML
        import re
        html_body = report_text
        # Bold
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
        # Bullets
        lines = html_body.split('\n')
        formatted_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- ') or stripped.startswith('• '):
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
  <div style="background:#1a1a2e;color:white;padding:24px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="margin:0;font-size:22px;">Nepal Government News Tracker</h1>
    <p style="margin:8px 0 0;opacity:0.8;font-size:14px;">{timestamp} | {count} articles analyzed</p>
  </div>
  <div style="background:white;padding:24px;border-radius:0 0 12px 12px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
    {body}
  </div>
  <div style="text-align:center;padding:16px;color:#888;font-size:12px;">
    Automated report by Nepal Gov Tracker | Powered by Claude AI
  </div>
</body>
</html>"""

    def _to_slack_blocks(self, report_text: str, timestamp: str, count: int) -> dict:
        """Convert report to Slack message format."""
        return {
            "text": f"Nepal Gov Update — {timestamp}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Nepal Government News Update"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f":newspaper: *{count} articles analyzed* | :clock1: {timestamp}"
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": report_text[:2900]  # Slack block limit ~3000 chars
                    }
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": ":robot_face: _Automated report by Nepal Gov Tracker | Powered by Claude AI_"
                        }
                    ]
                }
            ]
        }

    def _empty_report(self) -> dict:
        timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")
        msg = "No new Nepal government news articles found in this cycle. The tracker will check again in the next scheduled run."
        return {
            "subject": f"Nepal Gov Update — {timestamp} (No new updates)",
            "timestamp": timestamp,
            "article_count": 0,
            "plain_text": msg,
            "html": f"<html><body><p>{msg}</p></body></html>",
            "slack_blocks": {
                "text": msg,
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f":sleeping: {msg}"}}
                ]
            }
        }

    def _fallback_report(self, articles: list[dict]) -> str:
        """Simple report if Claude API fails."""
        lines = ["# Nepal Government News Summary\n",
                 f"*{len(articles)} articles collected (AI summary unavailable)*\n"]
        for a in articles[:10]:
            lines.append(f"- **{a['title']}** ({a['source']})\n  {a.get('summary', '')[:150]}\n")
        return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test with sample data
    sample = [
        {
            "title": "Nepal Cabinet approves new fiscal year budget",
            "url": "https://example.com/1",
            "summary": "The Nepal government has approved a new budget focusing on infrastructure development.",
            "published": datetime.now().isoformat(),
            "source": "The Kathmandu Post",
            "category": "government"
        }
    ]
    gen = ReportGenerator()
    report = gen.generate(sample)
    print(report["plain_text"])
