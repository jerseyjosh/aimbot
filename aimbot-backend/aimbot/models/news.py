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
    funeral_director: str = ""
    additional_text: str = ""

class TopImage(BaseModel):
    url: str
    image_url: str
    author: Optional[str] = None
    text: Optional[str] = None
