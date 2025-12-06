# Description: A simple library to make working with SD cards easier on the Raspberry Pi Pico W with MicroPython.
# from https://github.com/jblanked/RaspberryPi/tree/main/Pico%20W/Libraries/MicroPython
class EasySD:
    """Class to handle SD card operations using SPI interface on the Raspberry Pi Pico."""

    def __init__(
        self,
        miso_gpio: int = 16,  # GPIO 12
        cs_gpio: int = 17,  # GPIO 13
        sck_gpio: int = 18,  # GPIO 14
        mosi_gpio: int = 19,  # GPIO 15
        auto_mount: bool = False,
    ):
        from machine import SPI, Pin

        self.spi = SPI(0, sck=Pin(sck_gpio), mosi=Pin(mosi_gpio), miso=Pin(miso_gpio))
        self.cs = Pin(cs_gpio, Pin.OUT)
        self.sd = SDCard(self.spi, self.cs)
        self.auto_mount = auto_mount
        self.is_mounted = self.mount() if auto_mount else False

    def __del__(self):
        if self.is_mounted and self.auto_mount:
            self.unmount()
        if self.spi:
            self.spi.deinit()
            self.spi = None
        if self.sd:
            del self.sd
            self.sd = None

    def open(self, file_path: str, mode: str):
        """Open a file using a context manager."""
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return None
        try:
            return open(f"/sd/{file_path}", mode)
        except OSError as e:
            print(f"Error occurred while opening file: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while opening file: {e}")
        return None

    def os_error(self, err: OSError) -> str:
        """Return a human-readable error message based on the OSError code."""
        from errno import ENOENT, EACCES, ECONNREFUSED, EPERM, EIO, ENODEV, EEXIST

        error_messages = {
            ENOENT: "File or directory not found.",
            EACCES: "Permission denied.",
            ECONNREFUSED: "Connection refused.",
            EPERM: "Operation not permitted.",
            EIO: "I/O Error: Possible SD card disconnection or corruption.",
            ENODEV: "No SD card detected.",
            EEXIST: "File or directory already exists.",
        }
        return error_messages.get(err.errno, str(err))

    def mount(self, mount_point: str = "/sd") -> bool:
        """Mount the SD card to the specified mount point. Default is /sd."""
        try:
            from uos import mount

            mount(self.sd, mount_point)
            self.is_mounted = True
            return True
        except OSError as e:
            print(f"Error during mounting: {self.os_error(e)}")
            return False
        except Exception as e:
            print(f"General Error during mounting: {e}")
            return False

    def unmount(self, mount_point: str = "/sd") -> bool:
        """Unmount the SD card from the specified mount point. Default is /sd."""
        try:
            from uos import umount

            umount(mount_point)
            self.is_mounted = False
            return True
        except OSError as e:
            print(f"Error during unmounting: {self.os_error(e)}")
            return False
        except Exception as e:
            print(f"General Error during unmounting: {e}")
            return False

    def write(self, file_path: str, data: str, mode: str = "w") -> bool:
        """Write data to a file. If the file does not exist, it will be created."""
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return False
        try:
            with open(f"/sd/{file_path}", mode) as f:
                f.write(data)
            if self.auto_mount:
                self.unmount()
            return True
        except OSError as e:
            print(f"Error occurred while writing: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while writing: {e}")
        if self.auto_mount:
            self.unmount()
        return False

    def read(self, file_path: str, mode: str = "r") -> str:
        """Read data from a file."""
        returned_data = ""
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return returned_data
        try:
            with open(f"/sd/{file_path}", mode) as f:
                returned_data = f.read()
        except OSError as e:
            print(f"Error occurred while reading: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while reading: {e}")
        finally:
            if self.auto_mount:
                self.unmount()
        return returned_data

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return False
        try:
            from uos import stat

            stats = stat(f"/sd/{path}")
            # In MicroPython, stat returns a tuple where the first element (st_mode) contains file type info
            # Directory check: st_mode & 0o040000 (S_IFDIR)
            is_dir = (stats[0] & 0o170000) == 0o040000
            if self.auto_mount:
                self.unmount()
            return is_dir
        except OSError:
            if self.auto_mount:
                self.unmount()
            return False
        except Exception:
            if self.auto_mount:
                self.unmount()
            return False

    def listdir(self, directory: str = "/sd") -> list:
        """List all files in a directory. Default is /sd."""
        files = []
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return files
        try:
            from uos import listdir

            files = listdir(directory)
            if self.auto_mount:
                self.unmount()
        except OSError as e:
            print(f"Error occurred while listing files: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while listing files: {e}")
        return files

    def mkdir(self, directory: str) -> bool:
        """Create a directory."""
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return False
        try:
            from uos import mkdir

            mkdir(f"/sd/{directory}")
            if self.auto_mount:
                self.unmount()
            return True
        except OSError as e:
            from errno import EEXIST

            if e.errno == EEXIST:
                return True
            print(f"Error occurred while making directory: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while making directory: {e}")
        if self.auto_mount:
            self.unmount()
        return False

    def remove(self, file_path: str) -> bool:
        """Remove a file."""
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return False
        try:
            from uos import remove, stat

            # Check if it's a file or directory
            stats = stat(f"/sd/{file_path}")
            if stats[0] & 0x4000:  # Directory flag in mode
                print("Error: Path is a directory, use rmdir() instead.")
                return False
            remove(f"/sd/{file_path}")
            if self.auto_mount:
                self.unmount()
            return True
        except OSError as e:
            print(f"Error occurred while removing file: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while removing file: {e}")
        if self.auto_mount:
            self.unmount()
        return False

    def rmdir(self, directory: str) -> bool:
        """Remove a directory."""
        is_removed = False
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return is_removed
        try:
            from uos import rmdir

            rmdir(f"/sd/{directory}")
            is_removed = True
        except OSError as e:
            print(f"Error occurred while removing directory: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while removing directory: {e}")
        finally:
            if self.auto_mount:
                self.unmount()
        return is_removed

    def rename(self, old_file_path: str, new_file_path: str) -> bool:
        """Rename a file or directory."""
        is_renamed = False
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return is_renamed
        try:
            from uos import rename

            rename(f"/sd/{old_file_path}", f"/sd/{new_file_path}")
            is_renamed = True
        except OSError as e:
            print(f"Error occurred while renaming: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while renaming: {e}")
        finally:
            if self.auto_mount:
                self.unmount()
        return is_renamed

    def stat(self, file_path: str):
        """Get file stats."""
        stats = ()
        if not self.is_mounted and self.auto_mount:
            if not self.mount():
                return stats
        try:
            from uos import stat

            stats = stat(f"/sd/{file_path}")
        except OSError as e:
            print(f"Error occurred while getting file stats: {self.os_error(e)}")
        except Exception as e:
            print(f"Error occurred while getting file stats: {e}")
        finally:
            if self.auto_mount:
                self.unmount()
        return stats


"""
MicroPython driver for SD cards using SPI bus.

Requires an SPI bus and a CS pin.  Provides readblocks and writeblocks
methods so the device can be mounted as a filesystem.

Modified from MicroPython 0.17's release by Brenton Schulz at Core Electronics - 2022-06-02

Changes for increased read throughput:

Line 19: _CMD_TIMEOUT = const(100) to _CMD_TIMEOUT = const(1000)
Line 172: time.sleep_ms(1) to time.sleep(0.0001)
"""

from micropython import const

_CMD_TIMEOUT = const(1000)

_R1_IDLE_STATE = const(1 << 0)
_R1_ILLEGAL_COMMAND = const(1 << 2)
_TOKEN_CMD25 = const(0xFC)
_TOKEN_STOP_TRAN = const(0xFD)
_TOKEN_DATA = const(0xFE)


class SDCard:
    def __init__(self, spi, cs, baudrate=25000000):
        self.spi = spi
        self.cs = cs
        self.cdv = None

        self.cmdbuf = bytearray(6)
        self.dummybuf = bytearray(512)
        self.tokenbuf = bytearray(1)
        for i in range(512):
            self.dummybuf[i] = 0xFF
        self.dummybuf_memoryview = memoryview(self.dummybuf)

        # initialise the card
        self.init_card(baudrate)

    def init_spi(self, baudrate):
        try:
            master = self.spi.MASTER
        except AttributeError:
            # on ESP8266
            self.spi.init(baudrate=baudrate, phase=0, polarity=0)
        else:
            # on pyboard
            self.spi.init(master, baudrate=baudrate, phase=0, polarity=0)

    def init_card(self, baudrate):

        # init CS pin
        self.cs.init(self.cs.OUT, value=1)

        # init SPI bus; use low data rate for initialisation
        self.init_spi(400000)

        # clock card at least 100 cycles with cs high
        for _ in range(16):
            self.spi.write(b"\xff")

        # CMD0: init card; should return _R1_IDLE_STATE (allow 5 attempts)
        for _ in range(5):
            if self.cmd(0, 0, 0x95) == _R1_IDLE_STATE:
                break
        else:
            raise OSError("no SD card")

        # CMD8: determine card version
        r = self.cmd(8, 0x01AA, 0x87, 4)
        if r == _R1_IDLE_STATE:
            self.init_card_v2()
        elif r == (_R1_IDLE_STATE | _R1_ILLEGAL_COMMAND):
            self.init_card_v1()
        else:
            raise OSError("couldn't determine SD card version")

        # get the number of sectors
        # CMD9: response R2 (R1 byte + 16-byte block read)
        if self.cmd(9, 0, 0, 0, False) != 0:
            raise OSError("no response from SD card")
        csd = bytearray(16)
        self.readinto(csd)
        if csd[0] & 0xC0 == 0x40:  # CSD version 2.0
            self.sectors = ((csd[8] << 8 | csd[9]) + 1) * 1024
        elif csd[0] & 0xC0 == 0x00:  # CSD version 1.0 (old, <=2GB)
            c_size = csd[6] & 0b11 | csd[7] << 2 | (csd[8] & 0b11000000) << 4
            c_size_mult = ((csd[9] & 0b11) << 1) | csd[10] >> 7
            self.sectors = (c_size + 1) * (2 ** (c_size_mult + 2))
        else:
            raise OSError("SD card CSD format not supported")
        # print('sectors', self.sectors)

        # CMD16: set block length to 512 bytes
        if self.cmd(16, 512, 0) != 0:
            raise OSError("can't set 512 block size")

        # set to high data rate now that it's initialised
        self.init_spi(baudrate)

    def init_card_v1(self):
        for _ in range(_CMD_TIMEOUT):
            self.cmd(55, 0, 0)
            if self.cmd(41, 0, 0) == 0:
                self.cdv = 512
                # print("[SDCard] v1 card")
                return
        raise OSError("timeout waiting for v1 card")

    def init_card_v2(self):
        from time import sleep_ms

        for _ in range(_CMD_TIMEOUT):
            sleep_ms(50)
            self.cmd(58, 0, 0, 4)
            self.cmd(55, 0, 0)
            if self.cmd(41, 0x40000000, 0) == 0:
                self.cmd(58, 0, 0, 4)
                self.cdv = 1
                # print("[SDCard] v2 card")
                return
        raise OSError("timeout waiting for v2 card")

    def cmd(self, cmd, arg, crc, final=0, release=True, skip1=False):
        self.cs(0)

        # create and send the command
        buf = self.cmdbuf
        buf[0] = 0x40 | cmd
        buf[1] = arg >> 24
        buf[2] = arg >> 16
        buf[3] = arg >> 8
        buf[4] = arg
        buf[5] = crc
        self.spi.write(buf)

        if skip1:
            self.spi.readinto(self.tokenbuf, 0xFF)

        # wait for the response (response[7] == 0)
        for _ in range(_CMD_TIMEOUT):
            self.spi.readinto(self.tokenbuf, 0xFF)
            response = self.tokenbuf[0]
            if not (response & 0x80):
                # this could be a big-endian integer that we are getting here
                for j in range(final):
                    self.spi.write(b"\xff")
                if release:
                    self.cs(1)
                    self.spi.write(b"\xff")
                return response

        # timeout
        self.cs(1)
        self.spi.write(b"\xff")
        return -1

    def readinto(self, buf):
        from time import sleep

        self.cs(0)

        # read until start byte (0xff)
        for _ in range(_CMD_TIMEOUT):
            self.spi.readinto(self.tokenbuf, 0xFF)
            if self.tokenbuf[0] == _TOKEN_DATA:
                break
            sleep(0.0001)
        else:
            self.cs(1)
            raise OSError("timeout waiting for response")

        # read data
        mv = self.dummybuf_memoryview
        if len(buf) != len(mv):
            mv = mv[: len(buf)]
        self.spi.write_readinto(mv, buf)

        # read checksum
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        self.cs(1)
        self.spi.write(b"\xff")

    def write(self, token, buf):
        self.cs(0)

        # send: start of block, data, checksum
        self.spi.read(1, token)
        self.spi.write(buf)
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        # check the response
        if (self.spi.read(1, 0xFF)[0] & 0x1F) != 0x05:
            self.cs(1)
            self.spi.write(b"\xff")
            return

        # wait for write to finish
        while self.spi.read(1, 0xFF)[0] == 0:
            pass

        self.cs(1)
        self.spi.write(b"\xff")

    def write_token(self, token):
        self.cs(0)
        self.spi.read(1, token)
        self.spi.write(b"\xff")
        # wait for write to finish
        while self.spi.read(1, 0xFF)[0] == 0x00:
            pass

        self.cs(1)
        self.spi.write(b"\xff")

    def readblocks(self, block_num, buf):
        nblocks = len(buf) // 512
        assert nblocks and not len(buf) % 512, "Buffer length is invalid"
        if nblocks == 1:
            # CMD17: set read address for single block
            if self.cmd(17, block_num * self.cdv, 0, release=False) != 0:
                # release the card
                self.cs(1)
                raise OSError(5)  # EIO
            # receive the data and release card
            self.readinto(buf)
        else:
            # CMD18: set read address for multiple blocks
            if self.cmd(18, block_num * self.cdv, 0, release=False) != 0:
                # release the card
                self.cs(1)
                raise OSError(5)  # EIO
            offset = 0
            mv = memoryview(buf)
            while nblocks:
                # receive the data and release card
                self.readinto(mv[offset : offset + 512])
                offset += 512
                nblocks -= 1
            if self.cmd(12, 0, 0xFF, skip1=True):
                raise OSError(5)  # EIO

    def writeblocks(self, block_num, buf):
        nblocks, err = divmod(len(buf), 512)
        assert nblocks and not err, "Buffer length is invalid"
        if nblocks == 1:
            # CMD24: set write address for single block
            if self.cmd(24, block_num * self.cdv, 0) != 0:
                raise OSError(5)  # EIO

            # send the data
            self.write(_TOKEN_DATA, buf)
        else:
            # CMD25: set write address for first block
            if self.cmd(25, block_num * self.cdv, 0) != 0:
                raise OSError(5)  # EIO
            # send the data
            offset = 0
            mv = memoryview(buf)
            while nblocks:
                self.write(_TOKEN_CMD25, mv[offset : offset + 512])
                offset += 512
                nblocks -= 1
            self.write_token(_TOKEN_STOP_TRAN)

    def ioctl(self, op, arg):
        if op == 4:  # get number of blocks
            return self.sectors
