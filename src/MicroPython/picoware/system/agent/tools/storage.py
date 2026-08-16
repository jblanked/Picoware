"""Storage tools for the agent."""

from micropython import const
from picoware.system.agent.tools.tool import Tool, Parameters, Property

VALID_PATH = "Use a portable relative SD path such as 'picoware/apps/example.py'."
MAX_STORAGE_READ_BYTES = const(8192)


def storage_get_info(view_manager) -> dict:
    """Return free and total SD-card capacity in bytes."""
    storage = view_manager.storage
    return {
        "free_space": storage.free_space,
        "total_space": storage.total_space,
    }

def storage_listdir(view_manager, dir_path) ->list[str]:
    """List the contents of a directory on the SD card.

    Args:
        view_manager (ViewManager): The view manager for storage access.
        dir_path (str): The directory path.

    Returns:
        list[str]: A list of filenames.
    """
    storage = view_manager.storage
    return storage.listdir(dir_path)

def storage_mkdir(view_manager, dir_path) -> bool:
    """Create a directory on the SD card.

    Args:
        view_manager (ViewManager): The view manager for storage access.
        dir_path (str): The directory path to create.

    Returns:
        bool: True on success.
    """
    storage = view_manager.storage
    return storage.mkdir(dir_path)

def storage_read(view_manager, file_path, mode: str = "r", index: int = 0, count: int = 0):
    """Read the contents of a file from the SD card.

    Args:
        view_manager (ViewManager): The view manager for storage access.
        file_path (str): The file path.
        mode (str): The read mode. Defaults to "r".
        index (int): The byte index to start from. Defaults to 0.
        count (int): The number of bytes to read. Defaults to 8192 and is capped.

    Returns:
        str or bytes: The file contents.
    """
    storage = view_manager.storage
    index = max(0, int(index))
    count = int(count)
    if count <= 0 or count > MAX_STORAGE_READ_BYTES:
        count = MAX_STORAGE_READ_BYTES
    return storage.read(file_path, mode, index, count)

def storage_remove(view_manager, file_path) -> bool:
    """Remove a file or directory from the SD card.

    Args:
        view_manager (ViewManager): The view manager for storage access.
        file_path (str): The path to remove.

    Returns:
        bool: True on success.
    """
    storage = view_manager.storage
    return storage.remove(file_path)

def storage_write(view_manager, file_path, data, mode: str = "w") -> bool:
    """Write data to a file on the SD card.

    Args:
        view_manager (ViewManager): The view manager for storage access.
        file_path (str): The file path.
        data (str or bytes): The data to write.
        mode (str): The write mode. Defaults to "w".

    Returns:
        bool: True on success.
    """
    storage = view_manager.storage
    return storage.write(file_path, data, mode)

TOOL_STORAGE_LISTDIR = Tool(
    name="storage_listdir",
    description="List the contents of a directory on the SD card.",
    parameters=Parameters(
        properties=[
            Property(
                name="dir_path",
                type="string",
                description=VALID_PATH,
                required=True,
            ),
        ]
    ),
)

TOOL_STORAGE_MKDIR = Tool(
    name="storage_mkdir",
    description="Create a directory on the SD card.",
    parameters=Parameters(
        properties=[
            Property(
                name="dir_path",
                type="string",
                description=VALID_PATH,
                required=True,
            ),
        ]
    ),
)

TOOL_STORAGE_READ = Tool(
    name="storage_read",
    description="Read the contents of a file from the SD card.",
    parameters=Parameters(
        properties=[
            Property(
                name="file_path",
                type="string",
                description=VALID_PATH,
                required=True,
            ),
            Property(
                name="mode",
                type="string",
                description="The file mode (e.g. 'r' for read, 'rb' for read binary).",
                enum=["r", "rb"],
            ),
            Property(
                name="index",
                type="integer",
                description="The byte index to start reading from (for partial reads).",
            ),
            Property(
                name="count",
                type="integer",
                description=(
                    "Bytes to read. Zero uses the 8192-byte device limit; "
                    "continue with a larger index for the next page."
                ),
            ),
        ]
    ),
)

TOOL_STORAGE_REMOVE = Tool(
    name="storage_remove",
    description="Remove a file or directory from the SD card.",
    parameters=Parameters(
        properties=[
            Property(
                name="file_path",
                type="string",
                description=VALID_PATH,
                required=True,
            ),
        ]
    ),
)


TOOL_STORAGE_WRITE = Tool(
    name="storage_write",
    description="Write data to a file on the SD card.",
    parameters=Parameters(
        properties=[
            Property(
                name="file_path",
                type="string",
                description=VALID_PATH,
                required=True,
            ),
            Property(
                name="data",
                type="string",
                description="The data to write to the file.",
                required=True,
            ),
            Property(
                name="mode",
                type="string",
                description="The file mode (e.g. 'w' for write, 'wb' for write binary).",
                enum=["w", "a", "wb", "ab"],
            ),
        ]
    ),
)

TOOL_STORAGE_GET_INFO = Tool(
    name="storage_get_info",
    description="Return free and total SD-card capacity in bytes.",
    parameters=Parameters(properties=[]),
)
