"""
Nepal Government News Tracker — News Scraper Module
Scrapes RSS feeds, web sources, Instagram fallbacks, and gold prices.
"""

import os
import json
import hashlib
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
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
        cutoff = datetime.now() - timedelta(days=days)
        self.seen = {
            k: v for k, v in self.seen.items()
            if datetime.fromisoformat(v.get("seen_at", "2000-01-01")) > cutoff
        }
        self._save()


class NewsScraper:
    """Scrapes Nepal news from multiple source types."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
                category = source.get("category", "general")
                scrape_type = source.get("scrape_type", "")

                if scrape_type == "gold_price" and config.GOLD_ENABLED:
                    articles = self._scrape_gold_price(source)
                elif category == "instagram" and config.INSTAGRAM_ENABLED:
                    articles = self._scrape_instagram_fallback(source)
                elif source.get("rss"):
                    articles = self._scrape_rss(source)
                else:
                    articles = self._scrape_web(source)

                # Filter for relevant content (skip for gold/tech/instagram)
                if category in ("government", "politics", "general"):
                    filtered = self._filter_relevant(articles)
                else:
                    filtered = articles

                all_articles.extend(filtered)
                logger.info(f"[{source['name']}] Found {len(filtered)} articles")

            except Exception as e:
                logger.error(f"[{source['name']}] Scraping failed: {e}")

        # Deduplicate and mark as seen
        new_articles = []
        for article in all_articles:
            if not self.store.is_seen(article["url"]):
                self.store.mark_seen(article["url"], article["title"])
                new_articles.append(article)

        self.store.cleanup_old(days=7)

        logger.info(f"Total new articles: {len(new_articles)}")
        return new_articles[:config.MAX_ARTICLES_PER_REPORT]

    # ─── RSS Scraping ─────────────────────────────────────────
    def _scrape_rss(self, source: dict) -> list[dict]:
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
                    "full_article_url": entry.get("link", ""),
                }
                if article["title"] and article["url"]:
                    articles.append(article)
        except Exception as e:
            logger.error(f"RSS parse error for {source['name']}: {e}")
        return articles

    # ─── Web Scraping ─────────────────────────────────────────
    def _scrape_web(self, source: dict) -> list[dict]:
        articles = []
        try:
            resp = self.session.get(source["url"], timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for tag in soup.find_all("a", href=True):
                title_text = tag.get_text(strip=True)
                href = tag["href"]

                if not title_text or len(title_text) < 20:
                    continue
                if href.startswith("/"):
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
                    "full_article_url": href,
                })
        except Exception as e:
            logger.error(f"Web scrape error for {source['name']}: {e}")
        return articles

    # ─── Instagram Fallback (scrape their web presence) ───────
    def _scrape_instagram_fallback(self, source: dict) -> list[dict]:
        """
        Instagram blocks direct scraping, so we scrape the linked
        website/web fallback for RONB-style news portals.
        """
        articles = []
        web_url = source.get("web_fallback", "")
        ig_handle = source.get("instagram", "")

        if not web_url:
            logger.info(f"[{source['name']}] No web fallback, skipping")
            return articles

        try:
            resp = self.session.get(web_url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for article headlines in h2, h3, h4 tags
            seen_urls = set()
            for tag in soup.find_all(["h2", "h3", "h4"], limit=50):
                link = tag.find("a")
                if not link or not link.get("href"):
                    continue

                title_text = link.get_text(strip=True)
                href = link["href"]

                if not title_text or len(title_text) < 15:
                    continue
                if href.startswith("/"):
                    href = urljoin(web_url, href)
                if not href.startswith("http") or href in seen_urls:
                    continue

                seen_urls.add(href)
                articles.append({
                    "title": title_text[:200],
                    "url": href,
                    "summary": "",
                    "published": datetime.now().isoformat(),
                    "source": f"{source['name']} (@{ig_handle})",
                    "category": "instagram",
                    "full_article_url": href,
                    "instagram_url": f"https://www.instagram.com/{ig_handle}/",
                })

            logger.info(f"[{source['name']}] Scraped {len(articles)} from web fallback")
        except Exception as e:
            logger.error(f"Instagram fallback error for {source['name']}: {e}")

        return articles[:10]

    # ─── Gold Price Scraping ──────────────────────────────────
    def _scrape_gold_price(self, source: dict) -> list[dict]:
        """Scrape current gold and silver prices from Nepal sources."""
        articles = []
        try:
            resp = self.session.get(source["url"], timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            price_text = ""

            # Extract from tables
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    cell_text = " | ".join(c.get_text(strip=True) for c in cells)
                    if any(w in cell_text.lower() for w in ["gold", "silver", "hallmark", "tajabi", "fine"]):
                        price_text += cell_text + "\n"

            # Fallback: search divs and spans
            if not price_text:
                for elem in soup.find_all(["div", "span", "p"]):
                    text = elem.get_text(strip=True)
                    if re.search(r'(gold|silver|hallmark|tajabi|fine).*\d+', text, re.IGNORECASE):
                        price_text += text + "\n"
                        if len(price_text) > 300:
                            break

            if price_text:
                today = datetime.now().strftime("%B %d, %Y")
                articles.append({
                    "title": f"Nepal Gold & Silver Prices — {today}",
                    "url": source["url"],
                    "summary": price_text.strip()[:500],
                    "published": datetime.now().isoformat(),
                    "source": source["name"],
                    "category": "gold",
                    "full_article_url": source["url"],
                })
                logger.info(f"[{source['name']}] Gold prices scraped")
            else:
                logger.warning(f"[{source['name']}] Could not extract gold prices")

        except Exception as e:
            logger.error(f"Gold price scrape error for {source['name']}: {e}")
        return articles

    # ─── Helpers ──────────────────────────────────────────────
    def _filter_relevant(self, articles: list[dict]) -> list[dict]:
        relevant = []
        keywords = [t.lower() for t in config.TOPICS]
        for article in articles:
            text = f"{article['title']} {article['summary']}".lower()
            if any(kw in text for kw in keywords):
                relevant.append(article)
            elif article.get("category") in ("government", "politics"):
                relevant.append(article)
        return relevant

    def _clean_html(self, html_text: str) -> str:
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(separator=" ", strip=True)[:500]

    def _parse_date(self, date_str: str) -> str:
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
    print(f"\nFound {len(articles)} new articles:\n")
    for a in articles:
        print(f"  [{a['category'].upper():10}] [{a['source']}] {a['title'][:70]}")
        print(f"               Read full: {a.get('full_article_url', 'N/A')}\n")
