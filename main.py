"""
Nepal Government News Tracker — Main Scheduler & Orchestrator
Runs the full pipeline: Scrape → Analyze → Report → Notify
Includes a lightweight HTTP health check server for Railway/cloud hosting.
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import config
from scraper import NewsScraper
from report_generator import ReportGenerator
from notifier import EmailNotifier, SlackNotifier

# ─── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tracker.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("NepalGovTracker")

# ─── App State (shared with health check) ────────────────────
app_state = {
    "status": "starting",
    "last_run": None,
    "articles_found": 0,
    "total_cycles": 0,
    "started_at": datetime.now().isoformat(),
}

# ─── Health Check Server (keeps Railway happy) ───────────────
class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler so Railway knows the app is alive."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        import json
        response = json.dumps({
            "status": "running",
            "service": "Nepal Government News Tracker",
            "last_run": app_state["last_run"],
            "total_cycles": app_state["total_cycles"],
            "articles_last_cycle": app_state["articles_found"],
            "started_at": app_state["started_at"],
        })
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logs


def start_health_server():
    """Start the health check server on the PORT Railway assigns."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()


# ─── Graceful Shutdown ────────────────────────────────────────
running = True

def shutdown_handler(signum, frame):
    global running
    logger.info("Shutdown signal received. Stopping after current cycle...")
    running = False

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


# ─── Pipeline ─────────────────────────────────────────────────
def run_pipeline():
    """Execute one full cycle: scrape → generate report → send notifications."""
    cycle_start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"STARTING NEWS CYCLE — {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Step 1: Scrape
    logger.info("[1/3] Scraping news sources...")
    scraper = NewsScraper()
    articles = scraper.scrape_all()

    app_state["articles_found"] = len(articles)

    if not articles:
        logger.info("No new articles found. Skipping report generation.")
        logger.info(f"Next cycle in {config.RUN_INTERVAL_MINUTES} minutes.\n")
        return

    logger.info(f"Found {len(articles)} new articles")

    # Step 2: Generate Report
    logger.info("[2/3] Generating AI-powered report...")
    generator = ReportGenerator()
    report = generator.generate(articles)
    logger.info(f"Report generated: {report['subject']}")

    # Step 3: Send Notifications
    logger.info("[3/3] Sending notifications...")

    email_notifier = EmailNotifier()
    slack_notifier = SlackNotifier()

    email_ok = email_notifier.send(report)
    slack_ok = slack_notifier.send(report)

    # Save report locally as backup
    save_report_locally(report)

    # Summary
    elapsed = (datetime.now() - cycle_start).total_seconds()
    logger.info(f"Cycle complete in {elapsed:.1f}s — "
                f"Articles: {len(articles)} | "
                f"Email: {'OK' if email_ok else 'FAIL'} | "
                f"Slack: {'OK' if slack_ok else 'FAIL'}")
    logger.info(f"Next cycle in {config.RUN_INTERVAL_MINUTES} minutes.\n")


def save_report_locally(report: dict):
    """Save each report as an HTML file for backup/archive."""
    archive_dir = os.path.join(config.DATA_DIR, "reports")
    os.makedirs(archive_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(archive_dir, f"report_{timestamp}.html")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report["html"])

    logger.info(f"Report archived: {filepath}")


# ─── Entry Point ──────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info("  NEPAL GOVERNMENT NEWS TRACKER")
    logger.info(f"  Interval: Every {config.RUN_INTERVAL_MINUTES} minutes")
    logger.info(f"  Sources: {len(config.NEWS_SOURCES)} configured")
    logger.info(f"  Email: {'ON' if config.EMAIL_ENABLED else 'OFF'}")
    logger.info(f"  Slack: {'ON' if config.SLACK_ENABLED else 'OFF'}")
    logger.info("=" * 60)

    # Start health check server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    app_state["status"] = "running"

    # Check for --once flag (run single cycle and exit)
    if "--once" in sys.argv:
        logger.info("Running single cycle (--once mode)")
        run_pipeline()
        return

    # Continuous mode
    while running:
        try:
            run_pipeline()
            app_state["total_cycles"] += 1
            app_state["last_run"] = datetime.now().isoformat()
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)

        # Wait for next cycle
        if running:
            logger.info(f"Sleeping for {config.RUN_INTERVAL_MINUTES} minutes...")
            for _ in range(config.RUN_INTERVAL_MINUTES * 60):
                if not running:
                    break
                time.sleep(1)

    logger.info("Tracker stopped. Goodbye!")


if __name__ == "__main__":
    main()
