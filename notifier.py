"""
Nepal Government News Tracker — Email & Slack Notification Module
Sends reports via Gmail SMTP and Slack Webhooks.
"""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

import config

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends HTML email reports via Gmail SMTP."""

    def send(self, report: dict) -> bool:
        if not config.EMAIL_ENABLED:
            logger.info("Email notifications disabled in config")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = report["subject"]
            msg["From"] = config.EMAIL_SENDER
            msg["To"] = ", ".join(config.EMAIL_RECIPIENTS)

            # Attach both plain text and HTML versions
            msg.attach(MIMEText(report["plain_text"], "plain"))
            msg.attach(MIMEText(report["html"], "html"))

            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
                server.sendmail(
                    config.EMAIL_SENDER,
                    config.EMAIL_RECIPIENTS,
                    msg.as_string()
                )

            logger.info(f"Email sent to {len(config.EMAIL_RECIPIENTS)} recipients")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Email auth failed. Make sure you're using a Gmail App Password, "
                "not your regular password. Generate one at: "
                "https://myaccount.google.com/apppasswords"
            )
            return False
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False


class SlackNotifier:
    """Sends formatted reports to Slack via Incoming Webhook."""

    def send(self, report: dict) -> bool:
        if not config.SLACK_ENABLED:
            logger.info("Slack notifications disabled in config")
            return False

        try:
            payload = report["slack_blocks"]

            resp = requests.post(
                config.SLACK_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if resp.status_code == 200 and resp.text == "ok":
                logger.info("Slack message sent successfully")
                return True
            else:
                logger.error(f"Slack API error: {resp.status_code} — {resp.text}")
                return False

        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with a sample report
    sample_report = {
        "subject": "Test — Nepal Gov Update",
        "timestamp": "March 30, 2026 — 02:00 PM",
        "article_count": 3,
        "plain_text": "This is a test report.\n\n- Item 1\n- Item 2\n- Item 3",
        "html": "<html><body><h1>Test Report</h1><p>This is a test.</p></body></html>",
        "slack_blocks": {
            "text": "Test Nepal Gov Update",
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "This is a *test report*."}}
            ]
        }
    }

    email = EmailNotifier()
    slack = SlackNotifier()

    print("Testing email...")
    email.send(sample_report)

    print("Testing Slack...")
    slack.send(sample_report)
