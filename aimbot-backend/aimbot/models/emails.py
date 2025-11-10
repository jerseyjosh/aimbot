from typing import Optional
from datetime import datetime

from pydantic import BaseModel

from .news import NewsStory, Advert, FamilyNotice, TopImage

class BEEmailData(BaseModel):
    top_image: TopImage
    tides: str
    weather: str
    date: str
    news_stories: list[NewsStory]
    horizontal_adverts: list[Advert]
    vertical_adverts: list[Advert]
    sports_stories: list[NewsStory]
    business_stories: list[NewsStory]
    connect_image_url: str
    community_stories: list[NewsStory]
    podcast_stories: list[NewsStory]
    family_notices: list[FamilyNotice]
    
    def __repr__(self):
        return f"BEEmailData(date={self.date}, {len(self.news_stories)} news stories, {len(self.family_notices)} family notices)"

class GEEmailData(BaseModel):
    top_image: TopImage
    tides: str
    weather: str
    date: str
    news_stories: list[NewsStory]
    horizontal_adverts: list[Advert]
    vertical_adverts: list[Advert]
    sports_stories: list[NewsStory]
    business_stories: list[NewsStory]
    connect_image_url: str
    community_stories: list[NewsStory]
    podcast_stories: list[NewsStory]
    
    def __repr__(self):
        return f"GEEmailData(date={self.date}, {len(self.news_stories)} news stories)"
    
class Foreword(BaseModel):
    title: str
    author: str
    job_title: str
    image_url: str
    text: str

    @staticmethod
    def default() -> "Foreword":
        return Foreword(
            title = "",
            author = "",
            job_title = "",
            image_url = "",
            text = ""
        )


class AIMPremiumEmailData(BaseModel):
    title: str
    news_stories: list[NewsStory]
    foreword: Foreword

class JEPEmailData(BaseModel):
    jep_cover_url: str
    publication_cover_url: str
    date: str
    news_stories: list[NewsStory]
    adverts: list[Advert]

    def __repr__(self):
        return f"JEPEmailData(date={self.date}, {len(self.news_stories)} news stories)"
