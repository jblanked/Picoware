"""Host storage and audio services for the firmware's native Ghouls game."""

import os
import struct
import sim_runtime

_audio = None
_temporary = []
_sequence = 0


def _matches(pattern, name):
    """Match the firmware's case-insensitive * and ? filename wildcards."""
    pattern, name = pattern.lower(), name.lower()
    p = n = 0
    star = -1
    retry = 0
    while n < len(name):
        if p < len(pattern) and pattern[p] in ("?", name[n]):
            p += 1
            n += 1
        elif p < len(pattern) and pattern[p] == "*":
            star, retry = p, n
            p += 1
        elif star >= 0:
            retry += 1
            p, n = star + 1, retry
        else:
            return False
    return all(char == "*" for char in pattern[p:])


def _player():
    global _audio
    if _audio is None:
        from audio import Audio

        _audio = Audio()
    return _audio


def _wave(data, channels, rate):
    """Play generated PCM through the same WAV backend as firmware assets."""
    global _sequence
    if sim_runtime.audio_mode != "real":
        return True
    _sequence += 1
    path = "sim_reports/ghouls-audio-{}-{}.wav".format(id(_temporary), _sequence)
    target = sim_runtime.host_path(path)
    sim_runtime.mkdir_p(target.rsplit("/", 1)[0])
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(data),
                         b"WAVE", b"fmt ", 16, 1, channels, rate,
                         rate * channels * 2, channels * 2, 16, b"data", len(data))
    with open(target, "wb") as handle:
        handle.write(header)
        handle.write(data)
    _temporary.append(target)
    return play_wav(path)


def list_files(pattern, skip=0, maximum=65535):
    import sd_mp

    directory, mask = pattern.rsplit("/", 1) if "/" in pattern else ("", pattern)
    names = []
    for entry in sd_mp.read_directory(directory):
        name = entry["filename"]
        if not name.startswith(".") and not entry["is_directory"] and _matches(mask or "*", name):
            names.append(name)
    return sorted(names)[skip:skip + maximum]


def play_pcm(data):
    return _wave(data, 2, 44100)


def play_tone(left, right, duration):
    import math

    if sim_runtime.audio_mode != "real":
        return True
    rate = 22050
    frames = max(0, int(duration)) * rate // 1000
    data = bytearray(frames * 4)
    for frame in range(frames):
        for channel, frequency in enumerate((left, right)):
            sample = int(8191 * math.sin(2 * math.pi * frequency * frame / rate)) if frequency > 0 else 0
            struct.pack_into("<h", data, frame * 4 + channel * 2, sample)
    return _wave(data, 2, rate)


def play_wav(path):
    return _player().play_wav(path)


def stop():
    if _audio is not None:
        _audio.stop()
    for path in _temporary:
        try:
            os.remove(path)
        except OSError:
            pass
    _temporary[:] = []
