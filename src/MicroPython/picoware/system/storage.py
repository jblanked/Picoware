from picoware.system.boards import (
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
)


class Storage:
    """
    Class to control the storage on a Raspberry Pi Pico device.
    """

    def __init__(self, auto_mount: bool = False):
        """
        Initialize the storage class.

        :param bool auto_mount: Will automatically mount the SD card before performing any operations and unmount it afterwards.
        """
        from picoware_boards import get_current_id

        self._current_board_id = get_current_id()
        self.sd = None

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import init

            init()
        elif self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            pass  # No SD storage on this board
        else:
            from picoware.system.drivers.EasySD import EasySD

            self.sd = EasySD(auto_mount=auto_mount)

    def __del__(self):
        """Destructor to ensure SD card is unmounted."""
        self.unmount()

        if self.sd:
            del self.sd
            self.sd = None

    @property
    def active(self) -> bool:
        """Returns True if the storage is active (mounted)."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import is_initialized

            return is_initialized()
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        return self.sd is not None

    def close(self, file_obj) -> None:
        """Close the storage and release resources."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import close

            close(file_obj)

    def deserialize(self, json_dict: dict, file_path: str) -> None:
        """Deserialize a JSON object and write it to a file."""
        from json import dump, dumps

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import write

            try:
                json_str = dumps(json_dict)
                write(file_path, json_str.encode("utf-8"), True)
            except Exception as e:
                print(f"Error writing JSON to file {file_path}: {e}")
            return

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return

        if self.sd is None:
            raise RuntimeError("SD card not initialized")

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
            if not self.sd.auto_mount and self.sd.is_mounted:
                self.unmount()

    def execute_script(self, file_path: str = "/") -> None:
        """Run a Python file from the storage."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import read

            script_content = read(file_path, 0, 0).decode("utf-8")
            code = compile(script_content, file_path, "exec")
            exec(code, globals())
            return
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return

        if self.sd is None:
            raise RuntimeError("SD card not initialized")

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
            if not self.sd.auto_mount and self.sd.is_mounted:
                self.unmount()

    def exists(self, path: str) -> bool:
        """Check if a file or directory exists."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import exists

            return exists(path)

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        if self.sd is None:
            return False

        # try to open the file/directory
        file_handle = self.sd.open(path, "r")
        if file_handle is None:
            return False
        file_handle.close()
        return True

    def file_read(self, file_obj) -> str:
        """Read from an open file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_read

            return file_read(file_obj, 0, 0).decode("utf-8")
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return ""  # Waveshare SD module does not support file read yet
        return file_obj.read()

    def file_seek(self, file_obj, position: int) -> None:
        """Seek to a specific position in an open file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_seek

            file_seek(file_obj, position)
        elif self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            pass  # Waveshare SD module does not support file seek yet
        else:
            file_obj.seek(position)

    def file_write(self, file_obj, data: str, mode: str = "w") -> bool:
        """Write data to an open file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_write

            try:
                if mode == "w":
                    return file_write(file_obj, data.encode("utf-8"), True)
                if mode == "a":
                    return file_write(file_obj, data.encode("utf-8"), False)
                return file_write(file_obj, data, False)
            except Exception as e:
                print(f"Error writing to file {file_obj}: {e}")
                return False

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # Waveshare SD module does not support file write yet
        try:
            count = file_obj.write(data)
            return count == len(data)
        except MemoryError as e:
            print(f"Memory error writing to file: {e}")
            return False
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import is_directory

            return is_directory(path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        if self.sd is None:
            return False

        return self.sd.is_directory(path)

    def listdir(self, path: str = "/sd") -> list[str]:
        """List files in a directory.

        Args:
            path: Directory path to list (default: "/sd")

        Returns:
            List of filenames in the directory
        """
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return []  # Waveshare SD module does not support listdir yet

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import read_directory

            return [item["filename"] for item in read_directory(path)]

        if self.sd is None:
            return []

        return self.sd.listdir(path)

    def mkdir(self, path: str = "/sd") -> bool:
        """Create a new directory."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import create_directory

            return create_directory(path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        if self.sd is None:
            return False

        return self.sd.mkdir(path)

    def mount(self, mount_point: str = "/sd") -> bool:
        """Mount the SD card."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import mount

            try:
                return mount()
            except Exception as e:
                print(f"Error mounting SD card: {e}")
                return False
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        if self.sd is None:
            return False
        if self.sd.is_mounted:
            return True
        return self.sd.mount(mount_point)

    def open(self, file_path: str, mode: str = "r"):
        """Open a file and return the file handle."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import open

            return open(file_path, mode)

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return None  # No SD storage on this board

        if self.sd is None:
            return None

        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                return None

        return self.sd.open(file_path, mode)

    def read(self, file_path: str, mode: str = "r") -> str:
        """Read and return the contents of a file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import read

            try:
                return read(file_path, 0, 0).decode("utf-8")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return ""

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return ""  # No SD storage on this board

        if self.sd is None:
            return ""

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
            if not self.sd.auto_mount and self.sd.is_mounted:
                self.unmount()

    def read_chunked(
        self, file_path: str, start: int = 0, chunk_size: int = 1024
    ) -> bytes:
        """
        Read a chunk of data from a file without loading the entire file.

        :param str file_path: Path to the file to read
        :param int start: Starting byte position (offset) in the file
        :param int chunk_size: Number of bytes to read from the start position
        :return bytes: The chunk of data read from the file
        """
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import read

            try:
                return read(file_path, start, chunk_size)  # returns bytes
            except Exception as e:
                print(f"Error reading chunk from file {file_path}: {e}")
                return b""

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return b""  # No SD storage on this board

        if self.sd is None:
            return b""

        # Handle mounting if needed
        if not self.sd.is_mounted and not self.sd.auto_mount:
            if not self.mount():
                return b""

        file_handle = self.sd.open(file_path, "rb")  # Open in binary mode
        if file_handle is None:
            return b""

        try:
            with file_handle as f:
                # Seek to the starting position
                f.seek(start)
                # Read only the requested chunk
                return f.read(chunk_size)
        except Exception as e:
            print(f"Error reading chunk from file {file_path}: {e}")
            return b""
        finally:
            if not self.sd.auto_mount and self.sd.is_mounted:
                self.unmount()

    def remove(self, file_path: str) -> bool:
        """Remove a file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import remove

            return remove(file_path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        if self.sd is None:
            return False

        return self.sd.remove(file_path)

    def rename(self, old_path: str, new_path: str) -> bool:
        """Rename a file or directory."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import rename

            try:
                return rename(old_path, new_path)
            except Exception as e:
                print(f"Error renaming from {old_path} to {new_path}: {e}")
                return False
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        if self.sd is None:
            return False
        return self.sd.rename(old_path, new_path)

    def rmdir(self, path: str) -> bool:
        """Remove a directory."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import remove

            return remove(path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        if self.sd is None:
            return False
        return self.sd.rmdir(path)

    def serialize(self, file_path: str) -> dict:
        """Read a file and return its contents as a JSON object."""
        from json import loads

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import read

            try:
                file_content = read(file_path, 0, 0).decode("utf-8")
                return loads(file_content)
            except Exception as e:
                print(f"Error deserializing file {file_path}: {e}")
                return {}

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return {}  # No SD storage on this board

        if self.sd is None:
            return {}

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
            if not self.sd.auto_mount and self.sd.is_mounted:
                self.unmount()

    def size(self, file_path: str) -> int:
        """Get the size of a file in bytes."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import get_file_size

            return get_file_size(file_path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # No SD storage on this board

        if self.sd is None:
            return 0

        file_handle = self.sd.open(file_path, "r")
        if file_handle is None:
            return 0

        try:
            with file_handle as f:
                f.seek(0, 2)  # Move to end of file
                return f.tell()
        except Exception as e:
            print(f"Error getting size of file {file_path}: {e}")
            return 0

    def write(self, file_path: str, data: str, mode: str = "w") -> bool:
        """Write data to a file, creating or overwriting as needed."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import write

            try:
                if mode == "w":
                    return write(file_path, data.encode("utf-8"), True)
                if mode == "a":
                    return write(file_path, data.encode("utf-8"), False)
                return write(file_path, data, False)
            except Exception as e:
                print(f"Error writing to file {file_path}: {e}")
                return False

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        if self.sd is None:
            return False

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
            if not self.sd.auto_mount and self.sd.is_mounted:
                self.unmount()

    def unmount(self, mount_point: str = "/sd") -> bool:
        """Unmount the SD card."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import unmount

            unmount()
            return True
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        if self.sd is None:
            return False
        return self.sd.unmount(mount_point)
