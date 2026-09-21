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
from time import sleep, ticks_diff, ticks_ms
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
_FLASH_WRITE_SIZE = const(0x400)
_FLASH_MD5_TIMEOUT_PER_MB = const(8000)
_FLASH_SCAN_SIZE = const(16 * 1024)
_FLASH_PROGRESS_INTERVAL = const(64)

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

    def __init__(self, reset, gpio0, uart: UART, log_enabled=False, chip="esp32"):
        """Initialize the ESP32 flasher.

        Args:
            reset (callable): Function used to control the ESP32 reset pin.
            gpio0 (callable): Function used to control the ESP32 GPIO0 pin.
            uart (UART): Picoware UART interface connected to the ESP32.
            log_enabled (bool): Whether to print packet diagnostics. Defaults to False.
            chip (str): ESP ROM target. Defaults to "esp32".
        """
        self.uart = uart
        self.reset_pin = reset
        self.gpio0_pin = gpio0
        self.log = log_enabled
        self.chip = chip.lower()
        self.baudrate = 115200
        self.md5sum = None
        self._pyb = None
        self._repl_uart = None
        self._slip_buffer = bytearray()
        if self.chip == "esp32s2":
            self._flash_reg_base = 0x3F402000
            self._spi_usr = 0x18
            self._spi_usr2 = 0x20
            self._spi_w0 = 0x58
            self._spi_dlen = 0x28
        else:
            self._flash_reg_base = _FLASH_REG_BASE
            self._spi_usr = 0x1C
            self._spi_usr2 = 0x24
            self._spi_w0 = 0x80
            self._spi_dlen = 0x2C
        try:
            import hashlib

            if hasattr(hashlib, "md5"):
                self.md5sum = hashlib.md5()
        except ImportError:
            pass

    def _detach_repl_uart(self):
        """Detach the flasher UART from the MicroPython REPL."""
        try:
            import pyb

            repl_uart = pyb.repl_uart()
        except (ImportError, AttributeError):
            return

        if repl_uart is self.uart.uart:
            pyb.repl_uart(None)
            self._pyb = pyb
            self._repl_uart = repl_uart

    def _restore_repl_uart(self):
        """Restore the MicroPython REPL UART."""
        if self._repl_uart is not None:
            self._pyb.repl_uart(self._repl_uart)
            self._pyb = None
            self._repl_uart = None

    def _clear_uart(self):
        """Clear UART input and buffered SLIP data."""
        self.uart.clear()
        self._slip_buffer = bytearray()

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

    def _read_reg(self, addr):
        """Read a value from an ESP32 flash register.

        Args:
            addr (int): Register offset from the flash register base.

        Returns:
            int: Register value.
        """
        v, d = self._command(_CMD_ESP_READ_REG, struct.pack("<I", self._flash_reg_base + addr))
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
            _CMD_ESP_WRITE_REG,
            struct.pack("<IIII", self._flash_reg_base + addr, data, mask, delay),
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

    def _read_slip(self, timeout_ms=1000):
        """Read and decode one SLIP packet from the ESP32.

        Args:
            timeout_ms (int): Maximum time to wait for a complete packet.

        Returns:
            bytearray or None: Decoded packet, or None if no packet is available.
        """
        start = ticks_ms()
        pkt = None
        while ticks_diff(ticks_ms(), start) < timeout_ms:
            if self._slip_buffer:
                data = self._slip_buffer
                self._slip_buffer = bytearray()
            else:
                available = self.uart.uart.any()
                if available <= 0:
                    sleep(0.001)
                    continue
                data = self.uart.uart.read(available)
            if not data:
                continue

            for index, value in enumerate(data):
                if pkt is None:
                    if value == 0xC0:
                        pkt = bytearray()
                    continue

                if value == 0xC0:
                    if index + 1 < len(data):
                        self._slip_buffer = bytearray(data[index + 1 :])
                    pkt = pkt.replace(b"\xdb\xdd", b"\xdb").replace(b"\xdb\xdc", b"\xc0")
                    self._log(b"\xc0" + pkt + b"\xc0", False)
                    return pkt

                pkt.append(value)

        return None

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

    def _command(self, cmd, payload=b"", checksum=0, timeout_ms=3000):
        """Send a command and return its response.

        Args:
            cmd (int): ESP32 ROM bootloader command.
            payload (bytes): Command payload. Defaults to b"".
            checksum (int): Payload checksum. Defaults to 0.

        Returns:
            tuple: Response value and response data.
        """
        self._write_slip(struct.pack(b"<BBHI", 0, cmd, len(payload), checksum) + payload)
        start = ticks_ms()
        while ticks_diff(ticks_ms(), start) < timeout_ms:
            elapsed = ticks_diff(ticks_ms(), start)
            pkt = self._read_slip(timeout_ms - elapsed)
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
            self._clear_uart()
            self._command(_CMD_CHANGE_BAUDRATE, struct.pack("<II", baudrate, 0))
            self.baudrate = baudrate
        self.uart.uart.init(baudrate)
        self._clear_uart()

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

            for i in range(10):
                self._clear_uart()
                try:
                    # 36 bytes: 0x07 0x07 0x12 0x20, followed by 32 x 0x55
                    self._command(_CMD_SYNC, b"\x07\x07\x12\x20" + 32 * b"\x55")
                    self._clear_uart()
                    return True
                except Exception as e:
                    if self.log:
                        print(e)
                    sleep(0.050)

        raise Exception("Failed to enter download mode!")

    def flash_read_size(self):
        """Read and return the connected ESP32 flash size.

        Returns:
            int: Flash size in bytes.
        """
        SPI_REG_CMD = 0x00
        SPI_USR_FLAG = 1 << 18
        SPI_REG_USR = self._spi_usr
        SPI_REG_USR2 = self._spi_usr2
        SPI_REG_W0 = self._spi_w0
        SPI_REG_DLEN = self._spi_dlen

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

    def flash_write_file(
        self,
        path,
        blksize=_FLASH_WRITE_SIZE,
        progress_interval=_FLASH_PROGRESS_INTERVAL,
    ):
        """Write a firmware file to the ESP32 flash chip.

        Args:
            path (str): Path to the firmware image.
            blksize (int): Number of bytes in each transfer block. Must be 4-byte aligned
                and no larger than the ESP32 ROM limit of 0x400. Defaults to 0x400.
            progress_interval (int): Number of blocks between progress messages. Defaults
                to 64.
        """
        if blksize <= 0 or blksize > _FLASH_WRITE_SIZE or blksize % 4:
            raise ValueError("blksize must be 4-byte aligned and no larger than 0x400.")
        if progress_interval <= 0:
            raise ValueError("progress_interval must be greater than zero.")

        size = os.stat(path)[6]
        erase_size = ((size + _FLASH_SECTOR_SIZE - 1) // _FLASH_SECTOR_SIZE) * _FLASH_SECTOR_SIZE

        last_data = -1
        with open(path, "rb") as f:
            scan_position = size
            while scan_position > 0:
                scan_size = min(_FLASH_SCAN_SIZE, scan_position)
                scan_position -= scan_size
                f.seek(scan_position)
                data = f.read(scan_size)
                for index in range(len(data) - 1, -1, -1):
                    if data[index] != 0xFF:
                        last_data = scan_position + index
                        break
                if last_data >= 0:
                    break

        write_size = max(blksize, last_data + 1)
        total_blocks = (write_size + blksize - 1) // blksize
        print(f"Flash write size: {size} total_blocks: {total_blocks} block size: {blksize}")
        self._detach_repl_uart()
        try:
            with open(path, "rb") as f:
                begin_payload = struct.pack(
                    "<IIII", erase_size, total_blocks, blksize, 0
                )
                if self.chip == "esp32s2":
                    begin_payload += struct.pack("<I", 0)
                self._command(
                    _CMD_SPI_FLASH_BEGIN,
                    begin_payload,
                    timeout_ms=max(10000, (erase_size * 40000) // 1000000),
                )

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
                    if (
                        seq == 0
                        or seq == total_blocks - 1
                        or seq % progress_interval == 0
                    ):
                        print(f"Writing sequence number {seq}/{total_blocks}...")
                    self._command(
                        _CMD_SPI_FLASH_DATA,
                        struct.pack("<IIII", len(buf), seq, 0, 0) + buf,
                        checksum,
                    )
                    seq += 1

                if self.md5sum is not None:
                    while True:
                        buf = f.read(blksize)
                        if not buf:
                            break
                        self.md5sum.update(buf)

            print("Flash write finished")
        finally:
            self._restore_repl_uart()

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
        timeout_ms = max(3000, (size * _FLASH_MD5_TIMEOUT_PER_MB) // 1000000)
        val, data = self._command(
            _CMD_SPI_FLASH_MD5,
            struct.pack("<IIII", offset, size, 0, 0),
            timeout_ms=timeout_ms,
        )

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