import asyncio
import os
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from playwright.async_api import async_playwright

# Global state to maintain the browser session across multiple tool calls from the LLM
_playwright = None
_browser = None
_page = None

async def init_and_navigate(job_link: str) -> str:
    """Initialize the browser, navigate to the job link, and return the visible page context."""
    global _playwright, _browser, _page
    try:
        print(f"[ApplyAgent Tool] Initializing browser and navigating to {job_link}")
        if not _playwright:
            _playwright = await async_playwright().start()
            user_data_dir = r"C:\ChromeProfileForAutomation"
            _browser = await _playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
        
        if not _page:
            _page = await _browser.new_page()
            
        await _page.goto(job_link, timeout=60000)
        await _page.wait_for_timeout(3000)
        
        return await get_page_context()
    except Exception as e:
        return f"Error navigating: {e}"

async def get_page_context() -> str:
    """Extracts the visible text on the page and interactive form fields for the model to reason about."""
    global _page
    if not _page:
        return "Error: Browser not initialized."
    try:
        # Evaluate script to get inputs and visible text, including select options
        context_script = """
        () => {
            const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
                .filter(e => e.type !== 'hidden' && e.offsetWidth > 0 && e.offsetHeight > 0)
                .map(e => {
                    let info = `[${e.tagName.toLowerCase()} type="${e.type}"] css_selector="[name='${e.name}']" id="${e.id}" name="${e.name}" placeholder="${e.placeholder || ''}" aria-label="${e.getAttribute('aria-label') || ''}"`;
                    if (e.tagName.toLowerCase() === 'select') {
                        const options = Array.from(e.options).map(o => `'${o.value}'`).join(', ');
                        info += ` available_options=[${options}]`;
                    }
                    return info;
                });
            
            const text = document.body.innerText.substring(0, 2000);
            return `Interactable Form Fields:\n${inputs.join('\\n')}\n\nPage Text:\n${text}...`;
        }
        """
        page_data = await _page.evaluate(context_script)
        return f"Current Page Context:\n{page_data}"
    except Exception as e:
        return f"Error getting context: {e}"

import re

async def click_element(button_text: str) -> str:
    """Clicks a button or link matching the provided text (e.g., 'Easy Apply', 'Next', 'Submit'). Returns the new page context."""
    global _page
    if not _page:
        return "Error: Browser not initialized."
    try:
        print(f"[ApplyAgent Tool] Attempting to click element containing text: '{button_text}'...")
        
        pattern = re.compile(button_text.strip(), re.IGNORECASE)
        strategies = [
            _page.get_by_role("button", name=pattern),
            _page.get_by_role("link", name=pattern),
            _page.locator(f'button:has-text("{button_text}")'),
            _page.locator(f'span:has-text("{button_text}")')
        ]
        
        clicked = False
        for locator in strategies:
            count = await locator.count()
            for i in range(count):
                element = locator.nth(i)
                if await element.is_visible():
                    print(f"[ApplyAgent Tool] Found visible match, clicking it...")
                    await element.scroll_into_view_if_needed()
                    await element.click(force=True)
                    clicked = True
                    break
            if clicked:
                break
                
        if clicked:
            await _page.wait_for_timeout(4000)
            return await get_page_context()
        else:
            return f"Element with text '{button_text}' not found or not visible. Try a different button text."
    except Exception as e:
        return f"Error clicking element: {e}"

async def fill_element(css_selector: str, value: str) -> str:
    """Fills a form field identified by a CSS selector (e.g., '[name=\"firstName\"]' or '#email'). Returns the new context."""
    global _page
    if not _page:
        return "Error: Browser not initialized."
    try:
        print(f"[ApplyAgent Tool] Attempting to fill '{css_selector}' with '{value}'...")
        element = _page.locator(css_selector).first
        if await element.is_visible():
            await element.scroll_into_view_if_needed()
            
            tag_name = await element.evaluate("e => e.tagName.toLowerCase()")
            if tag_name == "select":
                try:
                    await element.select_option(value)
                except Exception:
                    try:
                        await element.select_option(label=value)
                    except Exception as e:
                        return f"Failed to select option '{value}'. Ensure it matches one of the available_options. Error: {e}"
            elif tag_name == "input" and await element.evaluate("e => e.type === 'file'"):
                return f"Cannot fill file input '{css_selector}' with text. (File uploads currently require manual intervention)."
            else:
                await element.fill(value)
                
            await _page.wait_for_timeout(1000)
            return f"Successfully filled {css_selector} with '{value}'."
        else:
            return f"Input element '{css_selector}' not found or not visible."
    except Exception as e:
        return f"Error filling element: {e}"

async def close_browser() -> str:
    """Closes the browser when the application is complete or failed."""
    global _playwright, _browser, _page
    print("[ApplyAgent Tool] Closing browser...")
    try:
        if _page: await _page.close()
        if _browser: await _browser.close()
        if _playwright: await _playwright.stop()
    except Exception:
        pass
    finally:
        _playwright = None
        _browser = None
        _page = None
    return "Browser closed successfully."

async def run_apply_for_job_agent(job_link: str):
    """
    Subagent that uses Playwright to open a job link, extract context, and reason about applying in a loop.
    """
    if not job_link or job_link == "No URL":
        return
        
    about_me_text = ""
    about_me_path = os.path.join(os.getcwd(), "about_me.md")
    if os.path.exists(about_me_path):
        with open(about_me_path, "r", encoding="utf-8") as f:
            about_me_text = f.read()
            
    # Keep about me context constrained to avoid prompt length issues
    applicant_context = about_me_text[:3500] if about_me_text else "No specific applicant info provided. Use standard placeholders."
        
    apply_agent = Agent(
        name="apply_for_job_agent",
        model="ollama/qwen2.5:7b",
        instruction=f"""You are an autonomous job application assistant. 
        Your goal is to apply for the given job link by interacting with the page.
        
        Follow these instructions exactly:
        1. Call `init_and_navigate(job_link)` to open the page.
        2. Analyze the context returned. Look for text indicating an apply button (e.g., "Easy Apply", "Apply now", "Apply for this job"). Click it using `click_element`.
        3. Once the form opens, analyze the "Interactable Form Fields".
        4. Use the `fill_element(css_selector, value)` tool to fill in details. Derive the css_selector from the context (e.g. `[name='email']` or `#first-name`). 
           CRITICAL: Use the following real applicant data to fill out the form:
           {applicant_context}
        5. For `<select>` fields, look at the `available_options` in the context and pass the exact matching string as the value.
        6. Use the `click_element(button_text)` tool to click "Next", "Review", or "Submit application" to progress.
        7. If the application is submitted successfully OR if you are completely stuck, call `close_browser()`.
        8. Finally, output a brief summary of what happened. If you successfully applied and submitted the application, your final output MUST contain the exact string "APPLICATION_SUCCESS".
        """,
        tools=[init_and_navigate, get_page_context, click_element, fill_element, close_browser]
    )

    session_service = InMemorySessionService()
    import uuid
    session_id = f"apply_{uuid.uuid4()}"
    await session_service.create_session(app_name="app", user_id="user", session_id=session_id)
    runner = Runner(agent=apply_agent, app_name="app", session_service=session_service)

    print(f"\n=======================================================")
    print(f" [ApplyAgent] Starting autonomous application loop")
    print(f" URL: {job_link}")
    print(f"=======================================================\n")
    
    success = False
    try:
        async for event in runner.run_async(
            user_id="user", session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=f"Start the application process for this job: {job_link}")])
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"\n[ApplyAgent Final Status]:\n{part.text}\n")
                        if "APPLICATION_SUCCESS" in part.text:
                            success = True
    except Exception as e:
        print(f"[ApplyAgent] Agent execution failed: {e}")
        await close_browser()
        
    return success
