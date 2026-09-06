"""Apply For Job - A tool to search and scrape jobs."""

__version__ = "0.1.0"

from .scraper import scrape_job_details, parse_time_ago
from .search import search_linkedin_jobs

__all__ = [
    "scrape_job_details",
    "parse_time_ago",
    "search_linkedin_jobs"
]
