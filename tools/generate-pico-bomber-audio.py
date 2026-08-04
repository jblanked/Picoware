#!/usr/bin/env python3
"""Generate Pico Bomber's original low-memory chiptune WAV pack."""

from array import array
from math import pi, sin
from pathlib import Path
from random import Random
import wave


SAMPLE_RATE = 11025
OUTPUT = Path(
    "builds/MicroPython/apps_unfrozen/games/pico_bomber/audio"
)
RNG = Random(0xB04B)

NOTES = {
    "C2": 65.41, "Cs2": 69.30, "D2": 73.42, "Eb2": 77.78,
    "E2": 82.41, "F2": 87.31, "Fs2": 92.50, "G2": 98.00,
    "Gs2": 103.83, "Ab2": 103.83, "A2": 110.00, "Bb2": 116.54,
    "B2": 123.47, "C3": 130.81, "Cs3": 138.59, "D3": 146.83,
    "Eb3": 155.56, "E3": 164.81, "F3": 174.61, "Fs3": 185.00,
    "G3": 196.00, "Gs3": 207.65, "Ab3": 207.65, "A3": 220.00,
    "Bb3": 233.08, "B3": 246.94, "C4": 261.63, "Cs4": 277.18,
    "D4": 293.66, "Eb4": 311.13, "E4": 329.63, "F4": 349.23,
    "Fs4": 369.99, "G4": 392.00, "Gs4": 415.30, "Ab4": 415.30,
    "A4": 440.00, "Bb4": 466.16, "B4": 493.88, "C5": 523.25,
    "Cs5": 554.37, "D5": 587.33, "Eb5": 622.25, "E5": 659.25,
    "F5": 698.46, "Fs5": 739.99, "G5": 783.99, "Gs5": 830.61,
    "Ab5": 830.61, "A5": 880.00, "Bb5": 932.33, "B5": 987.77,
    "C6": 1046.50, "Cs6": 1108.73, "D6": 1174.66,
}


def _blank(seconds):
    return array("f", [0.0]) * int(seconds * SAMPLE_RATE)


def _env(position, length, attack=0.04, release=0.18):
    if length <= 1:
        return 0.0
    fraction = position / length
    if fraction < attack:
        return fraction / attack
    if fraction > 1.0 - release:
        return max(0.0, (1.0 - fraction) / release)
    return 1.0


def _wave(kind, phase, duty=0.5):
    phase -= int(phase)
    if kind == "triangle":
        return 1.0 - 4.0 * abs(phase - 0.5)
    if kind == "saw":
        return phase * 2.0 - 1.0
    return 1.0 if phase < duty else -1.0


def add_tone(
    target,
    start,
    duration,
    frequency,
    volume,
    kind="square",
    duty=0.5,
    slide=0.0,
    vibrato=0.0,
):
    first = int(start * SAMPLE_RATE)
    count = max(1, int(duration * SAMPLE_RATE))
    last = min(len(target), first + count)
    phase = 0.0
    for index in range(first, last):
        local = index - first
        progress = local / count
        hz = frequency + slide * progress
        if vibrato:
            hz *= 1.0 + sin(progress * pi * 10.0) * vibrato
        phase += hz / SAMPLE_RATE
        target[index] += (
            _wave(kind, phase, duty)
            * volume
            * _env(local, count)
        )


def add_noise(target, start, duration, volume, decay=True):
    first = int(start * SAMPLE_RATE)
    count = max(1, int(duration * SAMPLE_RATE))
    last = min(len(target), first + count)
    previous = 0.0
    for index in range(first, last):
        progress = (index - first) / count
        raw = RNG.random() * 2.0 - 1.0
        previous = previous * 0.35 + raw * 0.65
        level = (1.0 - progress) if decay else _env(index - first, count)
        target[index] += previous * volume * level


def add_kick(target, start, volume=0.32):
    first = int(start * SAMPLE_RATE)
    count = int(0.12 * SAMPLE_RATE)
    phase = 0.0
    for local in range(count):
        index = first + local
        if index >= len(target):
            break
        progress = local / count
        phase += (120.0 - 75.0 * progress) / SAMPLE_RATE
        target[index] += sin(phase * 2.0 * pi) * volume * (1.0 - progress)


def write_wav(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = bytearray(len(samples))
    for index, sample in enumerate(samples):
        sample = max(-1.0, min(1.0, sample))
        pcm[index] = max(0, min(255, 128 + int(sample * 118)))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(1)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)


def scaled(samples, factor):
    for index in range(len(samples)):
        samples[index] *= factor
    return samples


def render_music(menu=False):
    bpm = 150
    step = 60.0 / bpm / 4.0
    bars = 8 if menu else 16
    target = _blank(bars * 16 * step)
    chords = (
        ("C2", ("C4", "Eb4", "G4")),
        ("Ab2", ("Ab3", "C4", "Eb4")),
        ("Eb2", ("Eb4", "G4", "Bb4")),
        ("Bb2", ("Bb3", "D4", "F4")),
    )
    melody = (
        "G4", "-", "G4", "Bb4", "C5", "-", "Eb5", "D5",
        "C5", "-", "G4", "Bb4", "G5", "F5", "Eb5", "D5",
        "Eb5", "-", "C5", "Eb5", "G5", "-", "Bb5", "G5",
        "F5", "Eb5", "D5", "Bb4", "D5", "F5", "G5", "-",
    )
    menu_melody = (
        "C5", "-", "G4", "Bb4", "C5", "Eb5", "D5", "-",
        "Ab4", "C5", "Eb5", "-", "G5", "F5", "Eb5", "D5",
    )

    for bar in range(bars):
        root_name, chord = chords[bar % len(chords)]
        bar_start = bar * 16 * step
        for beat in range(4):
            add_tone(
                target,
                bar_start + beat * 4 * step,
                step * 3.6,
                NOTES[root_name],
                0.16 if menu else 0.20,
                "triangle",
            )
            add_kick(target, bar_start + beat * 4 * step, 0.18 if menu else 0.27)
            if not menu and beat in (1, 3):
                add_noise(target, bar_start + beat * 4 * step, 0.07, 0.12)
        for position in range(16):
            note = chord[position % 3]
            add_tone(
                target,
                bar_start + position * step,
                step * 0.72,
                NOTES[note] * 2.0,
                0.075 if menu else 0.09,
                "square",
                0.25,
            )
            if not menu and position % 2:
                add_noise(target, bar_start + position * step, 0.025, 0.045)

        phrase = menu_melody if menu else melody
        phrase_offset = (bar % (1 if menu else 2)) * 16
        for position in range(16):
            note = phrase[(phrase_offset + position) % len(phrase)]
            if note == "-":
                continue
            add_tone(
                target,
                bar_start + position * step,
                step * (0.82 if position % 4 else 1.65),
                NOTES[note],
                0.17 if menu else 0.23,
                "square",
                0.25,
                vibrato=0.006,
            )
    return target


def render_battle_variant(
    bpm,
    bars,
    chords,
    melody,
    kick_steps,
    lead_kind="square",
    lead_duty=0.25,
    arp_duty=0.25,
    hat_stride=2,
):
    """Build one musically distinct, bar-aligned battle loop."""
    step = 60.0 / bpm / 4.0
    target = _blank(bars * 16 * step)
    for bar in range(bars):
        root_name, chord = chords[bar % len(chords)]
        bar_start = bar * 16 * step
        for position in kick_steps:
            add_kick(target, bar_start + position * step, 0.26)
        for position in (4, 12):
            add_noise(target, bar_start + position * step, 0.075, 0.13)
        for position in range(0, 16, hat_stride):
            add_noise(target, bar_start + position * step, 0.022, 0.045)

        bass_pattern = (0, 3, 6, 8, 11, 14)
        for position in bass_pattern:
            add_tone(
                target,
                bar_start + position * step,
                step * (1.7 if position in (0, 8) else 0.72),
                NOTES[root_name],
                0.19,
                "triangle",
            )
        for position in range(16):
            note = chord[(position + bar) % len(chord)]
            add_tone(
                target,
                bar_start + position * step,
                step * 0.66,
                NOTES[note],
                0.085,
                "square",
                arp_duty,
            )

        phrase_offset = (bar % max(1, len(melody) // 16)) * 16
        for position in range(16):
            note = melody[(phrase_offset + position) % len(melody)]
            if note == "-":
                continue
            add_tone(
                target,
                bar_start + position * step,
                step * (1.72 if position % 8 == 0 else 0.80),
                NOTES[note],
                0.23,
                lead_kind,
                lead_duty,
                vibrato=0.005,
            )
    return target


def render_battle_choices():
    """Return four new tunes; the original battle theme is choice one."""
    return {
        "battle_bounce.wav": render_battle_variant(
            132,
            8,
            (
                ("F2", ("F4", "A4", "C5")),
                ("D2", ("D4", "F4", "A4")),
                ("Bb2", ("Bb4", "D5", "F5")),
                ("C3", ("C4", "E4", "G4")),
            ),
            (
                "A4", "C5", "F5", "-", "E5", "C5", "A4", "-",
                "G4", "A4", "C5", "D5", "C5", "A4", "G4", "-",
                "F4", "A4", "C5", "A5", "-", "G5", "F5", "D5",
                "E5", "C5", "G4", "C5", "E5", "G5", "C6", "-",
            ),
            (0, 6, 8, 14),
            lead_kind="triangle",
            arp_duty=0.50,
            hat_stride=4,
        ),
        "battle_pursuit.wav": render_battle_variant(
            168,
            12,
            (
                ("E2", ("E4", "G4", "B4")),
                ("C2", ("C4", "E4", "G4")),
                ("G2", ("G4", "B4", "D5")),
                ("D2", ("D4", "Fs4", "A4")),
            ),
            (
                "B4", "E5", "G5", "B5", "A5", "G5", "E5", "D5",
                "E5", "G5", "B5", "-", "D6", "B5", "G5", "Fs5",
                "E5", "-", "B4", "D5", "E5", "G5", "A5", "B5",
                "A5", "Fs5", "D5", "A4", "D5", "Fs5", "A5", "-",
            ),
            (0, 3, 8, 11),
            lead_duty=0.125,
            arp_duty=0.25,
            hat_stride=1,
        ),
        "battle_midnight.wav": render_battle_variant(
            140,
            8,
            (
                ("Cs2", ("Cs4", "E4", "Gs4")),
                ("A2", ("A4", "Cs5", "E5")),
                ("Fs2", ("Fs4", "A4", "Cs5")),
                ("Gs2", ("Gs4", "B4", "Eb5")),
            ),
            (
                "Gs4", "-", "Cs5", "E5", "-", "Eb5", "Cs5", "B4",
                "Gs4", "B4", "Cs5", "-", "Gs5", "Fs5", "E5", "Eb5",
                "E5", "-", "A4", "Cs5", "E5", "-", "A5", "Gs5",
                "Fs5", "E5", "Cs5", "A4", "B4", "Eb5", "Gs5", "-",
            ),
            (0, 8, 10),
            lead_kind="saw",
            lead_duty=0.50,
            arp_duty=0.125,
            hat_stride=2,
        ),
        "battle_voltage.wav": render_battle_variant(
            156,
            12,
            (
                ("G2", ("G4", "B4", "D5")),
                ("D2", ("D4", "Fs4", "A4")),
                ("E2", ("E4", "G4", "B4")),
                ("C2", ("C4", "E4", "G4")),
            ),
            (
                "G4", "B4", "D5", "G5", "-", "Fs5", "E5", "D5",
                "B4", "D5", "G5", "A5", "G5", "D5", "B4", "-",
                "E5", "G5", "B5", "-", "A5", "G5", "E5", "D5",
                "C5", "E5", "G5", "C6", "B5", "A5", "G5", "-",
            ),
            (0, 7, 8, 14),
            lead_duty=0.375,
            arp_duty=0.25,
            hat_stride=2,
        ),
    }


def effect(duration, builder):
    target = _blank(duration)
    builder(target)
    return target


def render_effects():
    return {
        "bomb_place.wav": effect(0.12, lambda b: add_tone(b, 0, 0.11, 330, 0.46, "square", 0.25, -110)),
        "explosion.wav": effect(0.42, lambda b: (add_noise(b, 0, 0.42, 0.62), add_tone(b, 0, 0.38, 105, 0.38, "triangle", slide=-55))),
        "chain.wav": effect(0.58, lambda b: (add_noise(b, 0, 0.58, 0.72), add_tone(b, 0, 0.52, 180, 0.42, "saw", slide=-130))),
        "brick.wav": effect(0.16, lambda b: (add_noise(b, 0, 0.15, 0.44), add_tone(b, 0, 0.12, 190, 0.20, "square", slide=-80))),
        "pickup.wav": effect(0.20, lambda b: (add_tone(b, 0, 0.09, NOTES["C5"], 0.35, "square", 0.25), add_tone(b, 0.09, 0.10, NOTES["G5"], 0.36, "square", 0.25))),
        "extra_life.wav": effect(0.48, lambda b: tuple(add_tone(b, i * 0.10, 0.16, NOTES[n], 0.36, "square", 0.25) for i, n in enumerate(("C5", "Eb5", "G5", "C6")))),
        "shield.wav": effect(0.30, lambda b: (add_tone(b, 0, 0.28, 520, 0.30, "triangle", slide=520), add_tone(b, 0, 0.25, 780, 0.18, "square", 0.25, slide=420))),
        "teleport.wav": effect(0.38, lambda b: (add_tone(b, 0, 0.36, 180, 0.32, "square", 0.25, slide=920), add_tone(b, 0.04, 0.32, 260, 0.20, "triangle", slide=1180))),
        "enemy_down.wav": effect(0.25, lambda b: add_tone(b, 0, 0.23, 440, 0.38, "square", 0.5, slide=-320)),
        "slime_split.wav": effect(0.28, lambda b: tuple(add_tone(b, i * 0.06, 0.13, 230 + i * 115, 0.27, "square", 0.25, slide=90) for i in range(3))),
        "treasure.wav": effect(0.46, lambda b: tuple(add_tone(b, i * 0.075, 0.17, NOTES[n], 0.32, "square", 0.25) for i, n in enumerate(("C5", "Eb5", "G5", "Bb5", "C6")))),
        "courier.wav": effect(0.66, lambda b: tuple(add_tone(b, i * 0.11, 0.22, NOTES[n], 0.34, "square", 0.25) for i, n in enumerate(("C4", "G4", "C5", "Eb5", "G5")))),
        "hot_pass.wav": effect(0.22, lambda b: (add_tone(b, 0, 0.12, NOTES["G4"], 0.37, "square", 0.25), add_tone(b, 0.10, 0.11, NOTES["C5"], 0.37, "square", 0.25))),
        "warning.wav": effect(0.32, lambda b: (add_tone(b, 0, 0.13, 740, 0.38, "square", 0.5), add_tone(b, 0.17, 0.14, 740, 0.38, "square", 0.5))),
        "player_hit.wav": effect(0.42, lambda b: (add_noise(b, 0, 0.25, 0.42), add_tone(b, 0, 0.40, 390, 0.38, "saw", slide=-310))),
        "stage_clear.wav": effect(0.92, lambda b: tuple(add_tone(b, i * 0.13, 0.26, NOTES[n], 0.34, "square", 0.25) for i, n in enumerate(("C4", "Eb4", "G4", "C5", "G5", "C6")))),
        "game_over.wav": effect(1.18, lambda b: tuple(add_tone(b, i * 0.19, 0.31, NOTES[n], 0.34, "triangle") for i, n in enumerate(("G4", "F4", "Eb4", "D4", "C3")))),
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Leave generous headroom for the native four-stream WAV mixer.
    write_wav(OUTPUT / "menu_theme.wav", scaled(render_music(True), 0.52))
    write_wav(OUTPUT / "battle_theme.wav", scaled(render_music(False), 0.48))
    for name, samples in render_battle_choices().items():
        write_wav(OUTPUT / name, scaled(samples, 0.48))
    for name, samples in render_effects().items():
        write_wav(OUTPUT / name, scaled(samples, 0.72))
    print("generated", len(list(OUTPUT.glob("*.wav"))), "Pico Bomber WAV assets")


if __name__ == "__main__":
    main()
