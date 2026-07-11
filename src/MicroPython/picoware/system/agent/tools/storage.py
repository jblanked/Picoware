from picoware.system.agent.tools.tool import Tool, Parameters, Property

def storage_listdir(view_manager, dir_path) ->list[str]:
    """List the contents of a directory on the SD card."""
    storage = view_manager.storage
    return storage.listdir(dir_path)

def storage_mkdir(view_manager, dir_path) -> bool:
    """Create a directory on the SD card."""
    storage = view_manager.storage
    return storage.mkdir(dir_path)

def storage_read(view_manager, file_path, mode: str = "r", index: int = 0, count: int = 0):
    """Read the contents of a file from the SD card."""
    storage = view_manager.storage
    return storage.read(file_path, mode, index, count)

def storage_remove(view_manager, file_path) -> bool:
    """Remove a file or directory from the SD card."""
    storage = view_manager.storage
    return storage.remove(file_path)

def storage_write(view_manager, file_path, data, mode: str = "w") -> bool:
    """Write data to a file on the SD card."""
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
                description="The path to the directory on the SD card.",
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
                description="The path to the directory on the SD card.",
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
                description="The path to the file on the SD card.",
                required=True,
            ),
            Property(
                name="mode",
                type="string",
                description="The file mode (e.g. 'r' for read, 'rb' for read binary).",
            ),
            Property(
                name="index",
                type="integer",
                description="The byte index to start reading from (for partial reads).",
            ),
            Property(
                name="count",
                type="integer",
                description="The number of bytes to read (0 for full file).",
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
                description="The path to the file or directory on the SD card.",
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
                description="The path to the file on the SD card.",
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
            ),
        ]
    ),
)