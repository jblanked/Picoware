"""Tool registry and execution dispatcher."""
from picoware.system.agent.tools.storage import (
    storage_get_info,
    storage_listdir,
    storage_mkdir,
    storage_read,
    storage_remove,
    storage_write,
    TOOL_STORAGE_GET_INFO,
    TOOL_STORAGE_LISTDIR,
    TOOL_STORAGE_MKDIR,
    TOOL_STORAGE_READ,
    TOOL_STORAGE_REMOVE,
    TOOL_STORAGE_WRITE,
)

from picoware.system.agent.tools.network import (
    network_get_info,
    network_scan_wifi,
    network_scan_ble,
    network_send_request,
    TOOL_NETWORK_GET_INFO,
    TOOL_NETWORK_SCAN_WIFI,
    TOOL_NETWORK_SCAN_BLE,
    TOOL_NETWORK_SEND_REQUEST,
)
from picoware.system.agent.tools.api_reference import (
    picoware_api_search,
    picoware_api_read,
    picoware_app_validate,
    TOOL_PICOWARE_API_SEARCH,
    TOOL_PICOWARE_API_READ,
    TOOL_PICOWARE_APP_VALIDATE,
)


_TOOL_MAP = {
    "storage_get_info": storage_get_info,
    "storage_listdir": storage_listdir,
    "storage_mkdir": storage_mkdir,
    "storage_read": storage_read,
    "storage_remove": storage_remove,
    "storage_write": storage_write,
    "network_get_info": network_get_info,
    "network_scan_wifi": network_scan_wifi,
    "network_scan_ble": network_scan_ble,
    "network_send_request": network_send_request,
    "picoware_api_search": picoware_api_search,
    "picoware_api_read": picoware_api_read,
    "picoware_app_validate": picoware_app_validate,
}

def execute_tool(view_manager, name, args=None, **kwargs):
    """Execute a named tool with the given arguments.

    Args:
        view_manager (ViewManager): The view manager for tool execution.
        name (str): The tool name.
        args (dict or None): The tool arguments. Defaults to None.
        **kwargs: Extra keyword arguments merged into the payload.

    Returns:
        object: The tool result.
    """
    payload = {}
    if args and isinstance(args, dict):
        payload.update(args)
    payload.update(kwargs)
    function = _TOOL_MAP.get(name)
    if function is None:
        raise ValueError("unknown tool: " + str(name))
    result = function(view_manager, **payload)
    return result

def get_tool_map():
    """Return the mapping of tool names to their execution functions."""
    return _TOOL_MAP

def get_tool_list():
    """Return the list of available tools."""
    return [
        TOOL_STORAGE_GET_INFO,
        TOOL_STORAGE_LISTDIR,
        TOOL_STORAGE_MKDIR,
        TOOL_STORAGE_READ,
        TOOL_STORAGE_REMOVE,
        TOOL_STORAGE_WRITE,
        #
        TOOL_NETWORK_GET_INFO,
        TOOL_NETWORK_SCAN_WIFI,
        TOOL_NETWORK_SCAN_BLE,
        TOOL_NETWORK_SEND_REQUEST,
        TOOL_PICOWARE_API_SEARCH,
        TOOL_PICOWARE_API_READ,
        TOOL_PICOWARE_APP_VALIDATE,
    ]
