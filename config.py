"""
Nepal Government News Tracker — Configuration
Reads from environment variables (for cloud deployment) with local fallbacks.
"""

import os

# ─── ANTHROPIC (Claude AI for summarization) ───────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-api-key")
# Get from https://console.anthropic.com
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ─── EMAIL SETTINGS (Gmail SMTP) ──────────────────────────────
EMAIL_ENABLED = True
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "amitmhrzn16@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your-gmail-app-password")
# Use App Password, NOT your real password
# → Go to https://myaccount.google.com/apppasswords to generate one
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "amitmhrzn16@gmail.com").split(",")

# ─── SLACK SETTINGS ───────────────────────────────────────────
SLACK_ENABLED = True
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
# → Create at https://api.slack.com/messaging/webhooks

# ─── SCHEDULER ────────────────────────────────────────────────
RUN_INTERVAL_MINUTES = 60  # How often to check for news (default: every hour)

# ─── NEWS SOURCES ─────────────────────────────────────────────
NEWS_SOURCES = [
    {
        "name": "The Kathmandu Post",
        "url": "https://kathmandupost.com/national",
        "rss": "https://kathmandupost.com/rss",
        "category": "general"
    },
    {
        "name": "Republica",
        "url": "https://myrepublica.nagariknetwork.com/category/politics",
        "rss": "https://myrepublica.nagariknetwork.com/rss",
        "category": "politics"
    },
    {
        "name": "The Himalayan Times",
        "url": "https://thehimalayantimes.com/nepal",
        "rss": "https://thehimalayantimes.com/feed",
        "category": "general"
    },
    {
        "name": "Nepal News (English)",
        "url": "https://english.onlinekhabar.com/category/government",
        "rss": "https://english.onlinekhabar.com/feed",
        "category": "government"
    },
    {
        "name": "Setopati English",
        "url": "https://en.setopati.com/political",
        "rss": "https://en.setopati.com/feed",
        "category": "politics"
    },
]

# ─── TRACKING TOPICS ─────────────────────────────────────────
TOPICS = [
    "nepal government",
    "nepal parliament",
    "nepal prime minister",
    "nepal cabinet",
    "nepal budget",
    "nepal economy",
    "nepal policy",
    "nepal legislation",
    "nepal ministry",
    "nepal election",
    "nepal foreign affairs",
    "nepal trade",
    "nepal political party",
]

# ─── REPORT SETTINGS ─────────────────────────────────────────
MAX_ARTICLES_PER_REPORT = 20
REPORT_LANGUAGE = "english"
DATA_DIR = "data"  # Where to store scraped articles and history
