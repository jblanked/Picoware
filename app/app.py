#!/usr/bin/env python3
"""Picoware — USB Video Viewer with a customtkinter UI.

Usage:
    python app.py
"""

import customtkinter as ctk

from views.code import CodeView
from views.flash import FlashView
from views.home import HomeView
from views.store import StoreView


class PicowareApp(ctk.CTk):
    """Main application window with tabbed navigation."""

    def __init__(self):
        super().__init__()

        self.title("Picoware")
        self.geometry("960x680")
        self.minsize(600, 400)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._tab_view = ctk.CTkTabview(self)
        self._tab_view.pack(fill="both", expand=True, padx=5, pady=5)

        self._tab_view.add("Home")
        self._tab_view.add("Store")
        self._tab_view.add("Code")
        self._tab_view.add("Flash")

        self.home_view = HomeView(self._tab_view.tab("Home"))
        self.home_view.pack(fill="both", expand=True)

        self.store_view = StoreView(self._tab_view.tab("Store"))
        self.store_view.pack(fill="both", expand=True)

        self.code_view = CodeView(self._tab_view.tab("Code"))
        self.code_view.pack(fill="both", expand=True)

        self.flash_view = FlashView(self._tab_view.tab("Flash"))
        self.flash_view.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Clean up serial connection and destroy the window."""
        self.home_view.destroy()
        self.destroy()


def main() -> None:
    """Launch the Picoware application."""
    app = PicowareApp()
    app.mainloop()


if __name__ == "__main__":
    main()

