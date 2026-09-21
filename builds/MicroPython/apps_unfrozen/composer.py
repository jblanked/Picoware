from picoware.system.vector import Vector
from picoware.system.colors import (
    TFT_BLACK, TFT_DARKGREY, TFT_LIGHTGREY,
    TFT_YELLOW, TFT_ORANGE, TFT_BLUE
)
from picoware.system.buttons import (
    BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_CENTER, BUTTON_BACK, BUTTON_OK,
    BUTTON_A, BUTTON_B, BUTTON_N, BUTTON_T, BUTTON_G, BUTTON_H
)

try:
    from picoware.system.audio import AudioNote
    AUDIO_OK = True
except Exception:
    AUDIO_OK = False

PITCHES = [
    ("C2", 65), ("C#2", 69), ("D2", 73), ("D#2", 78),
    ("E2", 82), ("F2", 87), ("F#2", 93), ("G2", 98),
    ("G#2", 104), ("A2", 110), ("A#2", 117), ("B2", 123),
    ("C3", 131), ("C#3", 139), ("D3", 147), ("D#3", 156),
    ("E3", 165), ("F3", 175), ("F#3", 185), ("G3", 196),
    ("G#3", 208), ("A3", 220), ("A#3", 233), ("B3", 247),
    ("C4", 262), ("C#4", 277), ("D4", 294), ("D#4", 311),
    ("E4", 330), ("F4", 349), ("F#4", 370), ("G4", 392),
    ("G#4", 415), ("A4", 440), ("A#4", 466), ("B4", 494),
    ("C5", 523), ("C#5", 554), ("D5", 587), ("D#5", 622),
    ("E5", 659), ("F5", 698), ("F#5", 740), ("G5", 784),
    ("G#5", 831), ("A5", 880), ("A#5", 932), ("B5", 988),
    ("C6", 1047), ("C#6", 1109), ("D6", 1175), ("D#6", 1245),
    ("E6", 1319), ("F6", 1397), ("F#6", 1480), ("G6", 1568),
    ("G#6", 1661), ("A6", 1760), ("A#6", 1865), ("B6", 1976),
    ("C7", 2093),
    ("Rest", 0),
]

NUM_TRACKS = 3
TRACK_NAMES = ["Melody", "Bass", "Drums"]

COL_BG = TFT_BLACK
COL_TEXT = TFT_LIGHTGREY
COL_ACCENT = TFT_ORANGE
COL_CURSOR = TFT_BLUE
COL_NOTE = TFT_DARKGREY
COL_PLAY = TFT_YELLOW
COL_EMPTY = 0x4208

_pattern = None
_current_track = 0
_cursor = 0
_state = "grid"
_pitch_index = 24
_bpm = 120
_num_steps = 16
_swing = 0
_is_playing = False
_play_step = 0


def start(view_manager) -> bool:
    global _pattern, _current_track, _cursor, _state
    global _pitch_index, _bpm, _num_steps, _swing, _is_playing, _play_step

    _current_track = 0
    _cursor = 0
    _state = "grid"
    _pitch_index = 24
    _bpm = 120
    _num_steps = 16
    _swing = 0
    _is_playing = False
    _play_step = 0
    _pattern = [[None for _ in range(32)] for _ in range(NUM_TRACKS)]

    if AUDIO_OK:
        view_manager.audio.set_volume(75)

    _draw(view_manager)
    return True


def _base_duration():
    return max(40, int(60000 / _bpm / 4))


def _step_duration(step):
    base = _base_duration()
    if _swing > 0 and (step % 2 == 1):
        extra = int(base * _swing / 100)
        return base + extra
    return base


def _draw(view_manager):
    draw = view_manager.draw
    draw.erase()

    status = f"PLAY {_play_step+1}" if _is_playing else f"BPM:{_bpm}"
    draw.text(Vector(4, 1), "Step Sequencer", COL_ACCENT, 1)
    draw.text(Vector(4, 13),
              f"{TRACK_NAMES[_current_track]} {status} Sw:{_swing}%",
              COL_TEXT, 1)

    if _num_steps <= 8:
        rows, cols, cell_w, cell_h = 1, 8, 30, 20
    elif _num_steps <= 16:
        rows, cols, cell_w, cell_h = 2, 8, 28, 17
    else:
        rows, cols, cell_w, cell_h = 4, 8, 26, 14

    start_x = 6
    start_y = 28

    for row in range(rows):
        for col in range(cols):
            step = row * cols + col
            if step >= _num_steps:
                break

            x = start_x + col * (cell_w + 2)
            y = start_y + row * (cell_h + 3)

            has_note = _pattern[_current_track][step] is not None

            if _is_playing and step == _play_step:
                draw.fill_rectangle(Vector(x-1, y-1), Vector(cell_w+2, cell_h+2), COL_PLAY)
            elif step == _cursor:
                draw.fill_rectangle(Vector(x-1, y-1), Vector(cell_w+2, cell_h+2), COL_CURSOR)

            if has_note:
                draw.fill_rectangle(Vector(x, y), Vector(cell_w, cell_h), COL_NOTE)
            else:
                draw.rect(Vector(x, y), Vector(cell_w, cell_h), COL_EMPTY)

            if cell_h >= 16:
                draw.text(Vector(x + 6, y + 2), str(step + 1), COL_TEXT, 1)

    y = start_y + rows * (cell_h + 3) + 4
    draw.text(Vector(4, y), f"Steps:{_num_steps}  L/R Cursor  U/D Track", COL_TEXT, 1)
    y += 12
    draw.text(Vector(4, y), "A=Play  B/N=BPM  T=Steps  G/H=Swing", COL_ACCENT, 1)
    draw.swap()


def _play_one_step(view_manager):
    global _play_step, _is_playing

    if not _is_playing:
        return

    freq = _pattern[_current_track][_play_step]
    duration = _step_duration(_play_step)

    try:
        if freq and freq > 0:
            note = AudioNote(int(freq), int(freq), duration)
        else:
            note = AudioNote(0, 0, duration)
        view_manager.audio.play_note(note)
    except Exception:
        pass

    _play_step += 1
    if _play_step >= _num_steps:
        _is_playing = False
        _play_step = 0


def run(view_manager) -> None:
    global _current_track, _cursor, _state, _pitch_index
    global _bpm, _num_steps, _swing, _is_playing, _play_step

    button = view_manager.button

    if _is_playing:
        _play_one_step(view_manager)
        _draw(view_manager)
        return

    if _state == "grid":
        _draw(view_manager)

        if button == BUTTON_LEFT:
            _cursor = (_cursor - 1) % _num_steps
        elif button == BUTTON_RIGHT:
            _cursor = (_cursor + 1) % _num_steps
        elif button == BUTTON_UP:
            _current_track = (_current_track - 1) % NUM_TRACKS
        elif button == BUTTON_DOWN:
            _current_track = (_current_track + 1) % NUM_TRACKS
        elif button == BUTTON_CENTER or button == BUTTON_OK:
            if _pattern[_current_track][_cursor] is not None:
                _pattern[_current_track][_cursor] = None
            else:
                _state = "pick_pitch"
        elif button == BUTTON_A:
            if _is_playing:
                _is_playing = False
                _play_step = 0
                try:
                    view_manager.audio.stop()
                except:
                    pass
            else:
                _is_playing = True
                _play_step = 0
        elif button == BUTTON_B:
            _bpm = max(40, _bpm - 5)
        elif button == BUTTON_N:
            _bpm = min(280, _bpm + 5)
        elif button == BUTTON_T:
            if _num_steps == 8:
                _num_steps = 16
            elif _num_steps == 16:
                _num_steps = 32
            else:
                _num_steps = 8
            _cursor = _cursor % _num_steps
        elif button == BUTTON_G:
            _swing = max(0, _swing - 5)
        elif button == BUTTON_H:
            _swing = min(50, _swing + 5)
        elif button == BUTTON_BACK:
            _is_playing = False
            try:
                view_manager.audio.stop()
            except Exception:
                pass
            view_manager.back()

    elif _state == "pick_pitch":
        draw = view_manager.draw
        draw.erase()
        draw.text(Vector(8, 6), "Select Pitch", COL_ACCENT, 1)
        draw.text(Vector(8, 22), f"{TRACK_NAMES[_current_track]}  Step {_cursor+1}", COL_TEXT, 1)

        y = 42
        start = max(0, _pitch_index - 4)
        end = min(len(PITCHES), start + 10)
        for i in range(start, end):
            name = PITCHES[i][0]
            color = COL_ACCENT if i == _pitch_index else COL_TEXT
            prefix = ">" if i == _pitch_index else " "
            draw.text(Vector(16, y), f"{prefix} {name}", color, 1)
            y += 13

        draw.text(Vector(8, 175), "U/D Move   OK Place   Back Cancel", COL_TEXT, 1)
        draw.swap()

        if button == BUTTON_UP:
            _pitch_index = max(0, _pitch_index - 1)
        elif button == BUTTON_DOWN:
            _pitch_index = min(len(PITCHES) - 1, _pitch_index + 1)
        elif button == BUTTON_CENTER:
            name, freq = PITCHES[_pitch_index]
            if name == "Rest" or freq == 0:
                _pattern[_current_track][_cursor] = None
            else:
                _pattern[_current_track][_cursor] = freq
            _state = "grid"
        elif button == BUTTON_BACK:
            _state = "grid"


def stop(view_manager) -> None:
    global _pattern, _is_playing
    _is_playing = False
    if view_manager.audio:
        view_manager.audio.stop()
    _pattern = None