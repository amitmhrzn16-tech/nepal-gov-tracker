"""
Nepal Government News Tracker — Main Scheduler & Orchestrator
Runs the full pipeline: Scrape → Analyze → Report → Notify
Uses APScheduler for reliable cron-based scheduling.
Includes a lightweight HTTP health check server for Railway/cloud hosting.
"""

import os
import sys
import json
import signal
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from scraper import NewsScraper
from report_generator import ReportGenerator
from notifier import EmailNotifier, SlackNotifier
from audio_generator import AudioGenerator

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
    "next_run": None,
    "articles_found": 0,
    "total_cycles": 0,
    "started_at": datetime.now().isoformat(),
    "last_error": None,
}

# ─── Health Check Server (keeps Railway happy) ───────────────
class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler so Railway knows the app is alive."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = json.dumps(app_state, indent=2)
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logs


def start_health_server():
    """Start the health check server on the PORT Railway assigns."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()


# ─── Pipeline ─────────────────────────────────────────────────
def run_pipeline():
    """Execute one full cycle: scrape → generate report → send notifications."""
    cycle_start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"STARTING NEWS CYCLE — {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        # Step 1: Scrape
        logger.info("[1/3] Scraping news sources...")
        scraper = NewsScraper()
        articles = scraper.scrape_all()

        app_state["articles_found"] = len(articles)

        if not articles:
            logger.info("No new articles found. Skipping report generation.")
            app_state["total_cycles"] += 1
            app_state["last_run"] = datetime.now().isoformat()
            return

        logger.info(f"Found {len(articles)} new articles")

        # Step 2: Generate Report
        logger.info("[2/3] Generating AI-powered report...")
        generator = ReportGenerator()
        report = generator.generate(articles)
        logger.info(f"Report generated: {report['subject']}")

        # Step 3: Generate Audio Briefing
        logger.info("[3/4] Generating audio briefing...")
        audio_path = None
        if config.AUDIO_ENABLED:
            audio_gen = AudioGenerator(config.DATA_DIR)
            ai_summary = report.get("plain_text", "")[:500]
            audio_path = audio_gen.generate(ai_summary, articles)
            if audio_path:
                logger.info(f"Audio ready: {audio_path}")
            audio_gen.cleanup_old(keep_latest=5)

        # Step 4: Send Notifications
        logger.info("[4/4] Sending notifications...")

        email_notifier = EmailNotifier()
        slack_notifier = SlackNotifier()

        email_ok = email_notifier.send(report, audio_path=audio_path)
        slack_ok = slack_notifier.send(report)

        # Save report locally as backup
        save_report_locally(report)

        # Summary
        elapsed = (datetime.now() - cycle_start).total_seconds()
        logger.info(f"Cycle complete in {elapsed:.1f}s — "
                    f"Articles: {len(articles)} | "
                    f"Email: {'OK' if email_ok else 'FAIL'} | "
                    f"Slack: {'OK' if slack_ok else 'FAIL'}")

        app_state["total_cycles"] += 1
        app_state["last_run"] = datetime.now().isoformat()
        app_state["last_error"] = None

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        app_state["last_error"] = f"{type(e).__name__}: {str(e)}"


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
    interval = config.RUN_INTERVAL_MINUTES

    logger.info("=" * 60)
    logger.info("  NEPAL GOVERNMENT NEWS TRACKER")
    logger.info(f"  Schedule: Every {interval} minutes (APScheduler)")
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

    # ─── APScheduler (reliable cron-based scheduling) ─────────
    scheduler = BackgroundScheduler()

    # Run pipeline every N minutes
    scheduler.add_job(
        run_pipeline,
        trigger=IntervalTrigger(minutes=interval),
        id="news_pipeline",
        name=f"Nepal Gov News Pipeline (every {interval}min)",
        max_instances=1,  # Prevent overlapping runs
        misfire_grace_time=300,  # Allow 5 min grace for missed runs
    )

    scheduler.start()
    logger.info(f"Scheduler started — pipeline will run every {interval} minutes")

    # Run first cycle immediately
    logger.info("Running first cycle now...")
    run_pipeline()

    # Update next run time in status
    job = scheduler.get_job("news_pipeline")
    if job and job.next_run_time:
        app_state["next_run"] = job.next_run_time.isoformat()
        logger.info(f"Next scheduled run: {job.next_run_time}")

    # Keep main thread alive
    shutdown_event = threading.Event()

    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received...")
        scheduler.shutdown(wait=False)
        shutdown_event.set()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Block until shutdown
    shutdown_event.wait()
    logger.info("Tracker stopped. Goodbye!")


if __name__ == "__main__":
    main()
