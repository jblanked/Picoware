/*
Author: Blair Leduc
License: MIT License
Source: https://github.com/BlairLeduc/picocalc-text-starter
*/

#pragma once

#include "pico/stdlib.h"
#include "audio_config.h"

// Channels
#define LEFT_CHANNEL (0)
#define RIGHT_CHANNEL (1)

// Pitch and their frequencies (in Hz)

// Octave 3 (Low notes)
#define PITCH_C3  (131)
#define PITCH_CS3 (139)
#define PITCH_D3  (147)
#define PITCH_DS3 (156)
#define PITCH_E3  (165)
#define PITCH_F3  (175)
#define PITCH_FS3 (185)
#define PITCH_G3  (196)
#define PITCH_GS3 (208)
#define PITCH_A3  (220)
#define PITCH_AS3 (233)
#define PITCH_B3  (247)

// Octave 4 (Middle notes)
#define PITCH_C4  (262)
#define PITCH_CS4 (277)
#define PITCH_D4  (294)
#define PITCH_DS4 (311)
#define PITCH_E4  (330)
#define PITCH_F4  (349)
#define PITCH_FS4 (370)
#define PITCH_G4  (392)
#define PITCH_GS4 (415)
#define PITCH_A4  (440)  // A440 - Concert pitch
#define PITCH_AS4 (466)
#define PITCH_B4  (494)

// Octave 5 (High notes)
#define PITCH_C5  (523)
#define PITCH_CS5 (554)
#define PITCH_D5  (587)
#define PITCH_DS5 (622)
#define PITCH_E5  (659)
#define PITCH_F5  (698)
#define PITCH_FS5 (740)
#define PITCH_G5  (784)
#define PITCH_GS5 (831)
#define PITCH_A5  (880)
#define PITCH_AS5 (932)
#define PITCH_B5  (988)

// Octave 6 (Very high notes)
#define PITCH_C6  (1047)
#define PITCH_CS6 (1109)
#define PITCH_D6  (1175)
#define PITCH_DS6 (1245)
#define PITCH_E6  (1319)
#define PITCH_F6  (1397)
#define PITCH_FS6 (1480)
#define PITCH_G6  (1568)
#define PITCH_GS6 (1661)
#define PITCH_A6  (1760)
#define PITCH_AS6 (1865)
#define PITCH_B6  (1976)

// Special pitches
#define SILENCE (0)
#define LOW_BEEP (100)
#define HIGH_BEEP (2000)

// Common chord frequencies (for convenience)
#define CHORD_C_MAJOR PITCH_C4, PITCH_E4, PITCH_G4
#define CHORD_G_MAJOR PITCH_G4, PITCH_B4, PITCH_D5
#define CHORD_F_MAJOR PITCH_F4, PITCH_A4, PITCH_C5

// Note lengths in milliseconds
#define NOTE_WHOLE     (2000)    // Whole note - 2 seconds
#define NOTE_HALF      (1000)    // Half note - 1 second
#define NOTE_QUARTER   (500)     // Quarter note - 0.5 seconds
#define NOTE_EIGHTH    (250)     // Eighth note - 0.25 seconds
#define NOTE_SIXTEENTH (125)     // Sixteenth note - 0.125 seconds
#define NOTE_THIRTYSECOND (62)   // Thirty-second note - 0.062 seconds

// Common note length variations
#define NOTE_DOTTED_HALF      (1500)    // Dotted half note (1.5x half note)
#define NOTE_DOTTED_QUARTER   (750)     // Dotted quarter note (1.5x quarter note)
#define NOTE_DOTTED_EIGHTH    (375)     // Dotted eighth note (1.5x eighth note)

// Tempo-based note lengths (120 BPM as default)
#define NOTE_WHOLE_120BPM     (2000)    // Whole note at 120 BPM
#define NOTE_HALF_120BPM      (1000)    // Half note at 120 BPM
#define NOTE_QUARTER_120BPM   (500)     // Quarter note at 120 BPM
#define NOTE_EIGHTH_120BPM    (250)     // Eighth note at 120 BPM

// Fast tempo note lengths (140 BPM)
#define NOTE_WHOLE_140BPM     (1714)    // Whole note at 140 BPM
#define NOTE_HALF_140BPM      (857)     // Half note at 140 BPM
#define NOTE_QUARTER_140BPM   (429)     // Quarter note at 140 BPM
#define NOTE_EIGHTH_140BPM    (214)     // Eighth note at 140 BPM

// Slow tempo note lengths (80 BPM)
#define NOTE_WHOLE_80BPM      (3000)    // Whole note at 80 BPM
#define NOTE_HALF_80BPM       (1500)    // Half note at 80 BPM
#define NOTE_QUARTER_80BPM    (750)     // Quarter note at 80 BPM
#define NOTE_EIGHTH_80BPM     (375)     // Eighth note at 80 BPM

typedef struct {
    uint16_t left_frequency;  // Frequency in Hz
    uint16_t right_frequency; // Frequency in Hz
    uint32_t duration_ms; // Duration in milliseconds
} audio_note_t;

// Structure to hold song information
typedef struct {
    const char* name;           // Short name for command reference
    const audio_note_t* notes;  // Pointer to the song data
    const char* description;    // Full song title and artist
} audio_song_t;

// Audio driver function prototypes
void audio_init(void);

void audio_play_sound_blocking(uint32_t left_frequency, uint32_t right_frequency, uint32_t duration_ms);
void audio_play_sound(uint32_t left_frequency, uint32_t right_frequency);

void audio_play_note_blocking(const audio_note_t *note);
void audio_play_song_blocking(const audio_song_t *song);

void audio_stop(void);
bool audio_is_playing(void);

