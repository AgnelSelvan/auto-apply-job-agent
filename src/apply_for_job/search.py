import logging
import pandas as pd
from typing import Optional

from .browser_search import search_linkedin_jobs_browser

logger = logging.getLogger(__name__)

def search_linkedin_jobs(query: str, location: str = "India", *args, **kwargs) -> Optional[str]:
    """
    Search LinkedIn jobs exclusively via Google Chrome automation and save directly to an Excel file.
    """
    locations = [loc.strip() for loc in location.split(",") if loc.strip()]
    if not locations:
        locations = ["India"]
        
    all_jobs = []
    
    for loc in locations:
        logger.info(f"Opening Chrome to search for '{query}' jobs in '{loc}'...")
        print(f"Searching for jobs for '{query}' in '{loc}'...")
        
        # Fetch directly from browser search (no deep scraping, no Ollama)
        results_data = search_linkedin_jobs_browser(query, loc)
        
        if not results_data:
            logger.warning(f"No job listings were found for {loc}.")
            print(f"No job listings found for {loc}.")
            continue
            
        # Limit to top 2 latest jobs
        results_data = results_data[:2]
        
        print(f"Adding top {len(results_data)} jobs for {loc} to the spreadsheet.")
        logger.info(f"Adding {len(results_data)} jobs for {loc} to the spreadsheet.")
        all_jobs.extend(results_data)
            
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        output_filename = "linkedin_jobs.xlsx"
        df.to_excel(output_filename, index=False)
        print(f"Successfully saved {len(all_jobs)} jobs to {output_filename}")
        logger.info(f"Successfully saved {len(all_jobs)} jobs to {output_filename}")
        return output_filename
        
    return None
