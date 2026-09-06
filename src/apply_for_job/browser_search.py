import time
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

def search_linkedin_jobs_browser(query: str, location: str) -> List[Dict[str, Any]]:
    """
    Fallback method: Uses standard Selenium to open Google Chrome and search for jobs on LinkedIn.
    """
    logger.info("Initializing browser automation fallback...")

    options = Options()

    # Path to Chrome browser executable (Optional, Selenium usually finds it, but good to be explicit if installed elsewhere)
    # options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    # Set User Data Directory to use existing profiles
    # Make sure to close any existing Chrome browser windows before running this,
    # otherwise Selenium will fail to attach to the profile.
    user_data_dir = r"C:\ChromeProfileForAutomation"
    options.add_argument(f"user-data-dir={user_data_dir}")
    # options.add_argument(r"profile-directory=Default")

    # Anti-crash options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--hide-crash-restore-bubble")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    try:
        # Force kill any existing Chrome processes and chromedrivers
        import subprocess
        import os
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], capture_output=True)
        time.sleep(2)

        # Remove SingletonLock to prevent Chrome from thinking it's already running
        lock_path = os.path.join(user_data_dir, "SingletonLock")
        cookie_path = os.path.join(user_data_dir, "SingletonCookie")
        if os.path.exists(lock_path):
            try: os.remove(lock_path)
            except: pass
        if os.path.exists(cookie_path):
            try: os.remove(cookie_path)
            except: pass

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()
    except Exception as e:
        logger.error(f"Failed to start Google Chrome. **CRITICAL: You must completely close all Google Chrome windows before running this script because it uses your Default profile!** Error: {e}")
        return []

    results_data = []

    try:
        # Navigate to LinkedIn jobs search
        encoded_query = query.replace(' ', '%20')
        encoded_location = location.replace(' ', '%20')
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}"

        logger.info(f"Navigating to {search_url}")
        driver.get(search_url)

        # Wait for the jobs list to load dynamically (especially important when logged in)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.base-card, li.jobs-search-results__list-item, div.job-card-container"))
            )
        except Exception:
            logger.warning("Timeout waiting for job cards to appear. The page might be loading slowly or the structure changed.")
            time.sleep(3) # Extra fallback wait

        # Scroll a bit to trigger lazy loading if needed
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Parse job cards for both logged-in and logged-out states
        job_cards = soup.find_all('div', class_='base-card') or soup.find_all('li', class_='jobs-search-results__list-item') or soup.find_all('div', class_='job-card-container')

        if not job_cards:
            logger.warning("No job cards found on the page. The structure might have changed or login is required.")
        else:
            for card in job_cards:  # Process all job cards on the page
                # Handle different variations of title tags
                title_elem = (card.find('h3') or
                              card.find('a', class_='job-card-list__title') or
                              card.find('a', class_='job-card-container__link') or
                              card.find('strong'))

                # Handle different variations of company tags
                company_elem = (card.find('h4') or
                                card.find('span', class_='job-card-container__primary-description') or
                                card.find('a', class_='job-card-container__company-name') or
                                card.find('span', class_='job-card-list__company-name'))

                # Handle different variations of url tags
                url_elem = (card.find('a', class_='base-card__full-link') or
                            card.find('a', class_='job-card-list__title') or
                            card.find('a', class_='job-card-container__link') or
                            card.find('a'))

                title = title_elem.get_text(strip=True) if title_elem else 'No Title'
                company = company_elem.get_text(strip=True) if company_elem else 'Unknown Company'
                url = url_elem.get('href', 'No URL') if url_elem else 'No URL'

                if url != 'No URL' and 'linkedin.com' not in url:
                    if url.startswith('/'):
                        url = f"https://www.linkedin.com{url}"

                if url != 'No URL':
                    results_data.append({
                        'Job Title': title,
                        'Company': company,
                        'Application Web Link': url,
                        'Location': location
                    })

        logger.info(f"Successfully fetched {len(results_data)} jobs from browser search")

    except Exception as e:
        logger.error(f"Error during browser automation: {e}")
    finally:
        # Close the browser
        driver.quit()

    return results_data
    
def fetch_jd_from_url(url: str) -> str:
    """Opens a single URL and extracts the body text."""
    options = Options()
    user_data_dir = r"C:\ChromeProfileForAutomation"
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--hide-crash-restore-bubble")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    
    try:
        import subprocess
        import os
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], capture_output=True)
        time.sleep(2)
        
        lock_path = os.path.join(user_data_dir, "SingletonLock")
        cookie_path = os.path.join(user_data_dir, "SingletonCookie")
        if os.path.exists(lock_path):
            try: os.remove(lock_path)
            except: pass
        if os.path.exists(cookie_path):
            try: os.remove(cookie_path)
            except: pass
            
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
        # Extract body text
        page_text = driver.find_element(By.TAG_NAME, "body").text
        driver.quit()
        return page_text
        
    except Exception as e:
        logger.error(f"Error fetching JD from {url}: {e}")
        return ""
