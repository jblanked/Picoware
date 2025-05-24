from gc import collect, mem_free, mem_alloc
from json import dump, loads
from storage import enable_usb_drive, remount, disable_usb_drive


class Storage:
    """Class to control the storage on a Raspberry Pi Pico device."""

    def __init__(self):
        self._mounted = False

    def deserialize(self, json_dict: dict, file_path: str) -> None:
        """Deserialize a JSON object and write it to a file."""
        if not self._mounted:
            self.mount()
        with open(file_path, "w") as f:
            dump(json_dict, f)

    def execute_script(self, file_path: str = "/") -> None:
        """Run a Python file from the storage."""
        with open(file_path, "r") as f:
            code = compile(f.read(), file_path, "exec")
            exec(code, globals())

    def free(self) -> None:
        """Run garbage collection to free up memory."""
        collect()

    def heap_free(self) -> int:
        """Return the amount of free heap memory."""
        return mem_free()

    def heap_used(self) -> int:
        """Return the total heap memory used."""
        return mem_alloc()

    def mount(self, read_only: bool = False, print_errors: bool = False) -> bool:
        """
        Mount the CIRCUITPY filesystem over USB so it's visible to the host.

        :param readonly: if True, the drive is presented read-only to the host.
        :note: This will fail if the REPL is active.
        """
        try:
            enable_usb_drive()
            remount("/", readonly=read_only)
            self._mounted = True
            return True
        except Exception as e:
            if print_errors:
                print(f"Failed to mount storage: {e}")
            return False

    def read(self, file_path: str, mode: str = "r") -> str:
        """Read and return the contents of a file."""
        if not self._mounted:
            self.mount()
        with open(file_path, mode) as f:
            return f.read()

    def serialize(self, file_path: str) -> dict:
        """Read a file and return its contents as a JSON object."""
        if not self._mounted:
            self.mount()
        with open(file_path, "r") as f:
            return loads(f.read())

    def write(self, file_path: str, data: str, mode: str = "w") -> None:
        """Write data to a file, creating or overwriting as needed."""
        if not self._mounted:
            self.mount()
        with open(file_path, mode) as f:
            f.write(data)

    def unmount(self, print_errors: bool = False) -> bool:
        """
        Unmount the CIRCUITPY filesystem from USB so it's not visible to the host.
        :note: This will fail if the REPL is active.
        """
        try:
            remount("/", readonly=True)  # avoid host writes
            disable_usb_drive()
            return True
        except Exception as e:
            if print_errors:
                print(f"Failed to unmount storage: {e}")
            return False
