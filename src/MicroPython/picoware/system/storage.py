class Storage:
    """
    Class to control the storage on a Raspberry Pi Pico device.
    """

    def __init__(self, auto_mount: bool = False):
        """
        Initialize the storage class.

        :param bool auto_mount: Will automatically mount the SD card before performing any operations and unmount it afterwards.
        """
        from picoware.system.drivers.EasySD import EasySD

        self._mounted = False
        self.sd = EasySD(auto_mount=auto_mount)

    def deserialize(self, json_dict: dict, file_path: str) -> None:
        """Deserialize a JSON object and write it to a file."""
        from json import dump

        f = self.sd.with_open(file_path, "w")
        dump(json_dict, f)

    def execute_script(self, file_path: str = "/") -> None:
        """Run a Python file from the storage."""
        f = self.sd.with_open(file_path, "r")
        code = compile(f.read(), file_path, "exec")
        exec(code, globals())

    def listdir(self, path: str = "/sd") -> list:
        """List files in a directory."""
        return self.sd.listdir(path)

    def mount(self, mount_point: str = "/sd") -> bool:
        """Mount the SD card."""
        return self.sd.mount(mount_point)

    def read(self, file_path: str, mode: str = "r") -> str:
        """Read and return the contents of a file."""
        f = self.sd.with_open(file_path, mode)
        return f.read()

    def remove(self, file_path: str) -> bool:
        """Remove a file."""
        return self.sd.remove(file_path)

    def rename(self, old_path: str, new_path: str) -> bool:
        """Rename a file or directory."""
        return self.sd.rename(old_path, new_path)

    def rmdir(self, path: str) -> bool:
        """Remove a directory."""
        return self.sd.rmdir(path)

    def serialize(self, file_path: str) -> dict:
        """Read a file and return its contents as a JSON object."""
        from json import loads

        f = self.sd.with_open(file_path, "r")
        return loads(f.read())

    def write(self, file_path: str, data: str, mode: str = "w") -> None:
        """Write data to a file, creating or overwriting as needed."""
        f = self.sd.with_open(file_path, mode)
        f.write(data)

    def unmount(self, mount_point: str = "/sd") -> bool:
        """Unmount the SD card."""
        return self.sd.unmount(mount_point)
