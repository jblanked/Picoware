from picoware_boards import (
    BOARD_ID,
    BOARD_WAVESHARE_1_28_RP2350,
    BOARD_WAVESHARE_1_43_RP2350,
    BOARD_WAVESHARE_3_49_RP2350,
)

if BOARD_ID in (BOARD_WAVESHARE_1_43_RP2350, BOARD_WAVESHARE_3_49_RP2350):
    from waveshare_sd import fat32_file
    from waveshare_vfs import mount as mount_vfs
    from waveshare_vfs import umount as unmount_vfs
    import waveshare_sd
elif BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
    pass  # no sd card
else:
    from picoware_sd import fat32_file
    from picoware_vfs import mount as mount_vfs
    from picoware_vfs import umount as unmount_vfs
    import picoware_sd


class Storage:
    """
    Class to control the storage on a Raspberry Pi Pico device.
    """

    def __init__(self):
        """
        Initialize the storage class.
        """
        self._vfs_mounted = False
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_sd.init()
        elif BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            pass  # No SD storage on this board
        else:
            picoware_sd.init()

    def __del__(self):
        """Destructor to ensure SD card is unmounted."""
        self.unmount()

    @property
    def active(self) -> bool:
        """Returns True if the storage is active (mounted)."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.is_initialized()
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        return picoware_sd.is_initialized()

    @property
    def vfs_mounted(self) -> bool:
        """Returns True if the VFS is mounted (allows use of open(), __import__, etc.)."""
        return self._vfs_mounted

    def deserialize(self, json_dict: dict, file_path: str) -> None:
        """Deserialize a JSON object and write it to a file."""
        from json import dumps

        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                json_str = dumps(json_dict)
                waveshare_sd.write(file_path, json_str.encode("utf-8"), True)
            except Exception as e:
                print(f"Error writing JSON to file {file_path}: {e}")
            return

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return

        try:
            json_str = dumps(json_dict)
            picoware_sd.write(file_path, json_str.encode("utf-8"), True)
        except Exception as e:
            print(f"Error writing JSON to file {file_path}: {e}")

    def execute_script(self, file_path: str = "/") -> None:
        """Run a Python file from the storage."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            script_content = waveshare_sd.read(file_path, 0, 0).decode("utf-8")
            code = compile(script_content, file_path, "exec")
            exec(code, globals())
            return
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return

        script_content = picoware_sd.read(file_path, 0, 0).decode("utf-8")
        code = compile(script_content, file_path, "exec")
        exec(code, globals())

    def exists(self, path: str) -> bool:
        """Check if a file or directory exists."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.exists(path)

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        return picoware_sd.exists(path)

    def file_close(self, file_obj: fat32_file) -> None:
        """Close the storage and release resources."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_sd.file_close(file_obj)
        elif BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            pass  # No SD storage on this board
        else:
            picoware_sd.file_close(file_obj)

    def file_open(self, file_path: str) -> fat32_file:
        """Open a file and return the file handle."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.file_open(file_path)

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return None  # No SD storage on this board

        return picoware_sd.file_open(file_path)

    def file_read(
        self, file_obj: fat32_file, index: int = 0, count: int = 0, decode: bool = True
    ):
        """Read from an open file."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return (
                waveshare_sd.file_read(file_obj, index, count).decode("utf-8")
                if decode
                else waveshare_sd.file_read(file_obj, index, count)
            )
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return ""  # no SD storage on this board

        return (
            picoware_sd.file_read(file_obj, index, count).decode("utf-8")
            if decode
            else picoware_sd.file_read(file_obj, index, count)
        )

    def file_readinto(self, file_obj: fat32_file, buffer: bytearray) -> int:
        """Read data from an open file into a pre-allocated buffer."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.file_readinto(file_obj, buffer)

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # Waveshare SD module does not support file readinto yet

        return picoware_sd.file_readinto(file_obj, buffer)

    def file_seek(self, file_obj: fat32_file, position: int) -> None:
        """Seek to a specific position in an open file."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_sd.file_seek(file_obj, position)
        elif BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            pass  # Waveshare SD module does not support file seek yet
        else:
            picoware_sd.file_seek(file_obj, position)

    def file_write(self, file_obj: fat32_file, data, mode: str = "w") -> bool:
        """Write data to an open file."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                if mode == "w":
                    return waveshare_sd.file_write(file_obj, data.encode("utf-8"))
                if mode == "a":
                    return waveshare_sd.file_write(file_obj, data.encode("utf-8"))
                return waveshare_sd.file_write(file_obj, data)
            except Exception as e:
                print(f"Error writing to file: {e}")
                return False

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # Waveshare SD module does not support file write yet

        try:
            if mode == "w":
                return picoware_sd.file_write(file_obj, data.encode("utf-8"))
            if mode == "a":
                return picoware_sd.file_write(file_obj, data.encode("utf-8"))
            return picoware_sd.file_write(file_obj, data)
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.is_directory(path)

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        return picoware_sd.is_directory(path)

    def listdir(self, path: str = "/sd") -> list[str]:
        """List files in a directory.

        Args:
            path: Directory path to list (default: "/sd")

        Returns:
            List of filenames in the directory
        """
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return []  # Waveshare SD module does not support listdir yet

        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return [item["filename"] for item in waveshare_sd.read_directory(path)]

        return [item["filename"] for item in picoware_sd.read_directory(path)]

    def mkdir(self, path: str = "/sd") -> bool:
        """Create a new directory."""
        try:
            if BOARD_ID in (
                BOARD_WAVESHARE_1_43_RP2350,
                BOARD_WAVESHARE_3_49_RP2350,
            ):
                return waveshare_sd.create_directory(path)
            if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
                return False  # No SD storage on this board

            return picoware_sd.create_directory(path)
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False

    def mount(self) -> bool:
        """Mount the SD card."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                return waveshare_sd.mount()
            except Exception as e:
                print(f"Error mounting SD card: {e}")
                return False
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        try:
            return picoware_sd.mount()
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
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        try:
            result = mount_vfs(mount_point)
            if result:
                self._vfs_mounted = True
            return result
        except ImportError:
            print("module not available - VFS mount not supported")
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

        try:
            unmount_vfs(mount_point)
            self._vfs_mounted = False
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"Error unmounting VFS: {e}")
            return False

    def read(self, file_path, mode: str = "r", index: int = 0, count: int = 0):
        """Read and return the contents of a file."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                if mode == "r":
                    return waveshare_sd.read(file_path, index, count).decode("utf-8")
                return waveshare_sd.read(file_path, index, count)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return ""

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return ""  # No SD storage on this board

        try:
            if mode == "r":
                return picoware_sd.read(file_path, index, count).decode("utf-8")
            return picoware_sd.read(file_path, index, count)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""

    def readinto(self, file_path, buffer: bytearray) -> int:
        """Read data from an open file into a pre-allocated buffer."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.readinto(file_path, buffer)

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # No SD storage on this board

        return picoware_sd.readinto(file_path, buffer)

    def read_chunked(self, file_path, start: int = 0, chunk_size: int = 1024) -> bytes:
        """
        Read a chunk of data from a file without loading the entire file.

        :param str file_path: Path to the file to read
        :param int start: Starting byte position (offset) in the file
        :param int chunk_size: Number of bytes to read from the start position
        :return bytes: The chunk of data read from the file
        """
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                return waveshare_sd.read(file_path, start, chunk_size)  # returns bytes
            except Exception as e:
                print(f"Error reading chunk from file {file_path}: {e}")
                return b""

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return b""  # No SD storage on this board

        try:
            return picoware_sd.read(file_path, start, chunk_size)  # returns bytes
        except Exception as e:
            print(f"Error reading chunk from file {file_path}: {e}")
            return b""

    def remove(self, file_path: str) -> bool:
        """Remove a file."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.remove(file_path)
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        return picoware_sd.remove(file_path)

    def rename(self, old_path: str, new_path: str) -> bool:
        """Rename a file or directory."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                return waveshare_sd.rename(old_path, new_path)
            except Exception as e:
                print(f"Error renaming from {old_path} to {new_path}: {e}")
                return False
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        try:
            return picoware_sd.rename(old_path, new_path)
        except Exception as e:
            print(f"Error renaming from {old_path} to {new_path}: {e}")
            return False

    def rmdir(self, path: str) -> bool:
        """Remove a directory."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.remove(path)
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        return picoware_sd.remove(path)

    def serialize(self, file_path: str) -> dict:
        """Read a file and return its contents as a JSON object."""
        from json import loads

        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                file_content = waveshare_sd.read(file_path, 0, 0).decode("utf-8")
                return loads(file_content)
            except Exception as e:
                print(f"Error deserializing file {file_path}: {e}")
                return {}

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return {}  # No SD storage on this board
        try:
            file_content = picoware_sd.read(file_path, 0, 0).decode("utf-8")
            return loads(file_content)
        except Exception as e:
            print(f"Error deserializing file {file_path}: {e}")
            return {}

    def size(self, file_path: str) -> int:
        """Get the size of a file in bytes."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            return waveshare_sd.get_file_size(file_path)
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return 0  # No SD storage on this board
        return picoware_sd.get_file_size(file_path)

    def write(self, file_path, data: str, mode: str = "w") -> bool:
        """Write data to a file, creating or overwriting as needed."""
        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            try:
                if mode == "w":
                    return waveshare_sd.write(file_path, data.encode("utf-8"), True)
                if mode == "a":
                    return waveshare_sd.write(file_path, data.encode("utf-8"), False)
                return waveshare_sd.write(file_path, data, False)
            except Exception as e:
                print(f"Error writing to file {file_path}: {e}")
                return False

        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board

        try:
            if mode == "w":
                return picoware_sd.write(file_path, data.encode("utf-8"), True)
            if mode == "a":
                return picoware_sd.write(file_path, data.encode("utf-8"), False)
            return picoware_sd.write(file_path, data, False)
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
            return False

    def unmount(self) -> bool:
        """Unmount the SD card (including VFS if mounted)."""
        # Unmount VFS first if it's mounted
        if self._vfs_mounted:
            self.unmount_vfs()

        if BOARD_ID in (
            BOARD_WAVESHARE_1_43_RP2350,
            BOARD_WAVESHARE_3_49_RP2350,
        ):
            waveshare_sd.unmount()
            return True
        if BOARD_ID == BOARD_WAVESHARE_1_28_RP2350:
            return False  # No SD storage on this board
        picoware_sd.unmount()
        return True
