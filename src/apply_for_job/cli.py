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

async def run_chat():
    load_dotenv()

    chatbot = Agent(
        name="job_search_chatbot",
        model="ollama/qwen2.5:7b",
        instruction="""You are a helpful and polite job searching assistant.
        When the user sends a message, determine if it is related to job searching (e.g., they provide a role and location).
        - If it IS related to job searching, you must call the `run_job_search_agent` tool with the user's query to trigger the subagent.
        - If the chat is NOT related to job searching or applying for jobs, politely tell the user that you are only able to assist with job searches and applications. DO NOT call any tools.
        """,
        tools=[run_job_search_agent]
    )

    session_service = InMemorySessionService()
    session_id = "chat_session"
    await session_service.create_session(app_name="job_app", user_id="user", session_id=session_id)
    runner = Runner(agent=chatbot, app_name="job_app", session_service=session_service)

    print("======================================================")
    print(" Job Search Chatbot initialized. Type 'exit' to quit. ")
    print("======================================================")

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

        print("Assistant: ", end="", flush=True)
        try:
            async for event in runner.run_async(
                user_id="user", session_id=session_id,
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
