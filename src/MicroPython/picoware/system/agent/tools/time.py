"""Time tools for the agent."""
from picoware.system.agent.tools.tool import Tool, Parameters

def time_get_current_time(view_manager) -> str:
    """Get the current time as a string.

    Returns:
        str: The current time in the format "YYYY-MM-DD HH:MM:SS".
    """
    return view_manager.time.datetime

TOOL_TIME_GET_CURRENT_TIME = Tool(
    name="time_get_current_time",
    description="Get the current time as a string.",
    parameters=Parameters(properties=[]),
)