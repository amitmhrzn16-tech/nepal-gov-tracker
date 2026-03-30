"""
Nepal Government News Tracker — News Scraper Module
Scrapes RSS feeds and web sources for Nepal government news.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
import feedparser
import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


class ArticleStore:
    """Tracks which articles we've already seen to avoid duplicates."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.seen_file = os.path.join(data_dir, "seen_articles.json")
        os.makedirs(data_dir, exist_ok=True)
        self.seen = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.seen_file):
            try:
                with open(self.seen_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        with open(self.seen_file, "w") as f:
            json.dump(self.seen, f, indent=2, default=str)

    def _hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def is_seen(self, url: str) -> bool:
        return self._hash(url) in self.seen

    def mark_seen(self, url: str, title: str):
        self.seen[self._hash(url)] = {
            "url": url,
            "title": title,
            "seen_at": datetime.now().isoformat()
        }
        self._save()

    def cleanup_old(self, days: int = 7):
        """Remove entries older than N days to keep the file small."""
        cutoff = datetime.now() - timedelta(days=days)
        self.seen = {
            k: v for k, v in self.seen.items()
            if datetime.fromisoformat(v.get("seen_at", "2000-01-01")) > cutoff
        }
        self._save()


class NewsScraper:
    """Scrapes Nepal government news from multiple sources."""

    HEADERS = {
        "User-Agent": "NepalGovTracker/1.0 (News Aggregator; +https://github.com)"
    }

    def __init__(self):
        self.store = ArticleStore(config.DATA_DIR)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def scrape_all(self) -> list[dict]:
        """Scrape all configured news sources. Returns list of new articles."""
        all_articles = []

        for source in config.NEWS_SOURCES:
            try:
                if source.get("rss"):
                    articles = self._scrape_rss(source)
                else:
                    articles = self._scrape_web(source)

                # Filter for Nepal government-related content
                filtered = self._filter_relevant(articles)
                all_articles.extend(filtered)
                logger.info(f"[{source['name']}] Found {len(filtered)} relevant articles")

            except Exception as e:
                logger.error(f"[{source['name']}] Scraping failed: {e}")

        # Deduplicate and mark as seen
        new_articles = []
        for article in all_articles:
            if not self.store.is_seen(article["url"]):
                self.store.mark_seen(article["url"], article["title"])
                new_articles.append(article)

        # Cleanup old entries periodically
        self.store.cleanup_old(days=7)

        logger.info(f"Total new articles: {len(new_articles)}")
        return new_articles[:config.MAX_ARTICLES_PER_REPORT]

    def _scrape_rss(self, source: dict) -> list[dict]:
        """Parse an RSS feed for articles."""
        articles = []
        try:
            feed = feedparser.parse(source["rss"])
            for entry in feed.entries[:30]:
                article = {
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "summary": self._clean_html(entry.get("summary", entry.get("description", ""))),
                    "published": self._parse_date(entry.get("published", entry.get("updated", ""))),
                    "source": source["name"],
                    "category": source.get("category", "general"),
                }
                if article["title"] and article["url"]:
                    articles.append(article)
        except Exception as e:
            logger.error(f"RSS parse error for {source['name']}: {e}")

        return articles

    def _scrape_web(self, source: dict) -> list[dict]:
        """Fallback: scrape the webpage directly for article links."""
        articles = []
        try:
            resp = self.session.get(source["url"], timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for common article patterns
            for tag in soup.find_all("a", href=True):
                title_text = tag.get_text(strip=True)
                href = tag["href"]

                if not title_text or len(title_text) < 20:
                    continue

                # Make URL absolute
                if href.startswith("/"):
                    from urllib.parse import urljoin
                    href = urljoin(source["url"], href)

                if not href.startswith("http"):
                    continue

                articles.append({
                    "title": title_text[:200],
                    "url": href,
                    "summary": "",
                    "published": datetime.now().isoformat(),
                    "source": source["name"],
                    "category": source.get("category", "general"),
                })

        except Exception as e:
            logger.error(f"Web scrape error for {source['name']}: {e}")

        return articles

    def _filter_relevant(self, articles: list[dict]) -> list[dict]:
        """Keep only articles related to Nepal government topics."""
        relevant = []
        keywords = [t.lower() for t in config.TOPICS]

        for article in articles:
            text = f"{article['title']} {article['summary']}".lower()
            if any(kw in text for kw in keywords):
                relevant.append(article)
            # Also include articles from government-specific categories
            elif article.get("category") in ("government", "politics"):
                relevant.append(article)

        return relevant

    def _clean_html(self, html_text: str) -> str:
        """Strip HTML tags from text."""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(separator=" ", strip=True)[:500]

    def _parse_date(self, date_str: str) -> str:
        """Try to parse a date string, return ISO format or original."""
        if not date_str:
            return datetime.now().isoformat()
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).isoformat()
        except Exception:
            return date_str


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = NewsScraper()
    articles = scraper.scrape_all()
    print(f"\nFound {len(articles)} new articles:")
    for a in articles:
        print(f"  [{a['source']}] {a['title'][:80]}")
