"""One OS process of the ADK lab. It does one thing and exits:  start | resume | approve | deny  <repo>

It prints a final line `STATUS {...}` so a driver can see whether the run finished or paused for confirmation.
"""
import asyncio
import json
import sys

from google.adk.tools.tool_confirmation import ToolConfirmation
from google.genai import types

from coverage_agent import APP_NAME, USER, build_runner


async def main(mode: str, repo: str) -> None:
    runner, sessions = build_runner()
    session = await sessions.get_session(app_name=APP_NAME, user_id=USER, session_id=repo)
    kwargs: dict = {}
    if mode == "start":
        if not session:
            await sessions.create_session(app_name=APP_NAME, user_id=USER, session_id=repo)
        kwargs["new_message"] = types.Content(role="user", parts=[types.Part(text=f"Improve test coverage. repo={repo}")])
    elif mode == "resume":
        kwargs["invocation_id"] = session.events[-1].invocation_id
    else:
        ask = next(e for e in reversed(session.events) for c in e.get_function_calls() if c.name == "adk_request_confirmation")
        call = next(c for c in ask.get_function_calls() if c.name == "adk_request_confirmation")
        confirmation = ToolConfirmation(confirmed=(mode == "approve"))
        kwargs["invocation_id"] = ask.invocation_id
        kwargs["new_message"] = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
            id=call.id, name="adk_request_confirmation", response=confirmation.model_dump(by_alias=True)))])
    paused, final = None, None
    async for event in runner.run_async(user_id=USER, session_id=repo, **kwargs):
        for call in event.get_function_calls():
            if call.name == "adk_request_confirmation":
                paused = call.id
        if event.is_final_response() and event.content and event.content.parts and event.content.parts[0].text:
            final = event.content.parts[0].text
    print("STATUS " + json.dumps({"paused_for_confirmation": paused is not None, "final": final}))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
