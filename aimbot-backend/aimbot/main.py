import asyncio
import sys
from datetime import datetime
from enum import Enum
from typing import Union
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from loguru import logger

from aimbot.scrapers.news.be import BEScraper
from aimbot.scrapers.news.ge import GEScraper
from aimbot.scrapers.news.jep import JEPScraper
from aimbot.scrapers.weather import WeatherScraper
from aimbot.scrapers.family_notices import FamilyNoticesScraper

from aimbot.models.emails import (
    BEEmailData, ConnectInsiderEmailData, GEEmailData, 
    JEPEmailData, AIMPremiumEmailData, Foreword,
)
from aimbot.models.radio import RadioNewsData
from aimbot.models.news import Advert, NewsStory, TopImage
from aimbot.email_renderer import EmailRenderer
from aimbot.radio.elabs import ElevenLabs
from aimbot.cache import EmailCache

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logger.remove()  # remove default stderr handler
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{name}</cyan> | {message}",
    colorize=True,
)
logger.add(
    "logs/aimbot_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="1 day",
    retention="30 days",
    format="{time:HH:mm:ss} | {level:<7} | {name}:{function}:{line} | {message}",
)

EmailData = Union[BEEmailData, ConnectInsiderEmailData, GEEmailData, JEPEmailData, AIMPremiumEmailData]

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Global exception handler — ensures every error returns structured JSON
# so the frontend can display a meaningful message instead of a raw HTML 500.
# ---------------------------------------------------------------------------
from starlette.requests import Request
from starlette.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a structured JSON error.

    Without this handler FastAPI falls back to a raw HTML 500 page which the
    frontend cannot parse — the user would see nothing useful.  HTTPException
    instances are re-raised so that FastAPI's built-in handler can set the
    correct status code; everything else becomes a 500.
    """
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )

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
    INSIDER_JSY = "insider_jsy"
    INSIDER_GSY = "insider_gsy"


# ---------------------------------------------------------------------------
# Helper: run concurrent scrapers gracefully
# ---------------------------------------------------------------------------
async def _gather_scraper_tasks(
    tasks: dict[str, object],
) -> dict[str, object]:
    """
    Run a dict of coroutines concurrently, returning a dict of
    (name → result_or_None).  A single scraper failure will NOT
    crash the whole batch.
    """
    names = list(tasks.keys())
    coros = list(tasks.values())
    results = await asyncio.gather(*coros, return_exceptions=True)
    out: dict[str, object] = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.error(f"Scraper task '{name}' failed: {result}")
            out[name] = None
        else:
            out[name] = result
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # BE — Bailiwick Express Jersey
    # -----------------------------------------------------------------------
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
            "weather": weather_scraper.get_weather(),
        }
        results = await _gather_scraper_tasks(tasks)

        weather = results.get("weather")
        fresh_data: dict = {
            "top_image": TopImage(),
            "tides": weather.tides if weather else "",
            "weather": weather.weather if weather else "",
            "date": datetime.now().strftime("%-d %B %Y"),
            "news_stories": results.get("news_stories") or [],
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "spon_con_stories": [],
            "opinion_stories": results.get("opinion_stories") or [],
            "sports_stories": results.get("sports_stories") or [],
            "business_stories": results.get("business_stories") or [],
            "connect_image_url": "",
            "community_stories": results.get("community_stories") or [],
            "podcast_stories": results.get("podcast_stories") or [],
            "family_notices": results.get("family_notices") or [],
        }

        for k in fresh_data:
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]

        return BEEmailData(**fresh_data)

    # -----------------------------------------------------------------------
    # GE — Bailiwick Express Guernsey
    # -----------------------------------------------------------------------
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
            "weather": weather_scraper.get_weather(),
        }
        results = await _gather_scraper_tasks(tasks)

        weather = results.get("weather")
        fresh_data: dict = {
            "top_image": TopImage(),
            "tides": weather.tides if weather else "",
            "weather": weather.weather if weather else "",
            "date": datetime.now().strftime("%-d %B %Y"),
            "news_stories": results.get("news_stories") or [],
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "opinion_stories": results.get("opinion_stories") or [],
            "spon_con_stories": [],
            "sports_stories": results.get("sports_stories") or [],
            "business_stories": results.get("business_stories") or [],
            "connect_image_url": "",
            "community_stories": results.get("community_stories") or [],
            "podcast_stories": results.get("podcast_stories") or [],
        }

        for k in fresh_data:
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]

        return GEEmailData(**fresh_data)

    # -----------------------------------------------------------------------
    # JEP — Jersey Evening Post
    # -----------------------------------------------------------------------
    elif email_type == EmailType.JEP:
        scraper = JEPScraper()
        news_stories = await scraper.fetch_n_stories_for_section("news")

        fresh_data: dict = {
            "date": datetime.now().strftime("%-d %B %Y"),
            "jep_cover_url": "",
            "news_stories": news_stories,
            "publication_cover_url": "",
            "max_banner": Advert(url="", image_url=""),
            "leaderboard_adverts": [],
            "mpu_adverts": [],
        }

        for k in fresh_data:
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]

        return JEPEmailData(**fresh_data)

    # -----------------------------------------------------------------------
    # AIM Premium
    # -----------------------------------------------------------------------
    elif email_type == EmailType.AIMPremium:
        scraper = JEPScraper()
        news_stories = await scraper.fetch_n_stories_for_section("premium")

        fresh_data: dict = {
            "title": "",
            "news_stories": news_stories,
            "foreword": Foreword.default(),
        }
        for k in fresh_data:
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]

        return AIMPremiumEmailData(**fresh_data)

    # -----------------------------------------------------------------------
    # Connect Insider (Jersey & Guernsey)
    # -----------------------------------------------------------------------
    elif email_type in (EmailType.INSIDER_JSY, EmailType.INSIDER_GSY):
        scraper = BEScraper() if email_type == EmailType.INSIDER_JSY else GEScraper()
        business_stories = await scraper.fetch_n_stories_for_section("business", limit=10)

        fresh_data: dict = {
            "top_image": TopImage(),
            "big_stories": business_stories,
            # If no business stories were scraped, provide an empty list rather
            # than crashing with IndexError.
            "sponsored_stories": [business_stories[0]] if business_stories else [],
            "movers_and_shakers": business_stories,
            "connect_image_url": "",
            "ads": [],
        }
        for k in fresh_data:
            if not fresh_data[k] and cached_data.get(k):
                fresh_data[k] = cached_data[k]

        return ConnectInsiderEmailData(**fresh_data)

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
        EmailType.AIMPremium: "aim_premium_template.html",
        EmailType.INSIDER_JSY: "connect_insider.html",
        EmailType.INSIDER_GSY: "connect_insider_gsy.html",
    }

    template_name = template_map.get(email_type)
    if not template_name:
        raise HTTPException(status_code=400, detail=f"Unknown email type: {email_type}")

    try:
        renderer = EmailRenderer(template_name=template_name)
        html = renderer.render(email_data.model_dump())
        return HTMLResponse(content=html)
    except Exception as e:
        logger.exception(f"Failed to render email for {email_type}")
        raise HTTPException(status_code=500, detail=f"Failed to render email: {str(e)}")


@api_router.post("/emails/{email_type}/save")
async def save_email(email_type: EmailType, email_data: EmailData):
    """Save email data to cache for future fetches"""
    try:
        success = email_cache.save(email_type.value, email_data.model_dump())
        if success:
            return {"status": "success", "message": "Email data saved to cache"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save email data")
    except Exception as e:
        logger.exception(f"Failed to save email for {email_type}")
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
        logger.exception(f"Failed to fetch radio script for speaker '{speaker}'")
        raise HTTPException(status_code=500, detail=f"Failed to fetch radio script: {str(e)}")


@api_router.post("/radio/generate")
async def generate_radio_news(data: RadioNewsData):
    """Generate radio news data for a specific speaker"""
    elabs = ElevenLabs()
    voice_to_id = elabs.get_voice_to_id()
    if data.speaker_id not in voice_to_id:
        raise HTTPException(
            status_code=400,
            detail=f"Speaker {data.speaker_id} not found among custom voices: {list(voice_to_id.keys())}",
        )
    try:
        audio_bytes = elabs.generate(text=data.script, voice=data.speaker_id)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        logger.exception("Failed to generate audio")
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")


# Include the API router
app.include_router(api_router)

# Mount static files and SPA routing only in production (when build exists)
if static_dir.exists():
    # Mount static assets (with lower priority than API routes)
    app.mount("/_app", StaticFiles(directory=str(static_dir / "_app")), name="assets")

    # Catch-all route for SPA — must be defined last
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes"""
        # If the path points to an actual file, serve it
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise, serve index.html and let the SPA handle routing
        return FileResponse(static_dir / "index.html")
