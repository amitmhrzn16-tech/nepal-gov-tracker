"""
Nepal Government News Tracker — Email & Slack Notification Module
Sends reports via Gmail SMTP (with audio attachment) and Slack Webhooks.
"""

import json
import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests

import config

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends HTML email reports via Gmail SMTP with optional audio attachment."""

    def send(self, report: dict, audio_path: str = None) -> bool:
        if not config.EMAIL_ENABLED:
            logger.info("Email notifications disabled in config")
            return False

        # Log config for debugging (mask password)
        pw = config.EMAIL_PASSWORD
        masked = pw[:3] + "***" + pw[-3:] if len(pw) > 6 else "***"
        logger.info(f"Email config — Sender: {config.EMAIL_SENDER}, "
                     f"Password set: {len(pw)} chars ({masked}), "
                     f"Recipients: {config.EMAIL_RECIPIENTS}")

        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = report["subject"]
            msg["From"] = config.EMAIL_SENDER
            msg["To"] = ", ".join(config.EMAIL_RECIPIENTS)

            # Create alternative part for text/html
            alt_part = MIMEMultipart("alternative")
            alt_part.attach(MIMEText(report["plain_text"], "plain", "utf-8"))
            alt_part.attach(MIMEText(report["html"], "html", "utf-8"))
            msg.attach(alt_part)

            # Attach audio file if available
            if audio_path and os.path.exists(audio_path):
                try:
                    with open(audio_path, "rb") as audio_file:
                        audio_attachment = MIMEBase("audio", "mpeg")
                        audio_attachment.set_payload(audio_file.read())
                        encoders.encode_base64(audio_attachment)
                        filename = os.path.basename(audio_path)
                        audio_attachment.add_header(
                            "Content-Disposition",
                            f"attachment; filename=\"Nepal_News_Briefing.mp3\""
                        )
                        msg.attach(audio_attachment)
                        file_size = os.path.getsize(audio_path) / 1024
                        logger.info(f"Audio attached: {filename} ({file_size:.0f} KB)")
                except Exception as e:
                    logger.error(f"Failed to attach audio: {e}")

            # Use SSL context for secure connection
            context = ssl.create_default_context()

            logger.info("Connecting to Gmail SMTP...")
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                logger.info("TLS established, logging in...")
                server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
                logger.info("Login successful, sending email...")
                server.sendmail(
                    config.EMAIL_SENDER,
                    config.EMAIL_RECIPIENTS,
                    msg.as_string()
                )

            logger.info(f"Email sent successfully to {config.EMAIL_RECIPIENTS}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                f"EMAIL AUTH FAILED: {e}\n"
                "Fix: Use a Gmail App Password (NOT your regular password).\n"
                "1. Enable 2-Step Verification at https://myaccount.google.com/security\n"
                "2. Generate App Password at https://myaccount.google.com/apppasswords\n"
                "3. Set EMAIL_PASSWORD in Railway Variables to the 16-char password (no spaces)"
            )
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            logger.error(f"Email send failed: {type(e).__name__}: {e}")
            return False


class SlackNotifier:
    """Sends formatted reports to Slack via Incoming Webhook."""

    def send(self, report: dict) -> bool:
        if not config.SLACK_ENABLED:
            logger.info("Slack notifications disabled in config")
            return False

        # Log config for debugging
        url = config.SLACK_WEBHOOK_URL
        masked_url = url[:40] + "..." if len(url) > 40 else url
        logger.info(f"Slack config — Webhook: {masked_url}")

        if "YOUR/WEBHOOK/URL" in url:
            logger.error("SLACK NOT CONFIGURED: Webhook URL still has placeholder value. "
                        "Set SLACK_WEBHOOK_URL in Railway Variables.")
            return False

        try:
            payload = report["slack_blocks"]

            logger.info("Sending to Slack...")
            resp = requests.post(
                config.SLACK_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )

            if resp.status_code == 200 and resp.text == "ok":
                logger.info("Slack message sent successfully!")
                return True
            else:
                logger.error(f"SLACK FAILED: HTTP {resp.status_code} — {resp.text}\n"
                           "If 'invalid_payload': check Slack block format\n"
                           "If 'channel_not_found': webhook channel was deleted\n"
                           "If '403': webhook was revoked, create a new one")
                return False

        except requests.exceptions.ConnectionError as e:
            logger.error(f"SLACK CONNECTION ERROR: Cannot reach Slack. {e}")
            return False
        except Exception as e:
            logger.error(f"Slack send failed: {type(e).__name__}: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

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

    print("\nTesting Slack...")
    slack.send(sample_report)
