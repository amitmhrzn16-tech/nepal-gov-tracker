"""
Quick test script — sends a test email and Slack message
to verify credentials are working. No Gemini/scraping needed.

Usage: GEMINI_API_KEY=x EMAIL_PASSWORD=your-app-password python3 test_send.py
"""

import os
import sys
import smtplib
import ssl
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "amitmhrzn16@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "amitmhrzn16@gmail.com").split(",")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

timestamp = datetime.now().strftime("%B %d, %Y — %I:%M %p")

# ─── Test Email ──────────────────────────────────────────────
def test_email():
    print("\n=== EMAIL TEST ===")
    if not EMAIL_PASSWORD or EMAIL_PASSWORD == "your-gmail-app-password":
        print("SKIP: EMAIL_PASSWORD not set.")
        print("  Run with: EMAIL_PASSWORD=your-app-password python3 test_send.py")
        return False

    print(f"  Sender:     {EMAIL_SENDER}")
    print(f"  Password:   {EMAIL_PASSWORD[:3]}***{EMAIL_PASSWORD[-3:]}")
    print(f"  Recipients: {EMAIL_RECIPIENTS}")

    html = f"""<html><body style="font-family:Arial;max-width:600px;margin:0 auto;">
    <div style="background:#1a1a2e;color:white;padding:20px;text-align:center;">
        <h2>Nepal News Tracker — Test Email</h2>
        <p>{timestamp}</p>
    </div>
    <div style="padding:20px;">
        <p>If you're reading this, <strong>email delivery is working!</strong></p>
        <div style="background:#e0f7e9;padding:12px;border-radius:8px;margin:12px 0;">
            <strong>Stock Market / NEPSE</strong><br>
            Sample article: NEPSE rises 15 points on Monday trading
        </div>
        <div style="background:#ede7f6;padding:12px;border-radius:8px;margin:12px 0;">
            <strong>Tech News</strong><br>
            Sample article: New smartphone launched in Nepal market
        </div>
        <div style="background:#fef9e7;padding:12px;border-radius:8px;margin:12px 0;">
            <strong>Gold & Silver</strong><br>
            Sample: Fine Gold Rs 1,45,000 per tola
        </div>
    </div></body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"TEST — Nepal News Tracker — {timestamp}"
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(EMAIL_RECIPIENTS)
        msg.attach(MIMEText("Test email from Nepal News Tracker", "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        context = ssl.create_default_context()
        print("  Connecting to Gmail SMTP...")
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            print("  Logging in...")
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            print("  Sending...")
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())

        print("  EMAIL SENT SUCCESSFULLY!")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"  EMAIL AUTH FAILED: {e}")
        print("  Fix: Use Gmail App Password from https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        print(f"  EMAIL FAILED: {type(e).__name__}: {e}")
        return False

# ─── Test Slack ──────────────────────────────────────────────
def test_slack():
    print("\n=== SLACK TEST ===")
    if not SLACK_WEBHOOK_URL or "YOUR/WEBHOOK/URL" in SLACK_WEBHOOK_URL:
        print("SKIP: SLACK_WEBHOOK_URL not set.")
        print("  Set it to test Slack delivery.")
        return False

    print(f"  Webhook: {SLACK_WEBHOOK_URL[:40]}...")

    try:
        import requests
        payload = {
            "text": f"Nepal News Tracker — Test Message ({timestamp})",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "Nepal News Tracker — Test"}},
                {"type": "section", "text": {"type": "mrkdwn",
                    "text": f"If you're reading this, *Slack delivery is working!*\n:clock1: {timestamp}"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn",
                    "text": ":classical_building: *Government* — Sample headline\n"
                            ":chart_with_upwards_trend: *Stock* — NEPSE update\n"
                            ":coin: *Gold* — Price update\n"
                            ":computer: *Tech* — Latest gadget news\n"
                            ":camera: *Instagram* — Trending\n"
                            ":musical_note: *TikTok* — Viral news\n"
                            ":briefcase: *LinkedIn* — Business update"}}
            ]
        }
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=15)
        if resp.status_code == 200 and resp.text == "ok":
            print("  SLACK SENT SUCCESSFULLY!")
            return True
        else:
            print(f"  SLACK FAILED: HTTP {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        print(f"  SLACK FAILED: {type(e).__name__}: {e}")
        return False

# ─── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Nepal News Tracker — Delivery Test")
    print(f"Time: {timestamp}")

    email_ok = test_email()
    slack_ok = test_slack()

    print(f"\n=== RESULTS ===")
    print(f"  Email: {'PASS' if email_ok else 'FAIL'}")
    print(f"  Slack: {'PASS' if slack_ok else 'FAIL'}")

    if not email_ok and not slack_ok:
        print("\nBoth failed. Check your credentials:")
        print("  EMAIL_PASSWORD — Gmail App Password (16 chars)")
        print("  SLACK_WEBHOOK_URL — Slack Incoming Webhook URL")
        sys.exit(1)
