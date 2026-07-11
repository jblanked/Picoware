"""Tool registry and execution dispatcher."""
from picoware.system.agent.tools.storage import (
    storage_listdir,
    storage_mkdir,
    storage_read,
    storage_remove,
    storage_write,
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

def execute_tool(view_manager, name, args=None, **kwargs):
    """Execute a named tool with the given arguments."""
    payload = {}
    if args and isinstance(args, dict):
        payload.update(args)
    payload.update(kwargs)
    result = get_tool_map()[name](view_manager, **payload)
    return result

def get_tool_map():
    """Return the mapping of tool names to their execution functions."""
    return {
        "storage_listdir": storage_listdir,
        "storage_mkdir": storage_mkdir,
        "storage_read": storage_read,
        "storage_remove": storage_remove,
        "storage_write": storage_write,
        #
        "network_get_info": network_get_info,
        "network_scan_wifi": network_scan_wifi,
        "network_scan_ble": network_scan_ble,
        "network_send_request": network_send_request,
    }

def get_tool_list():
    """Return the list of available tools."""
    return [
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
    ]