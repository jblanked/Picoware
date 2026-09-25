"""Network tools for the agent."""

from picoware.system.agent.tools.tool import Tool, Parameters, Property

def compile_file(view_manager, file_path: str) -> str:
    """Compile the given file and return the compilation result as a string."""
    _ext = file_path.split('.')[-1]
    s = view_manager.storage

    if _ext == "py":
        mount_status = s.vfs_mounted
        try:
            if not mount_status:
                if not s.mount_vfs():
                    raise RuntimeError("Failed to mount VFS")
            s.execute_script(file_path)
            return "Compilation successful"
        except Exception as e:
            return f"Compilation failed: {e}"
        finally:
            if not mount_status and s.vfs_mounted:
                s.unmount_vfs()

    if _ext == "c":
        from picoware.system.c import C
        c = C()
        return str(c.exec(file_path))

    if _ext == "js":
        from picoware.system.js import JS
        js = JS()
        return str(js.exec(file_path))

    return "Unsupported file extension"

TOOL_COMPILE_FILE = Tool(
    name="compile_file",
    description="Compile the given file and return the compilation result as a string.",
    parameters=Parameters(
        [Property("file_path", "string", "Path to the file to compile", True)]
    ),
)