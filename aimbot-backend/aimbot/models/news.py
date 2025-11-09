from typing import Optional
from datetime import datetime
import re

from pydantic import BaseModel

class NewsStory(BaseModel):
    headline: str
    text: str
    date: datetime
    author: str
    url: str
    image_url: str
    
    def __repr__(self):
        return f"NewsStory(headline='{self.headline[:50]}...', author={self.author})"

class Advert(BaseModel):
    url: str
    image_url: str

class FamilyNotice(BaseModel):
    name: str
    url: str
    funeral_director: Optional[str] = None
    additional_text: Optional[str] = None

    @staticmethod
    def format_name(name: str) -> str:
        """
        Formats a name from 'Last, First (Extra1) (Extra2)' to 'First Last (Extra1) (Extra2)'.
        Handles multiple parenthetical parts.
        """
        # Extract all bracketed parts
        bracketed_parts = re.findall(r"\(.*?\)", name)
        
        # Remove bracketed parts from the main name
        name_without_brackets = re.sub(r"\(.*?\)", "", name).strip()
        
        # Handle "Last, First" format
        if "," in name_without_brackets:
            last, first = [part.strip() for part in name_without_brackets.split(",", 1)]
            formatted_name = f"{first} {last}"
        else:
            formatted_name = name_without_brackets  # If no comma, assume already correct

        # Append all extracted bracketed parts at the end
        if bracketed_parts:
            formatted_name = f"{formatted_name} {' '.join(bracketed_parts)}"

        # Capitalize first letter of each word, except for 'née'
        return formatted_name.title().replace('Née', 'née')


class TopImage(BaseModel):
    url: str
    image_url: str
    author: Optional[str] = None
    text: Optional[str] = None
