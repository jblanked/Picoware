#!/usr/bin/env python3
"""Picoware — USB Video Viewer with a customtkinter UI.

Usage:
    python app.py
"""

import customtkinter as ctk

from views.home import HomeView


class PicowareApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Picoware")
        self.geometry("740x620")
        self.minsize(400, 400)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.home_view = HomeView(self)
        self.home_view.pack(fill="both", expand=True)

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

