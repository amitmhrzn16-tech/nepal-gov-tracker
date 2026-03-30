"""
Nepal Government News Tracker — Configuration
Reads from environment variables (for cloud deployment) with local fallbacks.
"""

import os

# ─── GOOGLE GEMINI (Free AI for summarization) ───────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key")
# Get FREE from https://aistudio.google.com/apikey (no credit card needed)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Free tier: 1500 requests/day, 15 requests/minute

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

# ─── AUDIO TTS ────────────────────────────────────────────────
AUDIO_ENABLED = True
# Uses gTTS (Google Text-to-Speech) — completely free, no API key needed

# ─── SCHEDULER ────────────────────────────────────────────────
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "60"))

# ─── NEWS SOURCES ─────────────────────────────────────────────
NEWS_SOURCES = [
    # ── Government & Politics ──
    {
        "name": "The Kathmandu Post",
        "url": "https://kathmandupost.com/national",
        "rss": "https://kathmandupost.com/rss",
        "category": "government"
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
        "category": "government"
    },
    {
        "name": "Online Khabar (English)",
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
    {
        "name": "RSS Nepal (National News Agency)",
        "url": "https://www.rssnepal.com/",
        "rss": None,
        "category": "government"
    },

    # ── Instagram News Portals ──
    {
        "name": "Routine of Nepal Banda (RONB)",
        "url": "https://www.instagram.com/routineofnepalbanda/",
        "rss": None,
        "instagram": "routineofnepalbanda",
        "web_fallback": "https://english.onlinekhabar.com/",
        "category": "instagram"
    },
    {
        "name": "Nepal Live Today",
        "url": "https://www.instagram.com/nepallivetoday/",
        "rss": None,
        "instagram": "nepallivetoday",
        "web_fallback": "https://nepallivetoday.com/",
        "category": "instagram"
    },
    {
        "name": "Hamro Patro News",
        "url": "https://www.instagram.com/hamropatroofficial/",
        "rss": None,
        "instagram": "hamropatroofficial",
        "web_fallback": "https://www.hamropatro.com/news",
        "category": "instagram"
    },

    # ── TikTok News Portals ──
    {
        "name": "RONB TikTok",
        "url": "https://www.tiktok.com/@routineofnepalbanda",
        "rss": None,
        "tiktok": "routineofnepalbanda",
        "web_fallback": "https://english.onlinekhabar.com/trending",
        "category": "tiktok"
    },
    {
        "name": "Sajan Shrestha (News TikTok)",
        "url": "https://www.tiktok.com/@saabornepal",
        "rss": None,
        "tiktok": "saabornepal",
        "web_fallback": "https://english.onlinekhabar.com/category/social",
        "category": "tiktok"
    },

    # ── LinkedIn News / Business ──
    {
        "name": "Nepal Economic Forum",
        "url": "https://www.linkedin.com/company/nepal-economic-forum/",
        "rss": None,
        "linkedin": True,
        "web_fallback": "https://nepaleconomicforum.org/",
        "category": "linkedin"
    },
    {
        "name": "Invest Nepal",
        "url": "https://www.linkedin.com/company/invest-nepal/",
        "rss": None,
        "linkedin": True,
        "web_fallback": "https://english.onlinekhabar.com/category/business",
        "category": "linkedin"
    },

    # ── Gold & Silver Prices ──
    {
        "name": "Nepal Gold Price (Ashesh)",
        "url": "https://www.ashesh.com.np/gold/",
        "rss": None,
        "category": "gold",
        "scrape_type": "gold_price"
    },
    {
        "name": "NepseAlpha Gold",
        "url": "https://nepsealpha.com/gold-price",
        "rss": None,
        "category": "gold",
        "scrape_type": "gold_price"
    },

    # ── Tech News ──
    {
        "name": "Gadgets In Nepal",
        "url": "https://gadgetsinnepal.com.np/",
        "rss": "https://gadgetsinnepal.com.np/feed/",
        "category": "tech"
    },
    {
        "name": "Techmandu",
        "url": "https://techmandu.com/",
        "rss": "https://techmandu.com/feed/",
        "category": "tech"
    },
    {
        "name": "TechPana",
        "url": "https://www.techpana.com/",
        "rss": "https://www.techpana.com/feed/",
        "category": "tech"
    },
    {
        "name": "ICT Frame",
        "url": "https://ictframe.com/",
        "rss": "https://ictframe.com/feed/",
        "category": "tech"
    },

    # ── Stock Market / NEPSE ──
    {
        "name": "ShareSansar",
        "url": "https://www.sharesansar.com/category/latest",
        "rss": None,
        "category": "stock"
    },
    {
        "name": "NepseAlpha News",
        "url": "https://nepsealpha.com/news",
        "rss": None,
        "category": "stock"
    },
    {
        "name": "Merolagani",
        "url": "https://merolagani.com/NewsList.aspx",
        "rss": None,
        "category": "stock"
    },
]

# ─── TRACKING TOPICS ─────────────────────────────────────────
TOPICS = [
    # Government & Politics
    "nepal government", "nepal parliament", "nepal prime minister",
    "nepal cabinet", "nepal budget", "nepal economy",
    "nepal policy", "nepal legislation", "nepal ministry",
    "nepal election", "nepal foreign affairs", "nepal trade",
    "nepal political party", "nepal supreme court",
    # Gold & Economy
    "gold price", "gold rate", "silver price", "nepal rastra bank",
    "exchange rate", "remittance", "nepse", "stock market",
    # Tech
    "tech", "startup", "digital nepal", "internet", "telecom",
    "ntc", "ncell", "smartphone", "app", "ai", "fintech",
]

# ─── INSTAGRAM SCRAPING ─────────────────────────────────────
# Instagram doesn't allow direct scraping, so we use web fallbacks
# and search for RONB-style content from their linked websites
INSTAGRAM_ENABLED = True

# ─── GOLD PRICE SETTINGS ────────────────────────────────────
GOLD_ENABLED = True
GOLD_API_URL = os.getenv("GOLD_API_URL", "https://www.ashesh.com.np/gold/")

# ─── REPORT SETTINGS ─────────────────────────────────────────
MAX_ARTICLES_PER_REPORT = 100  # Show all articles across all categories
REPORT_LANGUAGE = "english"
DATA_DIR = "data"
