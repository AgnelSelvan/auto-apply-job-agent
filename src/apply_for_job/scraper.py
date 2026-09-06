import logging
import re
import requests
from typing import Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape_job_details(url: str) -> Tuple[str, str, str]:
    """
    Attempts to scrape the actual LinkedIn job page for the full description, job poster, and posted time.
    Note: LinkedIn has strong anti-scraping measures, so this might not work 100% of the time.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"Could not load page {url}: Status {response.status_code}")
            return "Could not load page (Blocked or Not Found)", "Unknown", ""
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        desc_div = soup.find('div', class_='show-more-less-html__markup')
        if not desc_div:
            desc_div = soup.find('div', class_='description__text')
            
        description = desc_div.get_text(separator='\n', strip=True) if desc_div else "Description not found on page"
        
        poster_name = "Not provided"
        poster_card = soup.find('div', class_='message-the-recruiter')
        if poster_card:
            name_tag = poster_card.find('h3', class_='base-main-card__title')
            if name_tag:
                poster_name = name_tag.get_text(strip=True)
                
        posted_time = ""
        time_tag = soup.find('span', class_=re.compile(r'posted-time-ago'))
        if time_tag:
            posted_time = time_tag.get_text(strip=True)
                
        return description, poster_name, posted_time
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while scraping {url}: {e}")
        return f"Request Error: {e}", "Error", ""
    except Exception as e:
        logger.error(f"Parsing error while scraping {url}: {e}")
        return f"Parsing Error: {e}", "Error", ""

def parse_time_ago(*texts: str) -> int:
    """Attempt to find relative time in the texts to sort by later. Returns hours."""
    min_hours = 999999
    for text in texts:
        if not text:
            continue
        match = re.search(r'(\d+)\s+(hour|day|week|month)s?\s+ago', text, re.IGNORECASE)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            hours = 999999
            if unit == 'hour': hours = amount
            elif unit == 'day': hours = amount * 24
            elif unit == 'week': hours = amount * 24 * 7
            elif unit == 'month': hours = amount * 24 * 30
            
            min_hours = min(min_hours, hours)
    return min_hours
