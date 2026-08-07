"""
UTF-8 streaming decoder and display character conversion.
"""


class UTF8StreamDecoder:
    def __init__(self):
        self.pending = b""

    def feed(self, data):
        if isinstance(data, str):
            return data

        data = self.pending + bytes(data)
        self.pending = b""

        if not data:
            return ""

        cut = len(data)
        start = max(0, len(data) - 3)

        for index in range(len(data) - 1, start - 1, -1):
            byte = data[index]

            if byte < 0x80:
                break

            if 0xC2 <= byte <= 0xF4:
                required = 2 if byte <= 0xDF else 3 if byte <= 0xEF else 4
                available = len(data) - index

                if available < required:
                    cut = index
                    self.pending = data[index:]

                break

            if not (0x80 <= byte <= 0xBF):
                break

        complete = data[:cut]

        try:
            return complete.decode("utf-8")
        except UnicodeError:
            return complete.decode("utf-8", "replace")

    def finish(self):
        if not self.pending:
            return ""

        data = self.pending
        self.pending = b""

        try:
            return data.decode("utf-8")
        except UnicodeError:
            return data.decode("utf-8", "replace")


_ASCII_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
    "ß": "ss",
    "ă": "a", "Ă": "A", "â": "a", "Â": "A",
    "î": "i", "Î": "I", "ș": "s", "Ș": "S",
    "ş": "s", "Ş": "S", "ț": "t", "Ț": "T",
    "ţ": "t", "Ţ": "T",
    "à": "a", "á": "a", "ã": "a", "å": "a",
    "À": "A", "Á": "A", "Ã": "A", "Å": "A",
    "ç": "c", "Ç": "C",
    "è": "e", "é": "e", "ê": "e", "ë": "e",
    "È": "E", "É": "E", "Ê": "E", "Ë": "E",
    "ì": "i", "í": "i", "ï": "i",
    "Ì": "I", "Í": "I", "Ï": "I",
    "ñ": "n", "Ñ": "N",
    "ò": "o", "ó": "o", "ô": "o", "õ": "o",
    "Ò": "O", "Ó": "O", "Ô": "O", "Õ": "O",
    "ù": "u", "ú": "u", "û": "u",
    "Ù": "U", "Ú": "U", "Û": "U",
    "ý": "y", "ÿ": "y", "Ý": "Y",
    "œ": "oe", "Œ": "Oe", "æ": "ae", "Æ": "Ae",
    "č": "c", "Č": "C", "ć": "c", "Ć": "C",
    "ď": "d", "Ď": "D", "ě": "e", "Ě": "E",
    "ğ": "g", "Ğ": "G", "ł": "l", "Ł": "L",
    "ń": "n", "Ń": "N", "ř": "r", "Ř": "R",
    "š": "s", "Š": "S", "ž": "z", "Ž": "Z",
    "ź": "z", "Ź": "Z", "ż": "z", "Ż": "Z",
    "ø": "o", "Ø": "O",
    "\u00a0": " ",
    "–": "-", "—": "-", "−": "-",
    "‘": "'", "’": "'", "‚": ",",
    "“": '"', "”": '"', "„": '"',
    "…": "...", "•": "*",
    "©": "(c)", "®": "(R)", "™": "(TM)",
    "°": " deg", "×": "x", "÷": "/",
    "€": "EUR", "£": "GBP", "¥": "YEN",
}


def display_text(text, mode="ascii"):
    if mode == "native":
        return text

    output = []

    for char in text:
        code = ord(char)

        if code < 128:
            output.append(char)
        elif char in _ASCII_MAP:
            output.append(_ASCII_MAP[char])
        else:
            output.append("?")

    return "".join(output)
