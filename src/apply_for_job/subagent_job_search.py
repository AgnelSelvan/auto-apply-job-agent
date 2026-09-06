import sqlite3
import asyncio
import json
import urllib.parse
import warnings
import os
from typing import List, Dict, Any

warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from playwright.async_api import async_playwright

from .scraper import scrape_job_details
from .ollama import calculate_match_percentage_async

def init_db(db_name="jobs.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            job_application_link TEXT,
            job_location TEXT,
            job_poster TEXT,
            matching_percentage REAL,
            job_description TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN job_description TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

_search_called = False
_store_called = False

def reset_inner_tools():
    global _search_called, _store_called
    _search_called = False
    _store_called = False

async def search_jobs_on_linkedin(role: str, location: str) -> str:
    """
    Search LinkedIn for jobs based on role and location using Playwright.
    Returns a JSON string of up to 5 job applications.
    """
    global _search_called
    if _search_called:
        return "ERROR: You already searched for jobs. DO NOT call this tool again. Proceed to store them."
    _search_called = True

    print(f"\n[SubAgent] Searching LinkedIn for '{role}' in '{location}'...")
    jobs = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            encoded_query = urllib.parse.quote(role)
            encoded_location = urllib.parse.quote(location)
            url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}"

            await page.goto(url)
            try:
                await page.wait_for_selector("div.base-card, li.jobs-search-results__list-item", timeout=10000)
            except Exception:
                print("[SubAgent] Timeout waiting for job cards, proceeding with what loaded.")

            await page.evaluate("window.scrollBy(0, 500);")
            await page.wait_for_timeout(2000)

            cards = await page.query_selector_all("div.base-card, li.jobs-search-results__list-item")

            about_me_text = ""
            about_me_path = os.path.join(os.getcwd(), "about_me.md")
            if os.path.exists(about_me_path):
                with open(about_me_path, "r", encoding="utf-8") as f:
                    about_me_text = f.read()

            for card in cards[:5]:
                title_elem = await card.query_selector("h3, .job-card-list__title, .job-card-container__link, strong")
                title = await title_elem.inner_text() if title_elem else "No Title"

                company_elem = await card.query_selector("h4, .job-card-container__primary-description, .job-card-container__company-name, .job-card-list__company-name, span.hidden-nested-link")
                company = await company_elem.inner_text() if company_elem else "Unknown Company"

                url_elem = await card.query_selector("a.base-card__full-link, a.job-card-list__title, a.job-card-container__link, a")
                link = await url_elem.get_attribute("href") if url_elem else "No URL"

                if link and link != 'No URL' and 'linkedin.com' not in link:
                    if link.startswith('/'):
                        link = f"https://www.linkedin.com{link}"

                job_description = ""
                matching_percentage = 0.0

                if link != "No URL":
                    try:
                        print(f"[SubAgent] Scraping details for {title}...")
                        job_description, _, _ = scrape_job_details(link)

                        if job_description and about_me_text:
                            print(f"[SubAgent] Calculating match percentage for {title}...")
                            matching_percentage = await calculate_match_percentage_async(job_description, about_me_text)
                    except Exception as scrape_e:
                        print(f"[SubAgent] Failed to scrape or match {link}: {scrape_e}")

                jobs.append({
                    "job_title": title.strip(),
                    "job_poster": company.strip(),
                    "job_application_link": link.strip(),
                    "job_location": location,
                    "matching_percentage": matching_percentage,
                    "job_description": job_description
                })

            await browser.close()
    except Exception as e:
        print(f"\n[SubAgent] Error during Playwright search: {e}")
        return f"Error: {e}"

    print(f"\n[SubAgent] Found {len(jobs)} jobs.")
    
    try:
        print(f"\n[SubAgent] Storing jobs into SQLite database...")
        init_db()
        conn = sqlite3.connect("jobs.db")
        cursor = conn.cursor()
        for job in jobs:
            cursor.execute('''
                INSERT INTO jobs (job_title, job_application_link, job_location, job_poster, matching_percentage, job_description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                job.get("job_title", ""),
                job.get("job_application_link", ""),
                job.get("job_location", ""),
                job.get("job_poster", ""),
                job.get("matching_percentage", 0.0),
                job.get("job_description", "")
            ))
        conn.commit()
        conn.close()
        print(f"\n[SubAgent] Successfully stored {len(jobs)} jobs in jobs.db.")
    except Exception as e:
        print(f"\n[SubAgent] Error storing jobs: {e}")
        return f"Failed to store jobs: {e}"

    stored_jobs_summary = "\n".join([f"- {j.get('job_title', 'Unknown')} at {j.get('job_poster', 'Unknown')} (Match: {j.get('matching_percentage', 0):.1f}%)" for j in jobs])
    return f"Successfully searched and stored {len(jobs)} jobs in jobs.db. Here are the jobs and their match percentages you should list to the user:\n{stored_jobs_summary}"

# Global flag to prevent loop
_job_search_called_this_turn = False

def reset_job_search_flag():
    global _job_search_called_this_turn
    _job_search_called_this_turn = False
    global _search_called
    _search_called = False

async def run_job_search_agent(query: str) -> str:
    """
    Call this tool ONLY when the user explicitly asks to search for jobs, find jobs, or apply to jobs.
    Do NOT call this tool if the user is just saying hello or asking what you can do.
    """
    global _job_search_called_this_turn
    if _job_search_called_this_turn:
        return "ERROR: You already called this tool. DO NOT call any more tools. Output your final response."
    _job_search_called_this_turn = True

    job_search_agent = Agent(
        name="job_search_subagent",
        model="ollama/qwen2.5:7b",
        instruction="""You are a job searching sub-agent.
        You have been given a query. Use the `search_jobs_on_linkedin` tool to search for the role and location.
        This tool will automatically search LinkedIn, scrape the descriptions, compute match percentages, and save the jobs to the database.
        After running the tool, your task is COMPLETE. Reply directly to the user with a conversational response confirming that the jobs were saved. You MUST include a formatted list of the Job Titles, Companies, and their Match Percentages that were found. DO NOT execute any more tools.
        """,
        tools=[search_jobs_on_linkedin]
    )

    async def _run():
        import uuid
        current_sub_session = f"sub1_{uuid.uuid4()}"
        session_service = InMemorySessionService()
        await session_service.create_session(app_name="app", user_id="user", session_id=current_sub_session)
        runner = Runner(agent=job_search_agent, app_name="app", session_service=session_service)

        result_text = ""
        try:
            async for event in runner.run_async(
                user_id="user", session_id=current_sub_session,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=query)])
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            result_text += part.text
        except Exception as e:
            return f"Subagent execution failed: {e}"
        return f"STOP CALLING TOOLS. Output the following text exactly and do nothing else:\n{result_text}"

    return await _run()
