import asyncio
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Global flag to prevent loop
_greeting_called_this_turn = False

def reset_greeting_flag():
    global _greeting_called_this_turn
    _greeting_called_this_turn = False

async def run_greeting_agent(query: str) -> str:
    """
    Call this tool ONLY when the user sends a greeting (like "hi", "hello") or asks "what can you do?".
    Do NOT call this tool for job searches.
    """
    global _greeting_called_this_turn
    if _greeting_called_this_turn:
        return "ERROR: You already called this tool. DO NOT call any more tools. Output your final response."
    _greeting_called_this_turn = True

    greeting_agent = Agent(
        name="greeting_subagent",
        model="ollama/qwen2.5:7b",
        instruction="""You are a helpful greeting sub-agent.
        The user has sent a greeting or asked what you can do.
        Politely greet them and explain that you are a job searching and applying assistant.
        You can help them search for jobs on LinkedIn by role and location, and store them in a database.
        """,
    )

    async def _run():
        import uuid
        current_sub_session = f"sub_greeting_{uuid.uuid4()}"
        print("\n[SubAgent]")
        session_service = InMemorySessionService()
        await session_service.create_session(app_name="app", user_id="user", session_id=current_sub_session)
        runner = Runner(agent=greeting_agent, app_name="app", session_service=session_service)
        print("\n[SubAgent] _run2")

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
        print("result_text: " + result_text)
        return f"STOP CALLING TOOLS. Output the following text exactly and do nothing else:\n{result_text}"

    return await _run()
