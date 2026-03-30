"""
Nepal News Tracker — Audio News Generator
Converts AI detailed report + all article summaries into a comprehensive
MP3 audio briefing. Podcast-style narration covering every category.
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AudioGenerator:
    """Generates comprehensive MP3 audio briefing using Google Text-to-Speech (free)."""

    def __init__(self, data_dir: str = "data"):
        self.audio_dir = os.path.join(data_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)

    def generate(self, ai_summary: str, articles: list[dict]) -> str | None:
        """
        Generate a detailed MP3 audio briefing.
        Returns the file path, or None on failure.
        """
        try:
            from gtts import gTTS
        except ImportError:
            logger.error("gTTS not installed. Run: pip install gTTS")
            return None

        try:
            script = self._build_detailed_script(ai_summary, articles)

            if not script or len(script) < 50:
                logger.warning("Script too short for audio generation")
                return None

            logger.info(f"Generating detailed audio ({len(script)} chars, ~{len(script)//150} sec)...")
            tts = gTTS(text=script, lang="en", slow=False)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.audio_dir, f"briefing_{timestamp}.mp3")
            tts.save(filepath)

            file_size = os.path.getsize(filepath) / 1024
            logger.info(f"Audio generated: {filepath} ({file_size:.0f} KB)")
            return filepath

        except Exception as e:
            logger.error(f"Audio generation failed: {type(e).__name__}: {e}")
            return None

    def _build_detailed_script(self, ai_summary: str, articles: list[dict]) -> str:
        """Build a comprehensive podcast-style spoken script."""
        parts = []

        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")

        # ── Intro ──
        parts.append(
            f"Nepal News Briefing. {date_str}, {time_str}. "
            f"Welcome to your comprehensive hourly news update. "
            f"We have {len(articles)} stories across government, stock market, "
            f"gold prices, technology, and social media. Let's get started."
        )

        # ── AI Detailed Report ──
        if ai_summary:
            parts.append("Here is the AI-generated detailed report for this hour.")
            clean = ai_summary.replace("**", "").replace("*", "")
            clean = clean.replace("#", "").replace("-", " ").strip()
            # Remove markdown-style headers but keep the text
            lines = clean.split("\n")
            for line in lines:
                line = line.strip()
                if line:
                    parts.append(line)
            parts.append("That was the overview. Now, let's go through each category in detail.")

        # ── Category-by-category detailed narration ──
        category_labels = {
            "government": "Government and Politics",
            "politics": "Government and Politics",
            "stock": "Stock Market and NEPSE",
            "gold": "Gold and Silver Prices",
            "tech": "Technology News",
            "instagram": "Trending on Instagram",
            "tiktok": "Trending on TikTok",
            "linkedin": "Business and LinkedIn Updates",
            "general": "General News",
        }

        category_intros = {
            "government": "Starting with government and politics. Here are today's developments from Nepal's political landscape.",
            "stock": "Moving to the stock market. Here's what's happening with NEPSE and the financial markets today.",
            "gold": "Now for gold and silver prices. Here are today's precious metal rates in Nepal.",
            "tech": "In technology news. Here are the latest tech developments from Nepal.",
            "instagram": "Now, what's trending on Instagram. These stories are going viral on Nepal's social media.",
            "tiktok": "Over on TikTok, here's what Nepal is talking about.",
            "linkedin": "In business news from LinkedIn. Here are the economic and professional updates.",
            "general": "And finally, some general news stories.",
        }

        # Group articles
        grouped = {}
        for a in articles:
            cat = a.get("category", "general")
            if cat == "politics":
                cat = "government"
            grouped.setdefault(cat, []).append(a)

        order = ["government", "stock", "gold", "tech", "instagram", "tiktok", "linkedin", "general"]

        for cat in order:
            items = grouped.get(cat, [])
            if not items:
                continue

            # Category intro
            intro = category_intros.get(cat, f"Next, {category_labels.get(cat, 'other news')}.")
            parts.append(intro)

            for i, a in enumerate(items):
                title = a["title"][:150]
                source = a.get("source", "Unknown")
                summary = a.get("summary", "")[:250]
                platform = a.get("platform", "")
                social_url = a.get("social_url", "")

                # Read the article
                parts.append(f"From {source}.")
                parts.append(f"{title}.")

                # Read summary if available
                if summary:
                    # Clean up summary for speech
                    clean_summary = summary.replace("|", ", ").replace("\n", " ").strip()
                    if len(clean_summary) > 20:
                        parts.append(clean_summary)

                # Mention social media source
                if platform in ("instagram", "tiktok") and social_url:
                    parts.append(
                        f"You can also find this on {platform.capitalize()}."
                    )

            # Category transition
            parts.append("")  # Small pause between categories

        # ── Outro ──
        article_count = len(articles)
        cat_count = len([c for c in order if c in grouped])
        parts.append(
            f"That concludes today's Nepal News Briefing. "
            f"We covered {article_count} stories across {cat_count} categories. "
            f"Your next briefing will arrive in one hour. "
            f"Stay informed, stay ahead. Thank you for listening."
        )

        return " ".join(p for p in parts if p)

    def cleanup_old(self, keep_latest: int = 5):
        """Remove old audio files, keeping only the latest N."""
        try:
            files = sorted(
                [os.path.join(self.audio_dir, f)
                 for f in os.listdir(self.audio_dir) if f.endswith(".mp3")],
                key=os.path.getmtime, reverse=True
            )
            for old_file in files[keep_latest:]:
                os.remove(old_file)
                logger.info(f"Cleaned up old audio: {old_file}")
        except Exception as e:
            logger.error(f"Audio cleanup error: {e}")
