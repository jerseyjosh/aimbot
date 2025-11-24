"""Simple JSON file cache for storing email data between renders."""
import json
from typing import Optional
from pathlib import Path
from datetime import datetime


class EmailCache:
    """Cache for storing and retrieving email data using JSON files."""
    
    def __init__(self, cache_dir: str):
        """
        Initialize file-based cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_filepath(self, email_type: str) -> Path:
        """Generate filepath for an email type."""
        return self.cache_dir / f"{email_type}.json"
    
    def save(self, email_type: str, email_data: dict) -> bool:
        """
        Save email data to cache.
        
        Args:
            email_type: Type of email (be, ge, jep, aimpremium)
            email_data: Dictionary of email data to cache
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self._get_filepath(email_type)
            with open(filepath, 'w') as f:
                json.dump(email_data, f, indent=2, default=self._json_serializer)
            return True
        except Exception as e:
            print(f"Failed to save to cache: {e}")
            return False
    
    @staticmethod
    def _json_serializer(obj):
        """Custom JSON serializer for objects not serializable by default."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def load(self, email_type: str) -> Optional[dict]:
        """
        Load email data from cache.
        
        Args:
            email_type: Type of email (be, ge, jep, aimpremium)
            
        Returns:
            Cached email data dictionary, or None if not found
        """
        try:
            filepath = self._get_filepath(email_type)
            if not filepath.exists():
                return None
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load from cache: {e}")
            return None
    
    def clear(self, email_type: str) -> bool:
        """
        Clear cached data for an email type.
        
        Args:
            email_type: Type of email to clear
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self._get_filepath(email_type)
            if filepath.exists():
                filepath.unlink()
            return True
        except Exception as e:
            print(f"Failed to clear cache: {e}")
            return False


# Define which fields are user-editable (should be preserved from cache)
USER_EDITABLE_FIELDS = {
    "be": ["top_image", "horizontal_adverts", "vertical_adverts", "connect_image_url"],
    "ge": ["top_image", "horizontal_adverts", "vertical_adverts", "connect_image_url"],
    "jep": ["cover_image_url", "adverts"],
    "aimpremium": ["title", "foreword"]
}


def merge_with_cache(email_type: str, fresh_data: dict, cached_data: Optional[dict]) -> dict:
    """
    Merge fresh scraped data with cached user-editable fields.
    
    Args:
        email_type: Type of email
        fresh_data: Newly scraped data
        cached_data: Previously cached data (may be None)
        
    Returns:
        Merged dictionary with fresh scraped data and preserved user edits
    """
    if not cached_data:
        return fresh_data
    
    # Start with fresh data
    merged = fresh_data.copy()
    
    # Overlay user-editable fields from cache
    user_fields = USER_EDITABLE_FIELDS.get(email_type, [])
    for field in user_fields:
        if field in cached_data:
            merged[field] = cached_data[field]
    
    return merged
