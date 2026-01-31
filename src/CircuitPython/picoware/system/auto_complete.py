import auto_complete


class AutoComplete:
    """A simple auto-complete class"""

    def __init__(self) -> None:
        self._ac = auto_complete.AutoComplete()

    def __del__(self) -> None:
        auto_complete.free(self._ac)

    def __str__(self) -> str:
        return str(self._ac)

    @property
    def context(self) -> auto_complete.AutoComplete:
        """Get the underlying auto-complete context."""
        return self._ac

    def add_word(self, word: str) -> bool:
        """Add a word to the auto-complete dictionary."""
        return auto_complete.add_word(self._ac, word)

    def add_words(self, words: list[str]) -> int:
        """Add multiple words to the auto-complete dictionary."""
        count = 0
        for word in words:
            if auto_complete.add_word(self._ac, word):
                count += 1
        return count

    def remove_suggestions(self) -> None:
        """Remove all search suggestions."""
        auto_complete.remove_suggestions(self._ac)

    def remove_words(self) -> None:
        """Remove all words from the auto-complete dictionary."""
        auto_complete.remove_words(self._ac)

    def search(self, prefix: str) -> tuple:
        """Search for words that match the given prefix."""
        results = auto_complete.search(self._ac, prefix)
        if not results:
            return ()
        return results
