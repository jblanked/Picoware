from picoware.system.boards import (
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
)
from picoware_sd import fat32_file


class Storage:
    """
    Class to control the storage on a Raspberry Pi Pico device.
    """

    def __init__(self):
        """
        Initialize the storage class.
        """
        from picoware_boards import get_current_id

        self._current_board_id = get_current_id()
        self._vfs_mounted = False
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import init

            init()
        elif self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            pass  # No SD storage on this board
        else:
            from picoware_sd import init

            init()

    def __del__(self):
        """Destructor to ensure SD card is unmounted."""
        self.unmount()

    @property
    def active(self) -> bool:
        """Returns True if the storage is active (mounted)."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import is_initialized

            return is_initialized()
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        from picoware_sd import is_initialized

        return is_initialized()

    @property
    def vfs_mounted(self) -> bool:
        """Returns True if the VFS is mounted (allows use of open(), __import__, etc.)."""
        return self._vfs_mounted

    def deserialize(self, json_dict: dict, file_path: str) -> None:
        """Deserialize a JSON object and write it to a file."""
        from json import dumps

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

        from picoware_sd import write

        try:
            json_str = dumps(json_dict)
            write(file_path, json_str.encode("utf-8"), True)
        except Exception as e:
            print(f"Error writing JSON to file {file_path}: {e}")

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

        from picoware_sd import read

        script_content = read(file_path, 0, 0).decode("utf-8")
        code = compile(script_content, file_path, "exec")
        exec(code, globals())

    def exists(self, path: str) -> bool:
        """Check if a file or directory exists."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import exists

            return exists(path)

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        from picoware_sd import exists

        return exists(path)

    def file_close(self, file_obj: fat32_file) -> None:
        """Close the storage and release resources."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_close

            file_close(file_obj)
        elif self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            pass  # No SD storage on this board
        else:
            from picoware_sd import file_close

            file_close(file_obj)

    def file_open(self, file_path: str) -> fat32_file:
        """Open a file and return the file handle."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_open

            return file_open(file_path)

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return None  # No SD storage on this board

        from picoware_sd import file_open

        return file_open(file_path)

    def file_read(
        self, file_obj: fat32_file, index: int = 0, count: int = 0, decode: bool = True
    ):
        """Read from an open file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_read

            return (
                file_read(file_obj, index, count).decode("utf-8")
                if decode
                else file_read(file_obj, index, count)
            )
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return ""  # Waveshare SD module does not support file read yet

        from picoware_sd import file_read

        return (
            file_read(file_obj, index, count).decode("utf-8")
            if decode
            else file_read(file_obj, index, count)
        )

    def file_readinto(self, file_obj: fat32_file, buffer: bytearray) -> int:
        """Read data from an open file into a pre-allocated buffer."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_readinto

            return file_readinto(file_obj, buffer)

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # Waveshare SD module does not support file readinto yet

        from picoware_sd import file_readinto

        return file_readinto(file_obj, buffer)

    def file_seek(self, file_obj: fat32_file, position: int) -> None:
        """Seek to a specific position in an open file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import file_seek

            file_seek(file_obj, position)
        elif self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            pass  # Waveshare SD module does not support file seek yet
        else:
            from picoware_sd import file_seek

            file_seek(file_obj, position)

    def file_write(self, file_obj: fat32_file, data: str, mode: str = "w") -> bool:
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

        from picoware_sd import file_write

        try:
            if mode == "w":
                return file_write(file_obj, data.encode("utf-8"), True)
            if mode == "a":
                return file_write(file_obj, data.encode("utf-8"), False)
            return file_write(file_obj, data, False)
        except Exception as e:
            print(f"Error writing to file {file_obj}: {e}")
            return False

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import is_directory

            return is_directory(path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        from picoware_sd import is_directory

        return is_directory(path)

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

        from picoware_sd import read_directory

        return [item["filename"] for item in read_directory(path)]

    def mkdir(self, path: str = "/sd") -> bool:
        """Create a new directory."""
        try:
            if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
                from waveshare_sd import create_directory

                return create_directory(path)
            if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
                return False  # No SD storage on this board

            from picoware_sd import create_directory

            return create_directory(path)
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False

    def mount(self) -> bool:
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
        from picoware_sd import mount

        try:
            return mount()
        except Exception as e:
            print(f"Error mounting SD card: {e}")
            return False

    def mount_vfs(self, mount_point: str = "/sd") -> bool:
        """
        Mount the SD card as a VFS filesystem.

        This enables the use of Python's built-in open(), __import__,
        os module functions, etc. with paths on the SD card.

        Args:
            mount_point: The mount point path (default: "/sd")

        Returns:
            True if mounted successfully, False otherwise

        Example:
            storage = Storage()
            storage.mount_vfs("/sd")

            # Now you can use standard Python file operations:
            with open("/sd/myfile.txt", "r") as f:
                content = f.read()

            # And import modules from SD card:
            import sys
            sys.path.append("/sd/picoware/apps")
            import myapp  # imports /sd/picoware/apps/myapp.py
        """
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            try:
                from waveshare_vfs import mount

                result = mount(mount_point)
                if result:
                    self._vfs_mounted = True
                return result
            except ImportError:
                print("waveshare_vfs module not available - VFS mount not supported")
                return False
            except Exception as e:
                print(f"Error mounting VFS on Waveshare: {e}")
                return False

        try:
            from picoware_vfs import mount

            result = mount(mount_point)
            if result:
                self._vfs_mounted = True
            return result
        except ImportError:
            print("picoware_vfs module not available - VFS mount not supported")
            return False
        except Exception as e:
            print(f"Error mounting VFS: {e}")
            return False

    def unmount_vfs(self, mount_point: str = "/sd") -> bool:
        """
        Unmount the VFS filesystem.

        Args:
            mount_point: The mount point path (default: "/sd")

        Returns:
            True if unmounted successfully, False otherwise
        """
        if not self._vfs_mounted:
            return True

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            try:
                from waveshare_vfs import umount

                umount(mount_point)
                self._vfs_mounted = False
                return True
            except ImportError:
                return False
            except Exception as e:
                print(f"Error unmounting VFS on Waveshare: {e}")
                return False

        try:
            from picoware_vfs import umount

            umount(mount_point)
            self._vfs_mounted = False
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"Error unmounting VFS: {e}")
            return False

    def read(self, file_path: str, mode: str = "r", index: int = 0, count: int = 0):
        """Read and return the contents of a file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import read

            try:
                if mode == "r":
                    return read(file_path, index, count).decode("utf-8")
                return read(file_path, index, count)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return ""

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return ""  # No SD storage on this board

        from picoware_sd import read

        try:
            if mode == "r":
                return read(file_path, index, count).decode("utf-8")
            return read(file_path, index, count)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""

    def readinto(self, file_path: str, buffer: bytearray) -> int:
        """Read data from an open file into a pre-allocated buffer."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import readinto

            return readinto(file_path, buffer)

        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # No SD storage on this board

        from picoware_sd import readinto

        return readinto(file_path, buffer)

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

        from picoware_sd import read

        try:
            return read(file_path, start, chunk_size)  # returns bytes
        except Exception as e:
            print(f"Error reading chunk from file {file_path}: {e}")
            return b""

    def remove(self, file_path: str) -> bool:
        """Remove a file."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import remove

            return remove(file_path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        from picoware_sd import remove

        return remove(file_path)

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
        from picoware_sd import rename

        try:
            return rename(old_path, new_path)
        except Exception as e:
            print(f"Error renaming from {old_path} to {new_path}: {e}")
            return False

    def rmdir(self, path: str) -> bool:
        """Remove a directory."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import remove

            return remove(path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        from picoware_sd import remove

        return remove(path)

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

        from picoware_sd import read

        try:
            file_content = read(file_path, 0, 0).decode("utf-8")
            return loads(file_content)
        except Exception as e:
            print(f"Error deserializing file {file_path}: {e}")
            return {}

    def size(self, file_path: str) -> int:
        """Get the size of a file in bytes."""
        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import get_file_size

            return get_file_size(file_path)
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # No SD storage on this board

        from picoware_sd import get_file_size

        return get_file_size(file_path)

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

        from picoware_sd import write

        try:
            if mode == "w":
                return write(file_path, data.encode("utf-8"), True)
            if mode == "a":
                return write(file_path, data.encode("utf-8"), False)
            return write(file_path, data, False)
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
            return False

    def unmount(self) -> bool:
        """Unmount the SD card (including VFS if mounted)."""
        # Unmount VFS first if it's mounted
        if self._vfs_mounted:
            self.unmount_vfs()

        if self._current_board_id == BOARD_WAVESHARE_1_43_RP2350:
            from waveshare_sd import unmount

            unmount()
            return True
        if self._current_board_id == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        from picoware_sd import unmount

        unmount()
        return True
