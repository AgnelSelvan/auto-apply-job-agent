import asyncio
import warnings
import sys

warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .subagent_job_search import run_job_search_agent
from .subagent_greeting import run_greeting_agent

async def run_chat():
    load_dotenv()

    coordinator_agent = Agent(
        name="coordinator_agent",
        model="ollama/qwen2.5:7b",
        instruction="""You are a strict routing assistant. You MUST use the tools provided to answer the user.

        RULES FOR TOOL SELECTION:
        1. If the user says "hi", "hello", "hey", or asks "what can you do?", you MUST call the `run_greeting_agent` tool. DO NOT call `run_job_search_agent`.
        2. If the user asks to search for jobs, find jobs, or apply for jobs (e.g., "find me software engineer jobs in New York"), you MUST call the `run_job_search_agent` tool.
        3. Only use ONE tool per user message.
        4. If the message is a greeting, do NOT assume it's a job search.
        5. CRITICAL: Once you receive the output from the tool you called, output that exact text to the user and STOP immediately. DO NOT call any other tools. DO NOT try to answer further.

        Pass the exact user message as the query argument to whichever tool you choose.
        """,
        tools=[run_greeting_agent, run_job_search_agent]
    )

    session_service = InMemorySessionService()
    session_id = "chat_session"
    await session_service.create_session(app_name="job_app", user_id="user", session_id=session_id)
    runner = Runner(agent=coordinator_agent, app_name="job_app", session_service=session_service)

    print("======================================================")
    print(" Job Search Coordinator initialized. Type 'exit' to quit. ")
    print("======================================================")

    import uuid

    while True:
        try:
            user_input = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.strip().lower() in ['exit', 'quit']:
            print("Goodbye!")
            break

        if not user_input.strip():
            continue

        # Generate a fresh session ID for each turn so the coordinator doesn't get confused by history
        current_session_id = f"chat_session_{uuid.uuid4()}"
        await session_service.create_session(app_name="job_app", user_id="user", session_id=current_session_id)

        # Reset tool execution flags for the new turn
        from .subagent_greeting import reset_greeting_flag
        from .subagent_job_search import reset_job_search_flag
        reset_greeting_flag()
        reset_job_search_flag()

        print("Assistant: ", end="", flush=True)
        try:
            async for event in runner.run_async(
                user_id="user", session_id=current_session_id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
            ):
                # Extract text from all events as they stream in
                try:
                    if hasattr(event, 'error_message') and event.error_message:
                        sys.stdout.write(f"[Model Error: {event.error_message}]")
                        sys.stdout.flush()
                    if hasattr(event, 'content') and event.content:
                        for part in getattr(event.content, 'parts', []):
                            if hasattr(part, 'text') and part.text:
                                sys.stdout.write(part.text)
                                sys.stdout.flush()
                except Exception as err:
                    pass
            print()
        except Exception as e:
            print(f"\n[Error communicating with model: {e}]")

def main():
    """Entry point for the apply-for-job CLI command."""
    asyncio.run(run_chat())

if __name__ == "__main__":
    main()
