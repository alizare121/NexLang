# translation_cache.py

import json
import os
import logging

logger = logging.getLogger(__name__)

class TranslationCache:
    def __init__(self, cache_file="translations_cache.json"):
        self.cache_file = cache_file
        self.cache = {}
        self.load_cache()
    
    def load_cache(self):
        """Load cached translations from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached translations")
            else:
                self.cache = {}
                logger.info("No translation cache file found, starting with empty cache")
        except Exception as e:
            logger.error(f"Error loading translation cache: {e}")
            self.cache = {}
    
    def save_cache(self):
        """Save cached translations to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.cache)} translations to cache")
        except Exception as e:
            logger.error(f"Error saving translation cache: {e}")
    
    def get_key(self, text, source_lang, target_lang):
        """Generate a unique key for the translation."""
        return f"{source_lang}:{target_lang}:{text}"
    
    def get_translation(self, text, source_lang, target_lang):
        """Get a cached translation if available."""
        key = self.get_key(text, source_lang, target_lang)
        return self.cache.get(key)
    
    def add_translation(self, text, translated_text, source_lang, target_lang):
        """Add a translation to the cache."""
        key = self.get_key(text, source_lang, target_lang)
        self.cache[key] = translated_text
        # Save periodically (we could optimize this to save less frequently)
        if len(self.cache) % 10 == 0:  # Save every 10 new translations
            self.save_cache()