class AutoComplete:
    def __init__(self):
        self._words = []
        self._suggestions = ()

    @property
    def context(self):
        return (self._suggestions, len(self._suggestions))

    def add_word(self, word):
        word = str(word)
        if not word:
            return False
        if word not in self._words:
            self._words.append(word)
        return True

    def add_words(self, words):
        for word in words:
            self.add_word(word)
        return True

    def add_dictionary(self, path):
        try:
            import sd_mp

            data = sd_mp.read(path)
            try:
                text = data.decode()
            except AttributeError:
                text = str(data, "utf-8")
            for word in text.replace(",", " ").split():
                self.add_word(word.strip())
            return True
        except Exception:
            return False

    def remove_words(self):
        self._words = []
        self._suggestions = ()
        return True

    def remove_suggestions(self):
        self._suggestions = ()
        return True

    def search(self, prefix):
        prefix = str(prefix).lower()
        out = []
        for word in self._words:
            if str(word).lower().startswith(prefix):
                out.append(word)
                if len(out) >= 3:
                    break
        self._suggestions = tuple(out)
        return self._suggestions
