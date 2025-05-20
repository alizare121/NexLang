import os
import json
import logging

logger = logging.getLogger(__name__)

class TranslationCache:
    def __init__(self, cache_file="translation_cache.json"):
        """Initialize the translation cache."""
        self.cache_file = cache_file
        self.cache = {}
        self.load_cache()

    def load_cache(self):
        """Load the cache from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} translation entries from cache")
            else:
                logger.info("No cache file found, starting with empty cache")
                self.cache = {}
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache = {}

    def save_cache(self):
        """Save the cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.cache)} translation entries to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def get_cache_key(self, text, source_lang, target_lang):
        """Generate a unique key for the cache."""
        # Use a shorter version of the text for the key to avoid too long keys
        text_part = text[:50] if len(text) > 50 else text
        return f"{source_lang}|{target_lang}|{text_part}"

    def get_translation(self, text, source_lang, target_lang):
        """Get a translation from the cache."""
        cache_key = self.get_cache_key(text, source_lang, target_lang)
        return self.cache.get(cache_key, {}).get('translation', None)

    def add_translation(self, text, translation, source_lang, target_lang):
        """Add a translation to the cache."""
        cache_key = self.get_cache_key(text, source_lang, target_lang)
        self.cache[cache_key] = {
            'text': text,
            'translation': translation,
            'source_lang': source_lang,
            'target_lang': target_lang
        }
        # Periodically save the cache (every 10 additions)
        if len(self.cache) % 10 == 0:
            self.save_cache()