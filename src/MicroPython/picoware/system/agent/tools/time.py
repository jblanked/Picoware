"""Time tools for the agent."""
from picoware.system.agent.tools.tool import Tool, Parameters

def time_get_current_time(view_manager) -> str:
    """Get the current time as a string.

    Returns:
        str: The current time in the format "YYYY-MM-DD HH:MM:SS".
    """
    rtc = view_manager.time.rtc
    if rtc is None:
        return "N/A"
    current_time = rtc.datetime()
    return f"{current_time[0]:04d}-{current_time[1]:02d}-{current_time[2]:02d} {current_time[4]:02d}:{current_time[5]:02d}:{current_time[6]:02d}"

TOOL_TIME_GET_CURRENT_TIME = Tool(
    name="time_get_current_time",
    description="Get the current time as a string.",
    parameters=Parameters(properties=[]),
)