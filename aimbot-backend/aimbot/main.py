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
from aimbot.models.news import NewsStory, TopImage
from aimbot.email_renderer import EmailRenderer
from aimbot.radio.elabs import ElevenLabs

EmailData = Union[BEEmailData, GEEmailData, JEPEmailData, AIMPremiumEmailData]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the built Svelte app (we'll mount this at the end)
static_dir = Path(__file__).parent.parent.parent / "aimbot-frontend" / "build"

class EmailType(str, Enum):
    BE = "be"
    GE = "ge"
    JEP = "jep"
    AIMPremium = "aimpremium"

@app.get('/')
def root():
    # Redirect to index.html since static files are mounted at root
    if static_dir.exists():
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "index.html")
    return {"message": "Aimbot Backend is running"}

@app.post("/news_stories/", response_model=NewsStory)
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

@app.get("/emails/{email_type}", response_model=EmailData)
async def fetch_email(email_type: EmailType):
    """Fetch email data for a specific email type"""
    
    if email_type == EmailType.BE:
        scraper = BEScraper()
        weather_scraper = WeatherScraper.Jsy()
        fn_scraper = FamilyNoticesScraper()
        
        tasks = {
            "news_stories": scraper.fetch_n_stories_for_section("news", limit=5),
            "sports_stories": scraper.fetch_n_stories_for_section("sport", limit=5),
            "business_stories": scraper.fetch_n_stories_for_section("business", limit=5),
            "community_stories": scraper.fetch_n_stories_for_section("community", limit=5),
            "podcast_stories": scraper.fetch_n_stories_for_section("podcasts", limit=5),
            "family_notices": fn_scraper.get_notices(),
            "weather": weather_scraper.get_weather()
        }
        results = await asyncio.gather(*tasks.values())
        results = dict(zip(tasks.keys(), results))

        email_data = BEEmailData(
            top_image = TopImage(url = "", image_url = ""),
            tides = results['weather'].tides,
            weather = results['weather'].weather,
            date = datetime.now().strftime("%-d %B %Y"),
            news_stories = results.get('news_stories', []),
            horizontal_adverts = [],
            vertical_adverts = [],
            sports_stories = results.get('sports_stories', []),
            business_stories = results.get('business_stories', []),
            connect_image_url = "",
            community_stories = results.get('community_stories', []),
            podcast_stories = results.get('podcast_stories', []),
            family_notices = results.get('family_notices', [])
        )
        return email_data
    
    elif email_type == EmailType.GE:
        scraper = GEScraper()
        weather_scraper = WeatherScraper.Gsy()
        tasks = {
            "news_stories": scraper.fetch_n_stories_for_section("news", limit=5),
            "sports_stories": scraper.fetch_n_stories_for_section("sport", limit=5),
            "business_stories": scraper.fetch_n_stories_for_section("business", limit=5),
            "community_stories": scraper.fetch_n_stories_for_section("community", limit=5),
            "podcast_stories": scraper.fetch_n_stories_for_section("podcasts", limit=5),
            "weather": weather_scraper.get_weather()
        }
        results = await asyncio.gather(*tasks.values())
        results = dict(zip(tasks.keys(), results))
        email_data = GEEmailData(
            top_image = TopImage(url = "", image_url = ""),
            tides = results['weather'].tides,
            weather = results['weather'].weather,
            date = datetime.now().strftime("%-d %B %Y"),
            news_stories = results.get('news_stories', []),
            horizontal_adverts = [],
            vertical_adverts = [],
            sports_stories = results.get('sports_stories', []),
            business_stories = results.get('business_stories', []),
            connect_image_url = "",
            community_stories = results.get('community_stories', []),
            podcast_stories = results.get('podcast_stories', [])
        )
        return email_data
    
    elif email_type == EmailType.JEP:

        scraper = JEPScraper()
        news_stories = await scraper.fetch_n_stories_for_section("news")
        email_data = JEPEmailData(
            cover_image_url = "",
            date = datetime.now().strftime("%-d %B %Y"),
            news_stories = news_stories,
            adverts = []
        )
        return email_data 

    elif email_type == EmailType.AIMPremium:

        scraper = JEPScraper()
        news_stories = await scraper.fetch_n_stories_for_section("premium")
        email_data = AIMPremiumEmailData(
            title = "",
            news_stories = news_stories,
            foreword = Foreword.default(),
        )
        return email_data
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown email type: {email_type}")

@app.post("/emails/{email_type}/render", response_class=HTMLResponse)
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

@app.get("/radio/speakers")
async def get_speakers() -> list[str]:
    """Return a list of available speakers for TTS"""
    elabs = ElevenLabs()
    voice_to_id = elabs.get_voice_to_id()
    return list(voice_to_id.keys())

@app.get("/radio/script")
async def fetch_radio_script(speaker: str) -> RadioNewsData:
    """Fetch radio news data and generate initial script"""
    from aimbot.radio.radio_news import RadioNews
    
    try:
        radio = RadioNews(speaker=speaker)
        data = await radio.get_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch radio script: {str(e)}")

@app.post("/radio/generate")
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

# SPA catch-all route for client-side routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the SPA for any route that doesn't match API endpoints"""
    if not static_dir.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
        
    # If it's a file request (has extension), try to serve it as static
    if "." in full_path.split("/")[-1]:
        file_path = static_dir / full_path
        if file_path.exists():
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="File not found")
    
    # For routes without extensions (SPA routes), serve index.html
    return FileResponse(static_dir / "index.html")