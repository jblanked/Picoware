"""Original palette-indexed pixel art; dots are transparent pixels."""

BANANA = (
    "......s.", ".....sy.", ".....yy.", "....yhy.",
    "...yhys.", ".syhys..", "syyys...", ".sss....",
)

CLOUD = (
    ".........hhhh...........",
    "........hhhhhh..........",
    "....hhhhhhhhhhhh........",
    "...hhhhhhhhhhhhhhhhh....",
    ".hhhhhhhhhhhhhhhhhhhh...",
    "hhhhhhhhhhhhhhhhhhhhhhh.",
    ".ssssssssssssssssssssss.",
    "...sssssssssssssssss....",
)

GORILLA = (
    ".......oooooo.......",
    "......offffffo......",
    ".....offhhhhffo.....",
    ".....ofhmmmmhfo.....",
    ".....ofmommomfo.....",
    ".....ofmmmmmmfo.....",
    "....offmssssmffo....",
    "...offfhmmmmhfffo...",
    "..offffhffffhffffo..",
    ".offffhhffffhhfffoo.",
    "offffhhmmmmmmhhfffo.",
    "offffhmmhhhhmmhfffo.",
    "offffhmmhhhhmmhfffo.",
    "offfohmmhhhhmmhofffo",
    "offfohmmmmmmmmhofffo",
    "ommmoofffffffoommmo",
    "ommmoffffffffommmmo",
    ".ooooffffffffooooo.",
    ".....offooffo.......",
    "....offfoofffo......",
    "...offffooffffo.....",
    "...ommmmoommmmo.....",
    "...ooooo..ooooo.....",
)

# Replace the hanging arm with the torso outline below the raised shoulder.
GORILLA_THROW = (
    ".ommmo.oooooo.......",
    ".ommmooffffffo......",
    ".offfoffhhhhffo.....",
    ".offfofhmmmmhfo.....",
    ".offfofmommomfo.....",
    ".offfofmmmmmmfo.....",
    ".offfofmssssmffo....",
    ".offfffhmmmmhfffo...",
    "..offffhffffhffffo..",
    "...offhhffffhhfffoo.",
) + tuple("....o" + row[5:] for row in GORILLA[10:18]) + GORILLA[18:]

GORILLA_SMALL = (
    "...oooo...", "..ohhhho..", "..hohhoh..", "..hmmmmh..",
    ".ohhmmhho.", "ohhmmmmhho", "ohhmmmmhho", "omohhhhomo",
    ".oohhhhoo.", "...h..h...", "..om..mo..",
)

GORILLA_DEAD = GORILLA_THROW[:3] + (
    ".offfofmomomomfo....",
    ".offfofmmoommfo.....",
    ".offfofmomomomfo....",
) + GORILLA_THROW[6:]

TITLE = {
    "A": (".###.", "##.##", "##.##", "#####", "##.##", "##.##", "##.##"),
    "G": (".####", "##...", "##...", "##.##", "##.##", "##.##", ".####"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "L": ("##...", "##...", "##...", "##...", "##...", "##...", "#####"),
    "O": (".###.", "##.##", "##.##", "##.##", "##.##", "##.##", ".###."),
    "R": ("####.", "##.##", "##.##", "####.", "##.##", "##.##", "##.##"),
    "S": (".####", "##...", "##...", ".###.", "...##", "...##", "####."),
}


def spans(pattern):
    """Compile transparent art to horizontal color runs outside rendering."""
    result = []
    for y, row in enumerate(pattern):
        x = 0
        while x < len(row):
            pixel = row[x]
            end = x + 1
            while end < len(row) and row[end] == pixel:
                end += 1
            if pixel != ".":
                result.append((x, y, end - x, pixel))
            x = end
    return tuple(result)


BANANA_FRAMES = []
_frame = BANANA
for _rotation in range(4):
    BANANA_FRAMES.append(spans(_frame))
    _frame = tuple("".join(row[x] for row in reversed(_frame)) for x in range(8))
BANANA_FRAMES = tuple(BANANA_FRAMES)
CLOUD_ART = spans(CLOUD)
GORILLA_ART = (spans(GORILLA), spans(GORILLA_THROW), spans(GORILLA_SMALL), spans(GORILLA_DEAD))
TITLE_ART = spans(tuple(".".join(TITLE[ch][row] for ch in "GORILLAS") for row in range(7)))
