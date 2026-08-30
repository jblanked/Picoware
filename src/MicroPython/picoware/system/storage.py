"""Storage - SD card file system access."""

from picoware_boards import (
    BOARD_CROWPANEL_10_1,
    BOARD_ID,
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_69_RP2350,
    BOARD_HAS_ESP32,
    BOARD_FLIPPER_ZERO,
)

try:
    import sd_mp

    class FAT32File(sd_mp.fat32_file):
        """Represents a fat32_mp_t structure on the FAT32 filesystem.

        Attributes:
        - is_open: Indicates if the file is currently open
        - last_entry_read: The last directory entry read from the file
        - attributes: The file attributes (e.g., read-only, hidden, system, etc.)
        - start_cluster: The starting cluster of the file on the SD card
        - current_cluster: The current cluster being accessed in the file
        - file_size: The total size of the file in bytes
        - position: The current read/write position within the file in bytes
        - dir_entry_sector: The sector number of the directory entry for this file
        - dir_entry_offset: The byte offset within the directory sector for this file's entry
        """

        def __setattr__(self, name, value):
            """Set a file attribute, routing position through the C setter.

            Args:
                name (str): The attribute name to set.
                value (object): The new value for the attribute.
            """
            if name == "position":
                self.set_position(value)
            else:
                super().__setattr__(name, value)

except ImportError:
    # waveshare 1.28, waveshare 1.69, and crowpanel
    pass


class Storage:
    """Control the storage on a Raspberry Pi Pico device."""

    __slots__ = ("_vfs_mounted", "_has_storage")

    def __init__(self):
        """Initialize the storage class and mount the SD card."""
        self._vfs_mounted = False
        self._has_storage = True

        if BOARD_ID in (
            BOARD_WAVESHARE_1_28_RP2350,
            BOARD_WAVESHARE_1_69_RP2350,
            BOARD_CROWPANEL_10_1,
        ):
            self._has_storage = False
        else:
            sd_mp.init()
            sd_mp.mount()

    def __del__(self):
        """Destructor to ensure SD card is unmounted."""
        try:
            self.unmount()
        except Exception:
            pass

    @property
    def active(self) -> bool:
        """Returns True if the storage is active (mounted)."""
        if not self._has_storage:
            return False  # No SD storage on this board
        return sd_mp.is_initialized()

    @property
    def free_space(self) -> int:
        """Returns the free space on the SD card in bytes."""
        if not self._has_storage:
            return 0 
        return sd_mp.get_free_space()

    @property
    def total_space(self) -> int:
        """Return total SD-card capacity in bytes."""
        if not self._has_storage:
            return 0
        return sd_mp.get_total_space()

    @property
    def vfs_mounted(self) -> bool:
        """Returns True if the VFS is mounted (allows use of open(), __import__, etc.)."""
        return self._vfs_mounted

    @property
    def vfs_prefix(self) -> str:
        """Returns the filesystem path prefix for VFS access.

        On Cardputer the SD card is exposed at /sdcard via the C POSIX bridge;
        on all other boards it is mounted at /sd by mount_vfs().
        """
        if BOARD_HAS_ESP32 == 1:
            return "/sdcard"
        return "/sd"

    def copy(
        self, source_path: str, destination_path: str, bytes_per_chunk: int = 2048
    ) -> bool:
        """Copy a file or directory from source_path to destination_path.

        Args:
            source_path (str): The source file or directory path.
            destination_path (str): The destination file or directory path.
            bytes_per_chunk (int): Bytes per copy chunk. Defaults to 2048.

        Returns:
            bool: True if the copy succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        try:
            sd_mp.copy(source_path, destination_path, bytes_per_chunk)
            return True
        except Exception as e:
            print(f"Error copying from {source_path} to {destination_path}: {e}")
            return False

    def deserialize(self, json_dict: dict, file_path: str) -> bool:
        """Write a JSON object to a file.

        Args:
            json_dict (dict): The JSON object to write.
            file_path (str): The path of the file to write.

        Returns:
            bool: True if the write succeeded, False otherwise.
        """
        from json import dumps

        if not self._has_storage:
            return False

        try:
            json_str = dumps(json_dict)
            return sd_mp.write(file_path, json_str.encode("utf-8"), True)
        except Exception as e:
            print(f"Error writing JSON to file {file_path}: {e}")
            return False

    def execute_script(self, file_path: str = "/") -> None:
        """Run a Python file from the storage.

        Args:
            file_path (str): The path of the script to run. Defaults to "/".
        """
        if not self._has_storage:
            return

        script_content = sd_mp.read(file_path, 0, 0).decode("utf-8")
        code = compile(script_content, file_path, "exec")
        exec(code, globals())

    def exists(self, path: str) -> bool:
        """Check if a file or directory exists.

        Args:
            path (str): The path to check.

        Returns:
            bool: True if the path exists, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        return sd_mp.exists(path)

    def file_close(self, file_obj: FAT32File) -> None:
        """Close an open file handle.

        Args:
            file_obj (FAT32File): The open file handle to close.
        """
        if not self._has_storage:
            return  # No SD storage on this board
        sd_mp.file_close(file_obj)

    def file_copy(
        self, source_file: FAT32File, destination_path: str, bytes_per_chunk: int = 2048
    ) -> bool:
        """Copy an open file to a new location.

        Args:
            source_file (FAT32File): The open source file handle.
            destination_path (str): The destination file path.
            bytes_per_chunk (int): Bytes per copy chunk. Defaults to 2048.

        Returns:
            bool: True if the copy succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        try:
            sd_mp.file_copy(source_file, destination_path, bytes_per_chunk)
            return True
        except Exception as e:
            print(f"Error copying file to {destination_path}: {e}")
            return False

    def file_move(
        self, source_file: FAT32File, destination_path: str, bytes_per_chunk: int = 2048
    ) -> bool:
        """Move an open file to a new location.

        Args:
            source_file (FAT32File): The open source file handle.
            destination_path (str): The destination file path.
            bytes_per_chunk (int): Bytes per move chunk. Defaults to 2048.

        Returns:
            bool: True if the move succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        try:
            sd_mp.file_move(source_file, destination_path, bytes_per_chunk)
            return True
        except Exception as e:
            print(f"Error moving file to {destination_path}: {e}")
            return False

    def file_open(self, file_path: str) -> FAT32File:
        """Open a file and return the file handle.

        Args:
            file_path (str): The path of the file to open.

        Returns:
            FAT32File: The open file handle, or None on failure.
        """
        if not self._has_storage:
            return None  # No SD storage on this board

        try:
            return sd_mp.file_open(file_path)
        except Exception as e:
            print(f"Error opening file {file_path}: {e}")
            return None

    def file_read(
        self, file_obj: FAT32File, index: int = 0, count: int = 0, decode: bool = True
    ):
        """Read data from an open file.

        Args:
            file_obj (FAT32File): The open file handle.
            index (int): Starting byte position. Defaults to 0.
            count (int): Number of bytes to read. Defaults to 0.
            decode (bool): Whether to decode as UTF-8. Defaults to True.

        Returns:
            str or bytes: The read data.
        """
        if not self._has_storage:
            return ""  # no SD storage on this board

        return (
            sd_mp.file_read(file_obj, index, count).decode("utf-8")
            if decode
            else sd_mp.file_read(file_obj, index, count)
        )

    def file_readinto(self, file_obj: FAT32File, buffer: bytearray) -> int:
        """Read data from an open file into a pre-allocated buffer.

        Args:
            file_obj (FAT32File): The open file handle.
            buffer (bytearray): The buffer to read into.

        Returns:
            int: The number of bytes read.
        """
        if not self._has_storage:
            return 0  # Waveshare SD module does not support file readinto yet

        return sd_mp.file_readinto(file_obj, buffer)

    def file_seek(self, file_obj: FAT32File, position: int) -> bool:
        """Seek to a specific position in an open file.

        Args:
            file_obj (FAT32File): The open file handle.
            position (int): The byte position to seek to.

        Returns:
            bool: True if the seek succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # Waveshare SD module does not support file seek yet

        try:
            sd_mp.file_seek(file_obj, position)
            return True
        except Exception as e:
            print(f"Error seeking in file: {e}")
            return False

    def file_write(self, file_obj: FAT32File, data, mode: str = "w") -> bool:
        """Write data to an open file.

        Args:
            file_obj (FAT32File): The open file handle.
            data (str or bytes): The data to write.
            mode (str): Write mode ("w", "a", or "wb"). Defaults to "w".

        Returns:
            bool: True if the write succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # Waveshare SD module does not support file write yet

        try:
            if mode in ("w", "a"):
                sd_mp.file_write(file_obj, data.encode("utf-8"))
            else:
                sd_mp.file_write(file_obj, data)
            return True
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory.

        Args:
            path (str): The path to check.

        Returns:
            bool: True if the path is a directory, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        return sd_mp.is_directory(path)

    def listdir(self, path: str = "") -> list[str]:
        """List files in a directory.

        Args:
            path (str): Directory path to list. Defaults to "".

        Returns:
            list[str]: The filenames in the directory.
        """
        if not self._has_storage:
            return []  # Waveshare SD module does not support listdir yet

        try:
            return sd_mp.list_directory(path)
        except Exception as e:
            print(f"Error listing directory {path}: {e}")
            return []

    def mkdir(self, path: str) -> bool:
        """Create a new directory.

        Args:
            path (str): The path of the directory to create.

        Returns:
            bool: True if the directory was created, False otherwise.
        """
        try:
            if not self._has_storage:
                return False  # No SD storage on this board

            return sd_mp.create_directory(path)
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False

    def mount(self) -> bool:
        """Mount the SD card.

        Returns:
            bool: True if mounted successfully, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board
        try:
            return sd_mp.mount()
        except Exception as e:
            print(f"Error mounting SD card: {e}")
            return False

    def mount_vfs(self, mount_point: str = "/sd") -> bool:
        """Mount the SD card as a VFS filesystem.

        This enables the use of Python's built-in open(), __import__, and os
        module functions with paths on the SD card.

        Args:
            mount_point (str): The mount point path. Defaults to "/sd".

        Returns:
            bool: True if mounted successfully, False otherwise.

        Example:
            storage = Storage()
            storage.mount_vfs("/sd")

            with open("/sd/myfile.txt", "r") as f:
                content = f.read()

            import sys
            sys.path.append("/sd/picoware/apps")
            import myapp
        """
        if self._vfs_mounted:
            return True  # Already mounted

        if not self._has_storage:
            return False  # No SD storage on this board

        if BOARD_HAS_ESP32 == 1:
            self._vfs_mounted = True
            return True

        if BOARD_ID == BOARD_FLIPPER_ZERO:
            result = self.mount()
            if result:
                self._vfs_mounted = True
            return result

        try:
            from vfs_mp import mount

            result = mount(mount_point)
            if result:
                self._vfs_mounted = True
            return result
        except ImportError:
            print("module not available - VFS mount not supported")
            return False
        except Exception as e:
            print(f"Error mounting VFS: {e}")
            return False

    def move(self, source_path: str, destination_path: str) -> bool:
        """Move a file or directory from source_path to destination_path.

        Args:
            source_path (str): The source file or directory path.
            destination_path (str): The destination file or directory path.

        Returns:
            bool: True if the move succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        try:
            sd_mp.move(source_path, destination_path)
            return True
        except Exception as e:
            print(f"Error moving from {source_path} to {destination_path}: {e}")
            return False

    def unmount_vfs(self, mount_point: str = "/sd") -> bool:
        """Unmount the VFS filesystem.

        Args:
            mount_point (str): The mount point path. Defaults to "/sd".

        Returns:
            bool: True if unmounted successfully, False otherwise.
        """
        if not self._vfs_mounted or BOARD_HAS_ESP32 == 1:
            return True

        if BOARD_ID == BOARD_FLIPPER_ZERO:
            self.unmount()
            self._vfs_mounted = False
            return True

        try:
            from vfs_mp import umount

            umount(mount_point)
            self._vfs_mounted = False
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"Error unmounting VFS: {e}")
            return False

    def read(self, file_path, mode: str = "r", index: int = 0, count: int = 0):
        """Read and return the contents of a file.

        Args:
            file_path (str): The path of the file to read.
            mode (str): Read mode ("r" for text, otherwise binary). Defaults to "r".
            index (int): Starting byte position. Defaults to 0.
            count (int): Number of bytes to read. Defaults to 0.

        Returns:
            str or bytes: The file contents.
        """
        if not self._has_storage:
            return ""  # No SD storage on this board

        try:
            if mode == "r":
                return sd_mp.read(file_path, index, count).decode("utf-8")
            return sd_mp.read(file_path, index, count)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""

    def readinto(self, file_path, buffer: bytearray) -> int:
        """Read data from a file into a pre-allocated buffer.

        Args:
            file_path (str): The path of the file to read.
            buffer (bytearray): The buffer to read into.

        Returns:
            int: The number of bytes read.
        """
        if not self._has_storage:
            return 0  # No SD storage on this board

        return sd_mp.readinto(file_path, buffer)

    def read_chunked(self, file_path, start: int = 0, chunk_size: int = 1024) -> bytes:
        """Read a chunk of data from a file without loading the entire file.

        Args:
            file_path (str): Path to the file to read.
            start (int): Starting byte position (offset) in the file. Defaults to 0.
            chunk_size (int): Number of bytes to read from the start position. Defaults to 1024.

        Returns:
            bytes: The chunk of data read from the file.
        """
        if not self._has_storage:
            return b""  # No SD storage on this board

        try:
            return sd_mp.read(file_path, start, chunk_size)  # returns bytes
        except Exception as e:
            print(f"Error reading chunk from file {file_path}: {e}")
            return b""

    def read_directory(self, path: str = "") -> list[dict]:
        """Read the contents of a directory and return a list of entries.

        Each entry is a dictionary with keys: filename, size, date, time,
        attributes, and is_directory.

        Args:
            path (str): The directory path to read. Defaults to "".

        Returns:
            list[dict]: The directory entries, or an empty list on failure.
        """
        if not self._has_storage:
            return []  # No SD storage on this board

        try:
            return sd_mp.read_directory(path)
        except Exception as e:
            print(f"Error reading directory {path}: {e}")
            return []

    def remove(self, file_path: str) -> bool:
        """Remove a file or directory.

        Args:
            file_path (str): The path of the file or directory to remove.

        Returns:
            bool: True if removed successfully, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board
        try:
            return sd_mp.remove(file_path)
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
            return False

    def rename(self, old_path: str, new_path: str) -> bool:
        """Rename a file or directory.

        Args:
            old_path (str): The current path.
            new_path (str): The new path.

        Returns:
            bool: True if renamed successfully, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board
        try:
            return sd_mp.rename(old_path, new_path)
        except Exception as e:
            print(f"Error renaming from {old_path} to {new_path}: {e}")
            return False

    def rmdir(self, path: str) -> bool:
        """Remove a directory.

        Args:
            path (str): The path of the directory to remove.

        Returns:
            bool: True if removed successfully, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board
        return sd_mp.remove(path)

    def serialize(self, file_path: str) -> dict:
        """Read a file and return its contents as a JSON object.

        Args:
            file_path (str): The path of the file to read.

        Returns:
            dict: The parsed JSON object, or an empty dict on failure.
        """
        from json import loads

        if not self._has_storage:
            return {}  # No SD storage on this board
        try:
            file_content = sd_mp.read(file_path, 0, 0).decode("utf-8")
            return loads(file_content)
        except Exception as e:
            print(f"Error deserializing file {file_path}: {e}")
            return {}

    def size(self, file_path: str) -> int:
        """Get the size of a file or directory in bytes.

        Args:
            file_path (str): The path to measure.

        Returns:
            int: The size in bytes.
        """
        if not self._has_storage:
            return 0  # No SD storage on this board
        return sd_mp.get_file_size(file_path)

    def write(self, file_path, data: str, mode: str = "w") -> bool:
        """Write data to a file, creating or overwriting as needed.

        Args:
            file_path (str): The path of the file to write.
            data (str): The data to write.
            mode (str): Write mode ("w" to overwrite, "a" to append). Defaults to "w".

        Returns:
            bool: True if the write succeeded, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board

        try:
            if mode == "w":
                return sd_mp.write(file_path, data.encode("utf-8"), True)
            if mode == "a":
                return sd_mp.write(file_path, data.encode("utf-8"), False)
            return sd_mp.write(file_path, data, False)
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
            return False

    def unmount(self) -> bool:
        """Unmount the SD card (including VFS if mounted).

        Returns:
            bool: True if unmounted successfully, False otherwise.
        """
        if not self._has_storage:
            return False  # No SD storage on this board
        try:
            sd_mp.unmount()
        except Exception as e:
            print(f"Error unmounting SD: {e}")
            return False
        return True
