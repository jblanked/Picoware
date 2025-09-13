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

    def __del__(self):
        """Destructor to ensure SD card is unmounted."""
        if self._mounted:
            self.unmount()

    def deserialize(self, json_dict: dict, file_path: str) -> None:
        """Deserialize a JSON object and write it to a file."""
        from json import dump

        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                raise RuntimeError("Failed to mount SD card")

        file_handle = self.sd.open(file_path, "w")
        if file_handle is None:
            raise RuntimeError(f"Failed to open file: {file_path}")

        try:
            with file_handle as f:
                dump(json_dict, f)
        finally:
            if not self.sd.auto_mount and self._mounted:
                self.unmount()

    def execute_script(self, file_path: str = "/") -> None:
        """Run a Python file from the storage."""
        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                raise RuntimeError("Failed to mount SD card")

        file_handle = self.sd.open(file_path, "r")
        if file_handle is None:
            raise RuntimeError(f"Failed to open file: {file_path}")

        try:
            with file_handle as f:
                code = compile(f.read(), file_path, "exec")
                exec(code, globals())
        finally:
            if not self.sd.auto_mount and self._mounted:
                self.unmount()

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        return self.sd.is_directory(path)

    def listdir(self, path: str = "/sd") -> list:
        """List files in a directory."""
        return self.sd.listdir(path)

    def mkdir(self, path: str = "/sd") -> bool:
        """Create a new directory."""
        return self.sd.mkdir(path)

    def mount(self, mount_point: str = "/sd") -> bool:
        """Mount the SD card."""
        result = self.sd.mount(mount_point)
        if result:
            self._mounted = True
        return result

    def read(self, file_path: str, mode: str = "r") -> str:
        """Read and return the contents of a file."""
        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                return ""

        file_handle = self.sd.open(file_path, mode)
        if file_handle is None:
            return ""

        try:
            with file_handle as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""
        finally:
            if not self.sd.auto_mount and self._mounted:
                self.unmount()

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

        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                return {}

        file_handle = self.sd.open(file_path, "r")
        if file_handle is None:
            return {}

        try:
            with file_handle as f:
                return loads(f.read())
        except Exception as e:
            print(f"Error deserializing file {file_path}: {e}")
            return {}
        finally:
            if not self.sd.auto_mount and self._mounted:
                self.unmount()

    def write(self, file_path: str, data: str, mode: str = "w") -> bool:
        """Write data to a file, creating or overwriting as needed."""
        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                return False

        file_handle = self.sd.open(file_path, mode)
        if file_handle is None:
            return False

        try:
            with file_handle as f:
                count = f.write(data)
                return count == len(data)
        except MemoryError as e:
            print(f"Memory error writing to file {file_path}: {e}")
            return False
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
            return False
        finally:
            if not self.sd.auto_mount and self._mounted:
                self.unmount()

    def unmount(self, mount_point: str = "/sd") -> bool:
        """Unmount the SD card."""
        result = self.sd.unmount(mount_point)
        if result:
            self._mounted = False
        return result
