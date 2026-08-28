# This file is part of the MicroPython project, http://micropython.org/
#
# The MIT License (MIT)
#
# Copyright (c) 2022 Ibrahim Abdelkader <iabdalkader@openmv.io>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# A minimal esptool implementation to communicate with ESP32 ROM bootloader.
# Note this tool does Not support advanced features, other ESP chips or stub loading.
# This is only meant to be used for updating the U-blox Nina module firmware.

import os
import struct
from micropython import const
from time import sleep
import binascii

from picoware.system.uart import UART

_CMD_SYNC = const(0x08)
_CMD_CHANGE_BAUDRATE = const(0x0F)

_CMD_ESP_READ_REG = const(0x0A)
_CMD_ESP_WRITE_REG = const(0x09)

_CMD_SPI_ATTACH = const(0x0D)
_CMD_SPI_FLASH_MD5 = const(0x13)
_CMD_SPI_FLASH_PARAMS = const(0x0B)
_CMD_SPI_FLASH_BEGIN = const(0x02)
_CMD_SPI_FLASH_DATA = const(0x03)
_CMD_SPI_FLASH_END = const(0x04)

_FLASH_ID = const(0)
_FLASH_REG_BASE = const(0x60002000)
_FLASH_BLOCK_SIZE = const(64 * 1024)
_FLASH_SECTOR_SIZE = const(4 * 1024)
_FLASH_PAGE_SIZE = const(256)

_ESP_ERRORS = {
    0x05: "Received message is invalid",
    0x06: "Failed to act on received message",
    0x07: "Invalid CRC in message",
    0x08: "Flash write error",
    0x09: "Flash read error",
    0x0A: "Flash read length error",
    0x0B: "Deflate error",
}


class ESPFlasher:
    """Flash firmware to an ESP32 ROM bootloader."""

    def __init__(self, reset, gpio0, uart: UART, log_enabled=False):
        """Initialize the ESP32 flasher.

        Args:
            reset (callable): Function used to control the ESP32 reset pin.
            gpio0 (callable): Function used to control the ESP32 GPIO0 pin.
            uart (UART): Picoware UART interface connected to the ESP32.
            log_enabled (bool): Whether to print packet diagnostics. Defaults to False.
        """
        self.uart = uart
        self.reset_pin = reset
        self.gpio0_pin = gpio0
        self.log = log_enabled
        self.baudrate = 115200
        self.md5sum = None
        try:
            import hashlib

            if hasattr(hashlib, "md5"):
                self.md5sum = hashlib.md5()
        except ImportError:
            pass

    def _log(self, data, out=True):
        """Log a packet when diagnostics are enabled.

        Args:
            data (bytes): Packet data to log.
            out (bool): Whether the packet is outgoing. Defaults to True.
        """
        if self.log:
            size = len(data)
            print(
                f"out({size}) => " if out else f"in({size})  <= ",
                "".join("%.2x" % (i) for i in data[0:10]),
            )

    def _uart_drain(self):
        """Drain pending bytes from the UART receive buffer."""
        while self.uart.uart.read(1) is not None:
            pass

    def _read_reg(self, addr):
        """Read a value from an ESP32 flash register.

        Args:
            addr (int): Register offset from the flash register base.

        Returns:
            int: Register value.
        """
        v, d = self._command(_CMD_ESP_READ_REG, struct.pack("<I", _FLASH_REG_BASE + addr))
        if d[0] != 0:
            raise Exception("Command ESP_READ_REG failed.")
        return v

    def _write_reg(self, addr, data, mask=0xFFFFFFFF, delay=0):
        """Write a value to an ESP32 flash register.

        Args:
            addr (int): Register offset from the flash register base.
            data (int): Value to write.
            mask (int): Register write mask. Defaults to 0xFFFFFFFF.
            delay (int): Hardware delay value. Defaults to 0.
        """
        v, d = self._command(
            _CMD_ESP_WRITE_REG, struct.pack("<IIII", _FLASH_REG_BASE + addr, data, mask, delay)
        )
        if d[0] != 0:
            raise Exception("Command ESP_WRITE_REG failed.")

    def _poll_reg(self, addr, flag, retry=10, delay=0.050):
        """Poll a flash register until a flag clears.

        Args:
            addr (int): Register offset from the flash register base.
            flag (int): Bit flag to wait for.
            retry (int): Maximum number of reads. Defaults to 10.
            delay (float): Delay between reads in seconds. Defaults to 0.050.
        """
        for i in range(retry):
            reg = self._read_reg(addr)
            if (reg & flag) == 0:
                break
            sleep(delay)
        else:
            raise Exception(f"Register poll timeout. Addr: 0x{addr:02X} Flag: 0x{flag:02X}.")

    def _write_slip(self, pkt):
        """Write a SLIP-encoded packet to the ESP32.

        Args:
            pkt (bytes): Packet data to encode and write.
        """
        pkt = pkt.replace(b"\xdb", b"\xdb\xdd").replace(b"\xc0", b"\xdb\xdc")
        self.uart.write(b"\xc0" + pkt + b"\xc0")
        self._log(pkt)

    def _read_slip(self):
        """Read and decode one SLIP packet from the ESP32.

        Returns:
            bytearray or None: Decoded packet, or None if no packet is available.
        """
        pkt = None
        # Find the packet start.
        if self.uart.uart.read(1) == b"\xc0":
            pkt = bytearray()
            while True:
                b = self.uart.uart.read(1)
                if b is None or b == b"\xc0":
                    break
                pkt += b
            pkt = pkt.replace(b"\xdb\xdd", b"\xdb").replace(b"\xdb\xdc", b"\xc0")
            self._log(b"\xc0" + pkt + b"\xc0", False)
        return pkt

    def _strerror(self, err):
        """Return a human-readable ESP32 error message.

        Args:
            err (int): ESP32 error code.

        Returns:
            str: Error description.
        """
        if err in _ESP_ERRORS:
            return _ESP_ERRORS[err]
        return "Unknown error"

    def _checksum(self, data):
        """Calculate the ESP32 packet checksum.

        Args:
            data (bytes): Packet data.

        Returns:
            int: Calculated checksum.
        """
        checksum = 0xEF
        for i in data:
            checksum ^= i
        return checksum

    def _command(self, cmd, payload=b"", checksum=0):
        """Send a command and return its response.

        Args:
            cmd (int): ESP32 ROM bootloader command.
            payload (bytes): Command payload. Defaults to b"".
            checksum (int): Payload checksum. Defaults to 0.

        Returns:
            tuple: Response value and response data.
        """
        self._write_slip(struct.pack(b"<BBHI", 0, cmd, len(payload), checksum) + payload)
        for i in range(10):
            pkt = self._read_slip()
            if pkt is not None and len(pkt) >= 8:
                (flag, _cmd, size, val) = struct.unpack("<BBHI", pkt[:8])
                if flag == 1 and cmd == _cmd:
                    status = list(pkt[-4:])
                    if status[0] == 1:
                        raise Exception(f"Command {cmd} failed {self._strerror(status[1])}")
                    return val, pkt[8:]
        raise Exception(f"Failed to read response to command {cmd}.")

    def set_baudrate(self, baudrate, timeout=350):
        """Set the ESP32 and UART communication baud rate.

        Args:
            baudrate (int): New baud rate.
            timeout (int): Unused compatibility argument. Defaults to 350.
        """
        if not hasattr(self.uart.uart, "init"):
            return
        if baudrate != self.baudrate:
            print(f"Changing baudrate => {baudrate}")
            self._uart_drain()
            self._command(_CMD_CHANGE_BAUDRATE, struct.pack("<II", baudrate, 0))
            self.baudrate = baudrate
        self.uart.uart.init(baudrate)
        self._uart_drain()

    def bootloader(self, retry=6):
        """Enter the ESP32 ROM bootloader download mode.

        Args:
            retry (int): Number of reset attempts. Defaults to 6.

        Returns:
            bool: True after synchronization succeeds.
        """
        for i in range(retry):
            self.gpio0_pin(1)
            self.reset_pin(0)
            sleep(0.1)
            self.gpio0_pin(0)
            self.reset_pin(1)
            sleep(0.1)
            self.gpio0_pin(1)

            if "POWERON_RESET" not in self.uart.uart.read():
                continue

            for i in range(10):
                self._uart_drain()
                try:
                    # 36 bytes: 0x07 0x07 0x12 0x20, followed by 32 x 0x55
                    self._command(_CMD_SYNC, b"\x07\x07\x12\x20" + 32 * b"\x55")
                    self._uart_drain()
                    return True
                except Exception as e:
                    print(e)

        raise Exception("Failed to enter download mode!")

    def flash_read_size(self):
        """Read and return the connected ESP32 flash size.

        Returns:
            int: Flash size in bytes.
        """
        SPI_REG_CMD = 0x00
        SPI_USR_FLAG = 1 << 18
        SPI_REG_USR = 0x1C
        SPI_REG_USR2 = 0x24
        SPI_REG_W0 = 0x80
        SPI_REG_DLEN = 0x2C

        # Command bit len | command
        SPI_RDID_CMD = ((8 - 1) << 28) | 0x9F
        SPI_RDID_LEN = 24 - 1

        # Save USR and USR2 registers
        reg_usr = self._read_reg(SPI_REG_USR)
        reg_usr2 = self._read_reg(SPI_REG_USR2)

        # Enable command phase and read phase.
        self._write_reg(SPI_REG_USR, (1 << 31) | (1 << 28))

        # Configure command.
        self._write_reg(SPI_REG_DLEN, SPI_RDID_LEN)
        self._write_reg(SPI_REG_USR2, SPI_RDID_CMD)

        self._write_reg(SPI_REG_W0, 0)
        # Trigger SPI operation.
        self._write_reg(SPI_REG_CMD, SPI_USR_FLAG)

        # Poll CMD_USER flag.
        self._poll_reg(SPI_REG_CMD, SPI_USR_FLAG)

        # Restore USR and USR2 registers
        self._write_reg(SPI_REG_USR, reg_usr)
        self._write_reg(SPI_REG_USR2, reg_usr2)

        flash_bits = int(self._read_reg(SPI_REG_W0)) >> 16
        if flash_bits < 0x12 or flash_bits > 0x19:
            raise Exception(f"Unexpected flash size bits: 0x{flash_bits:02X}.")

        flash_size = 2**flash_bits
        print(f"Flash size {flash_size / 1024 / 1024} MBytes")
        return flash_size

    def flash_attach(self):
        """Attach the ESP32 SPI flash chip."""
        self._command(_CMD_SPI_ATTACH, struct.pack("<II", 0, 0))
        print("Flash attached")

    def flash_config(self, flash_size=2 * 1024 * 1024):
        """Configure the ESP32 flash geometry.

        Args:
            flash_size (int): Flash size in bytes. Defaults to 2 * 1024 * 1024.
        """
        self._command(
            _CMD_SPI_FLASH_PARAMS,
            struct.pack(
                "<IIIIII",
                _FLASH_ID,
                flash_size,
                _FLASH_BLOCK_SIZE,
                _FLASH_SECTOR_SIZE,
                _FLASH_PAGE_SIZE,
                0xFFFF,
            ),
        )

    def flash_write_file(self, path, blksize=0x1000):
        """Write a firmware file to the ESP32 flash chip.

        Args:
            path (str): Path to the firmware image.
            blksize (int): Number of bytes in each transfer block. Defaults to 0x1000.
        """
        size = os.stat(path)[6]
        total_blocks = (size + blksize - 1) // blksize
        erase_blocks = 1
        print(f"Flash write size: {size} total_blocks: {total_blocks} block size: {blksize}")
        with open(path, "rb") as f:
            seq = 0
            for i in range(total_blocks):
                buf = f.read(blksize)
                # Update digest
                if self.md5sum is not None:
                    self.md5sum.update(buf)
                # The last data block should be padded to the block size with 0xFF bytes.
                if len(buf) < blksize:
                    buf += b"\xff" * (blksize - len(buf))
                checksum = self._checksum(buf)
                if seq % erase_blocks == 0:
                    # print(f"Erasing {seq} -> {seq+erase_blocks}...")
                    self._command(
                        _CMD_SPI_FLASH_BEGIN,
                        struct.pack(
                            "<IIII", erase_blocks * blksize, erase_blocks, blksize, seq * blksize
                        ),
                    )
                print(f"Writing sequence number {seq}/{total_blocks}...")
                self._command(
                    _CMD_SPI_FLASH_DATA,
                    struct.pack("<IIII", len(buf), seq % erase_blocks, 0, 0) + buf,
                    checksum,
                )
                seq += 1

        print("Flash write finished")

    def flash_verify_file(self, path, digest=None, offset=0):
        """Verify a firmware file against the ESP32 flash contents.

        Args:
            path (str): Path to the firmware image.
            digest (bytes or None): Expected hexadecimal MD5 digest. Defaults to None.
            offset (int): Flash offset to verify. Defaults to 0.
        """
        if digest is None:
            if self.md5sum is None:
                raise Exception("MD5 checksum missing.")
            digest = binascii.hexlify(self.md5sum.digest())

        size = os.stat(path)[6]
        val, data = self._command(_CMD_SPI_FLASH_MD5, struct.pack("<IIII", offset, size, 0, 0))

        print(f"Flash verify: File  MD5 {digest}")
        print(f"Flash verify: Flash MD5 {bytes(data[0:32])}")

        if digest == data[0:32]:
            print("Firmware verified.")
        else:
            raise Exception("Firmware verification failed.")

    def reboot(self):
        """Reboot the ESP32 after flashing."""
        payload = struct.pack("<I", 0)
        self._write_slip(struct.pack(b"<BBHI", 0, _CMD_SPI_FLASH_END, len(payload), 0) + payload)