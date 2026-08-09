
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
from typing import Optional
from urllib.parse import urljoin


logger = logging.getLogger(__name__)


class JobListing(BaseModel):
    """The job fields exposed by the First Recruitment jobs search."""

    title: str
    job_types: list[str]
    reference_number: str
    location: str
    url: str


class FirstRecruitmentScraper:

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
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.1strecruit.co.uk/jobs/",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Priority": "u=0, i",
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

    async def fetch_jobs(
        self,
        location: str = "Jersey",
        job_types: Optional[list[str]] = None,
        sector: str = None,
        limit: Optional[int] = 5,
    ) -> list[JobListing]:
        """Fetch jobs from 1st Recruitment website."""
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
            async with aiohttp.ClientSession(headers=self.HEADERS) as session:
                async with session.get(f"{self.url}/jobs/", params=params) as response:
                    logger.debug(
                        "First Recruitment response: status=%s, url=%s, content_type=%r",
                        response.status,
                        response.url,
                        response.headers.get("Content-Type"),
                    )
                    response.raise_for_status()
                    html = await response.text()
                    logger.debug("First Recruitment response body length: %d", len(html))
                    soup = BeautifulSoup(html, "html.parser")
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
