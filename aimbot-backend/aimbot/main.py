import asyncio
from datetime import datetime
from enum import Enum
from typing import Union
from pathlib import Path


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aimbot.scrapers.news.be import BEScraper
from aimbot.scrapers.news.ge import GEScraper
from aimbot.scrapers.news.jep import JEPScraper
from aimbot.scrapers.weather import WeatherScraper
from aimbot.scrapers.family_notices import FamilyNoticesScraper

from aimbot.models.emails import (
    BEEmailData, GEEmailData, JEPEmailData, AIMPremiumEmailData, Foreword
)
from aimbot.models.radio import RadioNewsData
from aimbot.models.news import Advert, NewsStory, TopImage
from aimbot.email_renderer import EmailRenderer
from aimbot.radio.elabs import ElevenLabs
from aimbot.cache import EmailCache, merge_with_cache

EmailData = Union[BEEmailData, GEEmailData, JEPEmailData, AIMPremiumEmailData]

app = FastAPI()

# Create API router with /api prefix
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the built Svelte app (we'll mount this at the end)
static_dir = Path(__file__).parent.parent.parent / "aimbot-frontend" / "build"

# Point email cache to same directory as main.py
email_cache = EmailCache(cache_dir=str(Path(__file__).parent / "cache"))

class EmailType(str, Enum):
    BE = "be"
    GE = "ge"
    JEP = "jep"
    AIMPremium = "aimpremium"

@api_router.post("/news_stories/", response_model=NewsStory)
async def get_news_story(url: str):
    """
    Scrape a single story from a URL
    Determines the appropriate scraper based on the URL origin
    """
    if "bailiwickexpress.com" in url:
        scraper = BEScraper()
        response = await scraper.fetch(url)
        story = scraper.parse(response)
        return story
    elif "jerseyeveningpost.com" in url:
        # TODO: Implement JEP scraper
        raise HTTPException(status_code=501, detail="JEP scraper not yet implemented")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown news source. Supported: bailiwickexpress.com, jerseyeveningpost.com")

@api_router.get("/emails/{email_type}", response_model=EmailData)
async def fetch_email(email_type: EmailType):
    """Fetch email data for a specific email type, merging fresh scraped data with cached user edits"""
    
    # Load cached data
    cached_data = email_cache.load(email_type.value) or {}
    
    if email_type == EmailType.BE:

        scraper = BEScraper()
        weather_scraper = WeatherScraper.Jsy()
        fn_scraper = FamilyNoticesScraper()
        
        tasks = {
            "news_stories": scraper.fetch_n_stories_for_section("news", limit=10),
            "sports_stories": scraper.fetch_n_stories_for_section("sport", limit=2),
            "business_stories": scraper.fetch_n_stories_for_section("business", limit=2),
            "opinion_stories": scraper.fetch_n_stories_for_section("opinion", limit=2),
            "community_stories": scraper.fetch_n_stories_for_section("community", limit=2),
            "podcast_stories": scraper.fetch_n_stories_for_section("podcasts", limit=2),
            "family_notices": fn_scraper.get_notices(),
            "weather": weather_scraper.get_weather()
        }
        results = await asyncio.gather(*tasks.values())
        results = dict(zip(tasks.keys(), results))

        fresh_data = {
            "top_image": TopImage(),
            "tides": results['weather'].tides,
            "weather": results['weather'].weather,
            "date": datetime.now().strftime("%-d %B %Y"),
            "news_stories": results.get('news_stories', []),
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "opinion_stories": results.get('opinion_stories', []),
            "sports_stories": results.get('sports_stories', []),
            "business_stories": results.get('business_stories', []),
            "connect_image_url": "",
            "community_stories": results.get('community_stories', []),
            "podcast_stories": results.get('podcast_stories', []),
            "family_notices": results.get('family_notices', [])
        }

        for k in fresh_data.keys():
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]

        return BEEmailData(**fresh_data)
    
    elif email_type == EmailType.GE:

        scraper = GEScraper()
        weather_scraper = WeatherScraper.Gsy()
        tasks = {
            "news_stories": scraper.fetch_n_stories_for_section("news", limit=10),
            "sports_stories": scraper.fetch_n_stories_for_section("sport", limit=2),
            "opinion_stories": scraper.fetch_n_stories_for_section("opinion", limit=2),
            "business_stories": scraper.fetch_n_stories_for_section("business", limit=2),
            "community_stories": scraper.fetch_n_stories_for_section("community", limit=2),
            "podcast_stories": scraper.fetch_n_stories_for_section("podcasts", limit=2),
            "weather": weather_scraper.get_weather()
        }
        results = await asyncio.gather(*tasks.values())
        results = dict(zip(tasks.keys(), results))
        
        fresh_data = {
            "top_image": TopImage(),
            "tides": results['weather'].tides,
            "weather": results['weather'].weather,
            "date": datetime.now().strftime("%-d %B %Y"),
            "news_stories": results.get('news_stories', []),
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "opinion_stories": results.get('opinion_stories', []),
            "sports_stories": results.get('sports_stories', []),
            "business_stories": results.get('business_stories', []),
            "connect_image_url": "",
            "community_stories": results.get('community_stories', []),
            "podcast_stories": results.get('podcast_stories', [])
        }
        for k in fresh_data.keys():
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]
        return GEEmailData(**fresh_data)
    
    elif email_type == EmailType.JEP:

        scraper = JEPScraper()
        news_stories = await scraper.fetch_n_stories_for_section("news")
        
        fresh_data = {
            "date": datetime.now().strftime("%-d %B %Y"),
            "jep_cover_url": "",    
            "news_stories": news_stories,
            "publication_cover_url": "",
            "max_banner": Advert(url="", image_url=""),
            "leaderboard_adverts": [],
            "mpu_adverts": []
        }
    
        for k in fresh_data.keys():
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]
        email_data = JEPEmailData(**fresh_data)
        return email_data

    elif email_type == EmailType.AIMPremium:

        scraper = JEPScraper()
        news_stories = await scraper.fetch_n_stories_for_section("premium")
        
        fresh_data = {
            "title": "",
            "news_stories": news_stories,
            "foreword": Foreword.default(),
        }
        for k in fresh_data.keys():
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]
        return AIMPremiumEmailData(**fresh_data)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown email type: {email_type}")

@api_router.post("/emails/{email_type}/render", response_class=HTMLResponse)
async def render_email(email_type: EmailType, email_data: EmailData):
    """Render email data to HTML using the appropriate template"""
    
    # Map email type to template
    template_map = {
        EmailType.BE: "be_template.html",
        EmailType.GE: "ge_template.html",
        EmailType.JEP: "jep_template.html",
        EmailType.AIMPremium: "aim_premium_template.html"
    }
    
    template_name = template_map.get(email_type)
    if not template_name:
        raise HTTPException(status_code=400, detail=f"Unknown email type: {email_type}")
    
    try:
        renderer = EmailRenderer(template_name=template_name)
        html = renderer.render(email_data.model_dump())
        
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render email: {str(e)}")

@api_router.post("/emails/{email_type}/save")
async def save_email(email_type: EmailType, email_data: EmailData):
    """Save email data to cache for future fetches"""
    try:
        success = email_cache.save(email_type.value, email_data.model_dump())
        if success:
            return {"status": "success", "message": f"Email data saved to cache"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save email data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save email: {str(e)}")

@api_router.get("/radio/speakers")
async def get_speakers() -> list[str]:
    """Return a list of available speakers for TTS"""
    elabs = ElevenLabs()
    voice_to_id = elabs.get_voice_to_id()
    return list(voice_to_id.keys())

@api_router.get("/radio/script")
async def fetch_radio_script(speaker: str) -> RadioNewsData:
    """Fetch radio news data and generate initial script"""
    from aimbot.radio.radio_news import RadioNews
    
    try:
        radio = RadioNews(speaker=speaker)
        data = await radio.get_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch radio script: {str(e)}")

@api_router.post("/radio/generate")
async def generate_radio_news(data: RadioNewsData):
    """Generate radio news data for a specific speaker"""
    elabs = ElevenLabs()
    voice_to_id = elabs.get_voice_to_id()
    if data.speaker_id not in voice_to_id:
        raise HTTPException(status_code=400, detail=f"Speaker {data.speaker_id} not found among custom voices: {list(voice_to_id.keys())}")
    try:
        audio_bytes = elabs.generate(text=data.script, voice=data.speaker_id)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")

# Include the API router
app.include_router(api_router)

# Mount static files and SPA routing only in production (when build exists)
if static_dir.exists():
    # Mount static assets (with lower priority than API routes)
    app.mount("/_app", StaticFiles(directory=str(static_dir / "_app")), name="assets")
    
    # Catch-all route for SPA - must be defined last
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes"""
        # If the path points to an actual file, serve it
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise, serve index.html and let the SPA handle routing
        return FileResponse(static_dir / "index.html")
