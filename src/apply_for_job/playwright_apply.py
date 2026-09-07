import pandas as pd
from playwright.sync_api import sync_playwright
import time
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_to_jobs(excel_file: str):
    if not os.path.exists(excel_file):
        logger.error(f"File not found: {excel_file}")
        return

    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        return

    with sync_playwright() as p:
        # Use persistent context to keep cookies/login state.
        # This will open a browser where you can log in once, and it remembers your session.
        user_data_dir = os.path.join(os.getcwd(), "playwright_profile")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, # Set to True if you want it to run in the background after logging in
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page()

        for index, row in df.iterrows():
            link = row.get('Application Web Link')
            title = row.get('Job Title', 'Unknown Title')
            company = row.get('Company', 'Unknown Company')

            if pd.isna(link) or link == 'No URL':
                continue

            logger.info(f"Processing Job: {title} at {company}")

            try:
                page.goto(link, timeout=60000)
                time.sleep(3) # Wait for dynamic elements to load

                # Try to locate the "Easy Apply" button
                # Note: LinkedIn's DOM changes frequently. Selectors might need updating.
                easy_apply_button = page.locator('button:has-text("Easy Apply")').first

                if easy_apply_button.is_visible():
                    easy_apply_button.click()
                    logger.info("Clicked 'Easy Apply'")
                    time.sleep(2)

                    # -------------------------------------------------------------------
                    # TODO: Implement step-by-step form completion here.
                    # LinkedIn easy apply modals contain "Next" or "Review" buttons.
                    # You will need to identify the inputs, fill out phone numbers,
                    # answer specific questions, and eventually click "Submit application".
                    #
                    # Example snippet to click next:
                    # next_button = page.locator('button:has-text("Next")')
                    # if next_button.is_visible():
                    #     next_button.click()
                    # -------------------------------------------------------------------

                    # For safety in this boilerplate, we'll just close the modal instead of submitting.
                    close_btn = page.locator('button[aria-label="Dismiss"]')
                    if close_btn.is_visible():
                        close_btn.click()
                        time.sleep(1)
                        discard_btn = page.locator('button:has-text("Discard")')
                        if discard_btn.is_visible():
                            discard_btn.click()
                else:
                    logger.info("Easy Apply button not found or this job redirects to an external site.")

            except Exception as e:
                logger.error(f"Failed to process {link}: {e}")

            # Wait a few seconds between requests to avoid rate limits
            logger.info("Waiting 5 seconds before next application...")
            time.sleep(5)

        browser.close()

if __name__ == "__main__":
    apply_to_jobs("linkedin_jobs.xlsx")
