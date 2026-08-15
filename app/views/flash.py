"""Firmware Flash view — flash a UF2 build to a device in bootloader mode."""

import os
import threading
import time
import tkinter.filedialog as fd
import tkinter.messagebox as mb

import customtkinter as ctk

from views import device

LOG_FONT = ("Courier New", 13)
DRIVE_POLL_SECS = 10


class FlashView(ctk.CTkFrame):
    """Flash a UF2 firmware file to a device in bootloader mode."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._busy = False

        self._build_ui()
        self._detect()

    def _build_ui(self) -> None:
        """Build the header, firmware picker, actions, and log."""
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_firmware_row()
        self._build_device_row()
        self._build_actions()
        self._build_log()
        self._build_instructions()

    def _build_header(self) -> None:
        """Create the title bar with status and detect button."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            header,
            text="Firmware Flash",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="transparent",
        ).grid(row=0, column=0, sticky="w")

        self.drive_label = ctk.CTkLabel(
            header,
            text="No bootloader drive detected",
            fg_color="transparent",
            text_color="gray",
        )
        self.drive_label.grid(row=0, column=1, padx=(10, 5))

        ctk.CTkButton(
            header, text="Detect", command=self._detect, width=70
        ).grid(row=0, column=2)

    def _build_firmware_row(self) -> None:
        """Create the firmware file picker."""
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="Firmware (.uf2):", fg_color="transparent").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.file_var = ctk.StringVar(value="")
        self.file_entry = ctk.CTkEntry(row, textvariable=self.file_var)
        self.file_entry.grid(row=0, column=1, sticky="ew")

        ctk.CTkButton(
            row, text="Browse…", command=self._browse_file, width=80
        ).grid(row=0, column=2, padx=(5, 0))

    def _build_device_row(self) -> None:
        """Create the port selector used to enter bootloader mode."""
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(row, text="Device port:", fg_color="transparent").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.port_var = ctk.StringVar(value="Auto-detect")
        self.port_combo = ctk.CTkComboBox(
            row, values=["Auto-detect"], variable=self.port_var, width=220
        )
        self.port_combo.grid(row=0, column=1)

        ctk.CTkButton(
            row, text="Refresh", command=self._refresh_ports, width=70
        ).grid(row=0, column=2, sticky="w", padx=(5, 0))

        self.port_status = ctk.CTkLabel(
            row, text="", fg_color="transparent", text_color="gray"
        )
        self.port_status.grid(row=0, column=3, sticky="e")

    def _build_actions(self) -> None:
        """Create the bootloader and flash buttons."""
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        self._boot_btn = ctk.CTkButton(
            row, text="Enter Bootloader", command=self._enter_bootloader, width=140
        )
        self._boot_btn.pack(side="left", padx=(0, 10))

        self._flash_btn = ctk.CTkButton(
            row, text="Flash Firmware", command=self._flash, width=140
        )
        self._flash_btn.pack(side="left")

    def _build_log(self) -> None:
        """Create the read-only operation log."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.log = ctk.CTkTextbox(
            frame,
            font=LOG_FONT,
            wrap="word",
            activate_scrollbars=True,
            state="disabled",
        )
        self.log.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _build_instructions(self) -> None:
        """Show a short usage hint at the bottom."""
        ctk.CTkLabel(
            self,
            text=(
                "Hold the BOOT button while plugging in the device to enter "
                "bootloader mode, or use 'Enter Bootloader' on a connected "
                "device. Then pick a .uf2 file and press 'Flash Firmware'."
            ),
            fg_color="transparent",
            text_color="gray",
            wraplength=900,
            justify="left",
        ).grid(row=5, column=0, sticky="w", padx=10, pady=(5, 10))

    def _browse_file(self) -> None:
        """Pick a UF2 firmware file."""
        path = fd.askopenfilename(
            title="Select Firmware",
            filetypes=[("UF2 firmware", "*.uf2"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def _selected_port(self) -> str:
        """Return the selected port, or 'auto' for auto-detect."""
        selected = self.port_var.get()
        return "auto" if selected in ("", "Auto-detect") else selected

    def _refresh_ports(self) -> None:
        """Scan for serial ports and populate the dropdown."""
        ports = ["Auto-detect"] + device.list_ports()
        self.port_combo.configure(values=ports)

    def _append_log(self, text: str) -> None:
        """Append *text* to the operation log."""
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable action buttons while an operation runs."""
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._boot_btn.configure(state=state)
        self._flash_btn.configure(state=state)

    def _detect(self) -> None:
        """Refresh port list and bootloader drive status."""
        self._refresh_ports()
        drive = device.find_bootloader_drive()
        if drive:
            self.drive_label.configure(
                text=f"Bootloader drive: {drive}", text_color="#6A9955"
            )
        else:
            self.drive_label.configure(
                text="No bootloader drive detected", text_color="gray"
            )

    def _enter_bootloader(self) -> None:
        """Put a connected device into bootloader mode via mpremote."""
        if self._busy:
            return
        self._set_busy(True)
        self.port_status.configure(text="Entering bootloader…")
        threading.Thread(
            target=self._enter_bootloader_thread, args=(self._selected_port(),),
            daemon=True,
        ).start()

    def _enter_bootloader_thread(self, port: str) -> None:
        """Background: send bootloader command, then wait for the drive."""
        self.after(0, lambda: self._append_log(f"Entering bootloader ({port})...\n"))
        _, out = device.enter_bootloader(device=port)
        self.after(0, lambda: self._append_log(out))

        drive = self._wait_for_drive(DRIVE_POLL_SECS)
        if drive:
            self.after(0, lambda: self._append_log(f"Bootloader drive: {drive}\n"))
            self.after(0, lambda: self.drive_label.configure(
                text=f"Bootloader drive: {drive}", text_color="#6A9955"))
            self.after(0, lambda: self.port_status.configure(text=""))
        else:
            self.after(0, lambda: self._append_log("Bootloader drive not detected.\n"))
            self.after(0, lambda: self.port_status.configure(text=""))
        self.after(0, lambda: self._set_busy(False))

    def _flash(self) -> None:
        """Flash the selected firmware to the bootloader drive."""
        if self._busy:
            return
        uf2 = self.file_var.get().strip()
        if not uf2 or not os.path.isfile(uf2):
            mb.showerror("Flash", "Choose a valid .uf2 firmware file.")
            return
        self._set_busy(True)
        threading.Thread(target=self._flash_thread, args=(uf2,), daemon=True).start()

    def _flash_thread(self, uf2: str) -> None:
        """Background: copy the firmware to the bootloader drive."""
        drive = device.find_bootloader_drive()
        if not drive:
            self.after(0, lambda: self._append_log(
                "No bootloader drive found. Enter bootloader mode first.\n"))
            self.after(0, lambda: self._set_busy(False))
            return
        name = os.path.basename(uf2)
        self.after(0, lambda: self._append_log(
            f"Flashing {name} to {drive}...\n"))
        ok = device.flash_uf2(uf2, drive)
        if ok:
            self.after(0, lambda: self._append_log("Firmware flashed successfully.\n"))
            self.after(0, lambda: self.drive_label.configure(
                text="No bootloader drive detected", text_color="gray"))
        else:
            self.after(0, lambda: self._append_log("Flash failed.\n"))
        self.after(0, lambda: self._set_busy(False))

    def _wait_for_drive(self, timeout: float) -> str | None:
        """Poll for the bootloader drive to appear, up to *timeout* seconds."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            drive = device.find_bootloader_drive()
            if drive:
                return drive
            time.sleep(0.5)
        return None
