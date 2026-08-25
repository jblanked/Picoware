"""Session class for Agents"""
class Session:
    """Class for managing an agent session, including conversation history and session ID.
    
    Attributes:
        conversation (list): The conversation history for the session.
        id (str): The unique session ID.
        path (str): The storage path for the session JSON file.
    """
    __slots__ = ("conversation", "_id", "_storage", "_time_created")
    def __init__(self, view_manager, session_id: str = None):
        """Initializes a new session with the given storage backend and optional session ID.
        
        Args:
            view_manager: An instance of the view manager containing the storage backend for saving and loading session data.
            session_id (str, optional): The unique identifier for the session. If not provided, a new session ID will be generated.

        Raises:
            Exception: If the session cannot be loaded from storage with the provided session ID.
        """
        self._storage = view_manager.storage
        self._id = None
        self.conversation = []
        self._time_created = None
        if session_id:
            if not self._load_session(session_id):
                raise Exception("Failed to load session with ID %s" % session_id)
        else:
            self._id = f"session_{id(self)}"
            self._time_created = view_manager.time.datetime
            

    @property
    def id(self) -> str:
        """Returns the unique session ID."""
        return self._id

    @property
    def path(self) -> str:
        """Returns the storage path for the session JSON file."""
        return "picoware/agent/sessions/%s.json" % self._id

    def __del__(self):
        """Cleans up the session before it is destroyed."""
        self._storage = None
        self._id = None
        self.conversation = None

    def _load_session(self, session_id: str) -> bool:
        """Loads a session from the storage backend using the provided session ID."""
        _data: dict = self._storage.serialize("picoware/agent/sessions/%s.json" % session_id)
        if not _data:
            return False
        self._id = _data.get("id")
        self.conversation = _data.get("conversation", [])
        return True
    
    def _save(self) -> bool:
        """Saves the current session to the storage backend."""
        return self._storage.deserialize({
            "id": self._id,
            "conversation": self.conversation,
        }, self.path)

    def append(self, message: dict) -> bool:
        """Appends a message to the session's conversation history and saves it to the storage backend."""
        self.conversation.append(message)
        return self._save()

    def list(self) -> list:
        """Returns a list of all session IDs stored in the storage backend."""
        session_path = "picoware/agent/sessions/"
        sessions = []
        for entry in self._storage.listdir(session_path):
            name = entry.rsplit("/", 1)[-1]
            if name.endswith(".json"):
                sessions.append(name[:-5])
        return sessions

    def update(self, conversation: list) -> bool:
        """Updates the session's conversation history and saves it to the storage backend."""
        self.conversation = conversation
        return self._save()
        