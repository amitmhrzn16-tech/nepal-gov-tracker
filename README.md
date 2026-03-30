# Nepal Government News Tracker

Automated system that tracks Nepal government news, generates AI-powered summaries using Claude, and delivers hourly reports via email and Slack.

## Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
cd nepal-gov-tracker
pip install -r requirements.txt
```

### 2. Get Your API Keys

You need three things:

**A) Anthropic API Key (for Claude AI reports)**
- Go to https://console.anthropic.com
- Create an account and generate an API key

**B) Gmail App Password (for email delivery)**
- Go to https://myaccount.google.com/apppasswords
- Select "Mail" and generate a password
- ⚠️ Use this App Password, NOT your regular Gmail password

**C) Slack Webhook URL (for Slack messages)**
- Go to https://api.slack.com/apps → Create New App
- Go to "Incoming Webhooks" → Activate → Add to a channel
- Copy the Webhook URL

### 3. Configure

Open `config.py` and fill in:

```python
ANTHROPIC_API_KEY = "sk-ant-..."
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"  # Gmail App Password
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/..."
```

### 4. Run

```bash
# Test a single cycle first
python main.py --once

# Run continuously (hourly)
python main.py
```

## How It Works

```
Every hour:
  1. SCRAPE — Pulls news from 5 Nepal news sources (RSS + web)
  2. FILTER — Keeps only government-related articles
  3. ANALYZE — Claude AI generates a structured briefing
  4. DELIVER — Sends HTML email + Slack message
  5. ARCHIVE — Saves report locally in data/reports/
```

## Project Structure

```
nepal-gov-tracker/
├── config.py              # All settings and API keys
├── main.py                # Scheduler and orchestrator
├── scraper.py             # News scraper (RSS + web)
├── report_generator.py    # Claude AI report generation
├── notifier.py            # Email + Slack delivery
├── requirements.txt       # Python dependencies
├── tracker.log            # Auto-generated log file
└── data/
    ├── seen_articles.json # Dedup tracker
    └── reports/           # Archived HTML reports
```

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `RUN_INTERVAL_MINUTES` | 60 | How often to check (minutes) |
| `MAX_ARTICLES_PER_REPORT` | 20 | Max articles per report |
| `EMAIL_ENABLED` | True | Toggle email notifications |
| `SLACK_ENABLED` | True | Toggle Slack notifications |

## Running as a Background Service

### macOS (launchd)

```bash
# Create a plist file
cat > ~/Library/LaunchAgents/com.nepal.govtracker.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nepal.govtracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/nepal-gov-tracker/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load it
launchctl load ~/Library/LaunchAgents/com.nepal.govtracker.plist
```

### Linux (systemd)

```bash
sudo cat > /etc/systemd/system/nepal-gov-tracker.service << 'EOF'
[Unit]
Description=Nepal Government News Tracker
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/nepal-gov-tracker
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable nepal-gov-tracker
sudo systemctl start nepal-gov-tracker
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

## Stopping the Tracker

Press `Ctrl+C` — it will finish the current cycle and shut down gracefully.
# nepal-gov-tracker
