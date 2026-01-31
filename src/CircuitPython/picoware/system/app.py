class App:
    """Class for a Picoware application."""

    def __init__(self, manifest: dict):
        self._authors: list[str] = manifest.get("authors", [])
        self._description: str = manifest.get("description", "")
        self._download_url: str = manifest.get("download_url", "")
        self._file_downloads: list[dict] = manifest.get("file_downloads", [])
        self._file_structure: list[str] = manifest.get("file_structure", [])
        self._github_url: str = manifest.get("github_url", "")
        self._icon_url: str = manifest.get("icon_url", "")
        self._id: int = manifest.get("id", -1)
        self._title: str = manifest.get("title", "Untitled App")
        self._version: str = manifest.get("version", "1.0.0")

        if self._icon_url == "null":
            self._icon_url = ""

    def __del__(self) -> None:
        """Cleanup resources when the App instance is deleted."""
        self._authors = None
        self._description = None
        self._download_url = None
        self._file_downloads = None
        self._file_structure = None
        self._github_url = None
        self._icon_url = None
        self._id = None
        self._title = None
        self._version = None

    def __str__(self) -> str:
        """Return a string representation of the application."""
        return f"App(id={self._id}, title='{self._title}', version='{self._version}')"

    @property
    def authors(self) -> list[str]:
        """Return the authors of the application."""
        return self._authors

    @property
    def description(self) -> str:
        """Return the description of the application."""
        return self._description

    @property
    def download_url(self) -> str:
        """Return the download URL of the application."""
        return self._download_url

    @property
    def file_downloads(self) -> list[dict]:
        """
        Return the list of file downloads for the application.

        Each file download is represented as a dictionary with keys:
        - "path": The path of the file within the application. (str)
        - "download_url": The URL to download the file. (str)
        - "file_id": The unique ID of the file. (int)
        - "file_size": The size of the file in bytes. (int)
        """
        return self._file_downloads

    @property
    def file_structure(self) -> list[str]:
        """Return the file structure of the application."""
        return self._file_structure

    @property
    def github_url(self) -> str:
        """Return the GitHub URL of the application."""
        return self._github_url

    @property
    def icon_url(self) -> str:
        """Return the icon URL of the application."""
        return self._icon_url

    @property
    def id(self) -> int:
        """Return the ID of the application."""
        return self._id

    @property
    def json(self) -> dict:
        """Return a dictionary/JSON representation of the application."""
        return {
            "id": self._id,
            "title": self._title,
            "version": self._version,
            "authors": self._authors,
            "description": self._description,
            "download_url": self._download_url,
            "file_downloads": self._file_downloads,
            "file_structure": self._file_structure,
            "github_url": self._github_url,
            "icon_url": self._icon_url,
        }

    @property
    def title(self) -> str:
        """Return the title of the application."""
        return self._title

    @property
    def version(self) -> str:
        """Return the version of the application."""
        return self._version
