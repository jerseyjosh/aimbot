
"""
Example browser request:

:method: GET
:scheme: https
:authority: www.1strecruit.co.uk
:path: /jobs/?sector=&location=Jersey&keywords=&jobtype=Permanent&jobtype=Temporary&jobtype=Contract
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Sec-Fetch-Site: same-origin
Cookie: _ga=GA1.1.349926086.1786294228; _ga_71M9C7MJNV=GS2.1.s1786294228$o1$g1$t1786294264$j24$l0$h0; _gid=GA1.3.978362557.1786294228; _gat=1
Sec-Fetch-Dest: document
Accept-Language: en-GB,en;q=0.9
Sec-Fetch-Mode: navigate
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15
Accept-Encoding: gzip, deflate, br
Referer: https://www.1strecruit.co.uk/jobs/?sector=&location=Jersey&keywords=&jobtype=Permanent&jobtype=Temporary&jobtype=Contract
Priority: u=0, i

"""

import aiohttp
from bs4 import BeautifulSoup
import logging
from pydantic import BaseModel
import re
import asyncio
from typing import Optional
from urllib.parse import urljoin, urlsplit


logger = logging.getLogger(__name__)


class JobListing(BaseModel):
    """The job fields exposed by the First Recruitment jobs search."""

    title: str
    job_types: list[str]
    reference_number: str
    location: str
    url: str


class FirstRecruitmentScraper:

    BASE_URL = "https://www.1strecruit.co.uk"
    VALID_SECTORS = {
        "Accounting", "Actuarial", "Administration", "Banking", "Bookkeeping",
        "Business Development", "Charity", "Commercial", "Company Secretarial",
        "Compliance", "Customer Service", "Engineering", "Executive", "Facilities",
        "Finance", "Fin-tech", "Funds", "Health & Social Services", "HR",
        "Information Technology", "Insurance", "Investments", "Languages", "Legal",
        "Marketing/PR/Communications", "Operations", "Payroll", "Pensions",
        "Procurement", "Project Management", "Public Sector", "Recruitment", "Retail",
        "Risk", "Sales", "Secretarial", "Securities/Custody", "Sustainability", "Tax",
        "Telecoms", "Trainee/Graduate", "Treasury", "Trust",
    }
    JOB_TYPES = {"Permanent", "Temporary", "Contract"}
    # Keep the browser identity internally consistent.  In particular, do not
    # advertise Safari while sending an aiohttp/Linux request.
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-User": "?1",
    }


    def __init__(self):
        self.url = "https://www.1strecruit.co.uk"

    @staticmethod
    def parse_job_listing(element, requested_location: str = "") -> JobListing:
        """Parse one ``.result-item.job-item`` element from the search page."""
        title_element = element.select_one(".j-heading a")

        attributes = [item.get_text(" ", strip=True) for item in element.select(".j-attributes li")]
        job_types = [job_type for job_type in attributes if job_type in FirstRecruitmentScraper.JOB_TYPES]

        location_element = element.select_one(".j-location, .job-location")
        listing_location = location_element.get_text(" ", strip=True) if location_element else ""
        for attribute in attributes:
            if listing_location:
                break
            match = re.match(r"^Location:\s*(.+)$", attribute, flags=re.IGNORECASE)
            if match:
                listing_location = match.group(1).strip()
                break

        reference_number = ""
        for attribute in attributes:
            match = re.match(r"^Ref:\s*(.+)$", attribute, flags=re.IGNORECASE)
            if match:
                reference_number = match.group(1).strip()
                break

        return JobListing(
            title=title_element.get_text(" ", strip=True) if title_element else "",
            job_types=job_types,
            reference_number=reference_number,
            location=listing_location or requested_location,
            url=urljoin("https://www.1strecruit.co.uk", title_element.get("href", "")) if title_element else "",
        )

    @classmethod
    def parse_jobs(
        cls,
        soup: BeautifulSoup,
        limit: Optional[int] = None,
        requested_location: str = "",
    ) -> list[JobListing]:
        """Parse listings in page order, optionally returning only the first ``limit``."""
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")

        elements = soup.select(".result-item.job-item")
        logger.debug("First Recruitment page contains %d matching job element(s)", len(elements))
        if limit is not None:
            elements = elements[:limit]
        if not elements:
            logger.warning(
                "First Recruitment returned no matching job elements "
                "(requested_location=%r, limit=%r, page_title=%r, body_length=%d)",
                requested_location,
                limit,
                soup.title.get_text(" ", strip=True) if soup.title else "",
                len(soup.get_text()),
            )
        return [cls.parse_job_listing(element, requested_location) for element in elements]

    @staticmethod
    def _normalise_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @classmethod
    def parse_latest_job_listing(cls, element, title_element=None) -> JobListing:
        """Parse one job card from the homepage latest-jobs section."""
        if title_element is None:
            title_element = element.select_one(
                ".j-heading a, .job-title a, .latest-job-title a, h1 a, h2 a, h3 a, h4 a"
            )
            if title_element is None:
                title_element = element.select_one("a[href]")

        text = cls._normalise_text(element.get_text(" ", strip=True))
        attributes = [
            cls._normalise_text(item.get_text(" ", strip=True))
            for item in element.select("li, .j-attribute, .job-attribute")
        ]
        attributes = [item for item in attributes if item]

        location = ""
        location_element = element.select_one(
            ".j-location, .job-location, .location, .latest-job-location, "
            "[class*='location']"
        )
        if location_element:
            location = cls._normalise_text(location_element.get_text(" ", strip=True))
        if not location:
            for value in attributes + [text]:
                match = re.search(r"(?:^|\s)Location\s*:\s*([^|•]+)", value, re.I)
                if match:
                    location = cls._normalise_text(match.group(1))
                    break

        reference_number = ""
        for value in attributes + [text]:
            match = re.search(r"(?:^|\s)(?:Ref|Reference)\s*:\s*([^|•]+)", value, re.I)
            if match:
                reference_number = cls._normalise_text(match.group(1))
                break

        job_types = [value for value in attributes if value in cls.JOB_TYPES]
        if not job_types:
            job_types = [value for value in cls.JOB_TYPES if re.search(rf"\b{re.escape(value)}\b", text, re.I)]
        return JobListing(
            title=cls._normalise_text(title_element.get_text(" ", strip=True)) if title_element else "",
            job_types=job_types,
            reference_number=reference_number,
            location=location,
            url=urljoin(cls.BASE_URL, title_element.get("href", "")) if title_element else "",
        )

    @staticmethod
    def _latest_job_card(link, container):
        """Return the smallest row/card around a homepage job link."""
        fallback = link.parent
        node = link.parent
        while node is not None and node is not container:
            classes = node.get("class", [])
            if node.name in {"tr", "li", "article"}:
                return node
            if any(
                marker in class_name.casefold()
                for class_name in classes
                for marker in ("job", "vacancy", "result")
            ):
                return node
            fallback = node
            node = node.parent
        return fallback

    @classmethod
    def parse_homepage_job_row(cls, row) -> JobListing:
        """Parse a four-column ``.job-listing-content`` homepage row."""
        spans = row.find_all("span", recursive=False)
        if len(spans) < 4:
            spans = row.select("span")
        title_span, location_span, type_span, reference_span = spans[:4]
        title_link = title_span.select_one("a[href]")
        job_type = cls._normalise_text(type_span.get_text(" ", strip=True))
        reference_number = cls._normalise_text(reference_span.get_text(" ", strip=True))
        reference_number = re.sub(r"^(?:ref(?:erence)?\s*:?\s*)", "", reference_number, flags=re.I)

        return JobListing(
            title=cls._normalise_text(title_span.get_text(" ", strip=True)),
            job_types=[job_type] if job_type in cls.JOB_TYPES else [],
            reference_number=reference_number,
            location=cls._normalise_text(location_span.get_text(" ", strip=True)),
            url=urljoin(cls.BASE_URL, title_link.get("href", "")) if title_link else "",
        )

    @classmethod
    def parse_latest_jobs(
        cls,
        soup: BeautifulSoup,
        location: Optional[str] = None,
        job_types: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> list[JobListing]:
        """Parse and filter the mixed-location latest-jobs cards on the homepage."""
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")

        requested = cls._normalise_text(location).casefold()
        # The current homepage uses four spans in this fixed order: title,
        # location, employment type, and reference number. Select only the
        # innermost matching elements so a parent wrapper is not mistaken for
        # one job row.
        homepage_rows = [
            row
            for row in soup.select(".latest-jobs .job-listing-content")
            if len(row.find_all("span", recursive=False)) >= 4
        ]
        if homepage_rows:
            results = []
            for row in homepage_rows:
                listing = cls.parse_homepage_job_row(row)
                if requested and listing.location.casefold() != requested:
                    continue
                if job_types and listing.job_types and not set(listing.job_types).intersection(job_types):
                    continue
                if listing.title:
                    results.append(listing)
                if limit is not None and len(results) >= limit:
                    break
            logger.debug(
                "First Recruitment homepage contains %d job-listing-content row(s), "
                "%d matching listing(s) for location=%r",
                len(homepage_rows), len(results), location,
            )
            return results

        containers = soup.select("div.latest-jobs.match-height") or soup.select(".latest-jobs")
        candidates = []
        # Treat job-detail URLs as the source of truth. The homepage has used
        # both a table and cards, but each listing has its own job URL.
        for container in containers:
            for link in container.select("a[href]"):
                path = urlsplit(link.get("href", "")).path.rstrip("/").casefold()
                if "/job" not in path or path in {"/job", "/jobs"}:
                    continue
                candidates.append((cls._latest_job_card(link, container), link))
        if not candidates:
            logger.warning(
                "First Recruitment homepage contains no latest-jobs links "
                "(page_title=%r, body_length=%d)",
                soup.title.get_text(" ", strip=True) if soup.title else "",
                len(soup.get_text()),
            )
        results = []
        seen_urls = set()
        for card, link in candidates:
            listing = cls.parse_latest_job_listing(card, title_element=link)
            actual = cls._normalise_text(listing.location).casefold()
            if requested:
                # Prefer the parsed location, but support tables where the
                # location is an unlabelled cell/text node.
                card_text = cls._normalise_text(card.get_text(" ", strip=True))
                location_matches = actual == requested or bool(
                    re.search(rf"(?<!\w){re.escape(requested)}(?!\w)", card_text.casefold())
                )
                if not location_matches:
                    continue
                if not actual:
                    listing.location = cls._normalise_text(location)
            if job_types and listing.job_types and not set(listing.job_types).intersection(job_types):
                continue
            if listing.title and listing.url:
                if listing.url in seen_urls:
                    continue
                seen_urls.add(listing.url)
                results.append(listing)
            if limit is not None and len(results) >= limit:
                break

        logger.debug(
            "First Recruitment homepage contains %d wrapper(s), %d candidate job link(s), "
            "%d matching listing(s) for location=%r",
            len(containers), len(candidates), len(results), location,
        )
        return results

    async def fetch_jobs_search(
        self,
        location: str = "Jersey",
        job_types: Optional[list[str]] = None,
        sector: str = None,
        limit: Optional[int] = 5,
    ) -> list[JobListing]:
        """Fetch jobs through the site's search endpoint."""
        logger.debug(
            "Fetching First Recruitment jobs (location=%r, job_types=%r, sector=%r, limit=%r)",
            location,
            job_types,
            sector,
            limit,
        )
        if job_types is None:
            job_types = ["Permanent", "Temporary", "Contract"]
        invalid_job_types = set(job_types) - self.JOB_TYPES
        if invalid_job_types:
            logger.error("Invalid First Recruitment job type(s): %s", sorted(invalid_job_types))
            raise ValueError(f"Invalid job type(s): {', '.join(sorted(invalid_job_types))}")
        # validate sector
        if sector and sector not in self.VALID_SECTORS:
            logger.error("Invalid First Recruitment sector: %r", sector)
            raise ValueError(f"Invalid sector '{sector}'. Valid sectors are: {', '.join(self.VALID_SECTORS)}")
        # build query params
        params = {
            "sector": sector or "",
            "location": location,
            "keywords": "",
            "jobtype": job_types,
        }
        # fetch data
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(
                headers=self.HEADERS,
                timeout=timeout,
                cookie_jar=aiohttp.CookieJar(unsafe=False),
            ) as session:
                # First visit the site so an edge service can set its normal
                # session/consent cookies before the search request.
                async with session.get(self.url, allow_redirects=True) as home:
                    logger.debug(
                        "First Recruitment homepage: status=%s, url=%s, cookies=%s",
                        home.status,
                        home.url,
                        list(session.cookie_jar),
                    )
                    await home.read()

                jobs_headers = {
                    "Referer": f"{self.url}/",
                    "Sec-Fetch-Site": "same-origin",
                }
                for attempt in range(1, 4):
                    async with session.get(
                        f"{self.url}/jobs/",
                        params=params,
                        headers=jobs_headers,
                        allow_redirects=True,
                    ) as response:
                        logger.debug(
                            "First Recruitment response: attempt=%d, status=%s, url=%s, content_type=%r",
                            attempt,
                            response.status,
                            response.url,
                            response.headers.get("Content-Type"),
                        )
                        response.raise_for_status()
                        html = await response.text()
                        logger.debug("First Recruitment response body length: %d", len(html))

                    soup = BeautifulSoup(html, "html.parser")
                    if response.status != 202 or soup.select_one(".result-item.job-item"):
                        break
                    # Some edge services briefly return 202 while establishing
                    # a session. Reuse the same cookie jar for a short retry.
                    if attempt < 3:
                        await asyncio.sleep(attempt)

                if not soup.select_one(".result-item.job-item"):
                    logger.warning(
                        "First Recruitment response does not contain job listings: "
                        "status=%s, title=%r, headers=%r, body_prefix=%r",
                        response.status,
                        soup.title.get_text(" ", strip=True) if soup.title else "",
                        {
                            key: value
                            for key, value in response.headers.items()
                            if key.lower() in {
                                "server", "location", "set-cookie", "retry-after",
                                "cf-mitigated", "x-cache", "x-request-id",
                            }
                        },
                        html[:300].replace("\n", " "),
                    )
        except Exception:
            logger.exception(
                "Failed to fetch or parse First Recruitment jobs "
                "(location=%r, job_types=%r, sector=%r, limit=%r, params=%r)",
                location,
                job_types,
                sector,
                limit,
                params,
            )
            raise

        try:
            return self.parse_jobs(soup, limit=limit, requested_location=location)
        except Exception:
            logger.exception(
                "Failed to parse First Recruitment jobs "
                "(location=%r, job_types=%r, sector=%r, limit=%r)",
                location,
                job_types,
                sector,
                limit,
            )
            raise

    async def fetch_jobs(
        self,
        location: Optional[str] = None,
        job_types: Optional[list[str]] = None,
        sector: str = None,
        limit: Optional[int] = 5,
    ) -> list[JobListing]:
        """Fetch matching jobs from the homepage's latest-jobs section."""
        del sector  # The homepage table is not sector-filtered.
        if job_types is None:
            job_types = list(self.JOB_TYPES)
        invalid_job_types = set(job_types) - self.JOB_TYPES
        if invalid_job_types:
            raise ValueError(f"Invalid job type(s): {', '.join(sorted(invalid_job_types))}")

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(headers=self.HEADERS, timeout=timeout) as session:
                async with session.get(f"{self.BASE_URL}/", allow_redirects=True) as response:
                    response.raise_for_status()
                    html = await response.text()
                    logger.debug(
                        "First Recruitment homepage response: status=%s, url=%s, body_length=%d",
                        response.status, response.url, len(html),
                    )
        except Exception:
            logger.exception("Failed to fetch First Recruitment homepage")
            raise

        return self.parse_latest_jobs(
            BeautifulSoup(html, "html.parser"),
            location=location,
            job_types=job_types,
            limit=limit,
        )


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    scraper = FirstRecruitmentScraper()
    jobs = asyncio.run(scraper.fetch_jobs())
    print(jobs)
    breakpoint()
