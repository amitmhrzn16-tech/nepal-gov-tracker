"""
Nepal News Tracker — Audio News Generator
Converts AI summary + headlines into an MP3 audio file using gTTS (free).
Users can listen to the news briefing as a podcast-style audio note.
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AudioGenerator:
    """Generates MP3 audio of the news briefing using Google Text-to-Speech (free)."""

    def __init__(self, data_dir: str = "data"):
        self.audio_dir = os.path.join(data_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)

    def generate(self, ai_summary: str, articles: list[dict]) -> str | None:
        """
        Generate an MP3 audio file of the news briefing.
        Returns the file path, or None on failure.
        """
        try:
            from gtts import gTTS
        except ImportError:
            logger.error("gTTS not installed. Run: pip install gTTS")
            return None

        try:
            # Build the spoken script
            script = self._build_script(ai_summary, articles)

            if not script or len(script) < 50:
                logger.warning("Script too short for audio generation")
                return None

            # Generate audio
            logger.info(f"Generating audio ({len(script)} chars)...")
            tts = gTTS(text=script, lang="en", slow=False)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.audio_dir, f"briefing_{timestamp}.mp3")
            tts.save(filepath)

            file_size = os.path.getsize(filepath) / 1024  # KB
            logger.info(f"Audio generated: {filepath} ({file_size:.0f} KB)")
            return filepath

        except Exception as e:
            logger.error(f"Audio generation failed: {type(e).__name__}: {e}")
            return None

    def _build_script(self, ai_summary: str, articles: list[dict]) -> str:
        """Build a natural-sounding spoken script from the news data."""
        parts = []

        # Intro
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%B %d, %Y")
        parts.append(
            f"Nepal News Briefing. {date_str}, {time_str}. "
            f"Here's your hourly news update."
        )

        # AI Summary
        if ai_summary:
            parts.append("First, the top summary.")
            # Clean up markdown for speech
            clean = ai_summary.replace("**", "").replace("*", "")
            clean = clean.replace("#", "").replace("-", "").strip()
            parts.append(clean)

        # Category headlines
        category_labels = {
            "government": "Government and Politics",
            "politics": "Government and Politics",
            "stock": "Stock Market and NEPSE",
            "gold": "Gold and Silver Prices",
            "tech": "Technology News",
            "instagram": "Trending on Social Media",
            "tiktok": "Trending on TikTok",
            "linkedin": "Business and LinkedIn News",
            "general": "General News",
        }

        # Group articles by category
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

            label = category_labels.get(cat, "Other News")
            parts.append(f"Now, {label}.")

            for a in items[:4]:
                title = a["title"][:120]
                source = a.get("source", "")
                summary = a.get("summary", "")[:100]

                parts.append(f"From {source}: {title}.")
                if summary and cat == "gold":
                    parts.append(summary)

        # Outro
        parts.append(
            "That's your Nepal news briefing. "
            "The next update will arrive in one hour. Stay informed."
        )

        return " ".join(parts)

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
