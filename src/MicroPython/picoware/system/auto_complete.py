import auto_complete as ac


class AutoComplete:
    """A simple auto-complete class"""

    def __init__(self) -> None:
        self._ac = ac.AutoComplete()

    def __del__(self) -> None:
        del self._ac
        self._ac = None

    def __str__(self) -> str:
        return str(self._ac)

    @property
    def context(self) -> tuple:
        """Get the underlying auto-complete context."""
        return self._ac.context

    @property
    def suggestion_count(self) -> int:
        """Get the number of current search suggestions."""
        return self._ac.context[1]

    @property
    def suggestions(self) -> tuple:
        """Get the current search suggestions."""
        return self._ac.context[0]

    def add_word(self, word: str) -> bool:
        """Add a word to the auto-complete dictionary."""
        return ac.add_word(self._ac, word)

    def add_words(self, words: list[str]) -> int:
        """Add multiple words to the auto-complete dictionary."""
        count = 0
        for word in words:
            if ac.add_word(self._ac, word):
                count += 1
        return count

    def remove_suggestions(self) -> None:
        """Remove all search suggestions."""
        ac.remove_suggestions(self._ac)

    def remove_words(self) -> None:
        """Remove all words from the auto-complete dictionary."""
        ac.remove_words(self._ac)

    def search(self, prefix: str) -> tuple:
        """Search for words that match the given prefix."""
        results = ac.search(self._ac, prefix)
        if not results:
            return ()
        return results
