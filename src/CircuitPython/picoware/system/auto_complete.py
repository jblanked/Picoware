import auto_complete as ac


class AutoComplete(ac.AutoComplete):
    """A simple auto-complete class"""

    @property
    def suggestion_count(self) -> int:
        """The number of suggestions currently stored."""
        return self.context[1]

    @property
    def suggestions(self) -> tuple:
        """The current suggestions as a tuple."""
        return self.context[0]

    def add_words(self, words: list[str]) -> int:
        """Add multiple words."""
        return sum(1 for word in words if self.add_word(word))
