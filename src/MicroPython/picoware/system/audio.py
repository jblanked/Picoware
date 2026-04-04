import audio


class Audio(audio.Audio):
    """
    Class to handle audio output (no args)

    Constants:
        HIGH_BEEP, LOW_BEEP,
        NOTE_DOTTED_EIGHTH, NOTE_DOTTED_HALF, NOTE_DOTTED_QUARTER, NOTE_EIGHTH, NOTE_HALF, NOTE_QUARTER,
        NOTE_SIXTEENTH, NOTE_THIRTYSECOND, NOTE_WHOLE,
        PITCH_A3, PITCH_A4, PITCH_A5, PITCH_A6,
        PITCH_AS3, PITCH_AS4, PITCH_AS5, PITCH_AS6,
        PITCH_B3, PITCH_B4, PITCH_B5, PITCH_B6,
        PITCH_C3, PITCH_C4, PITCH_C5, PITCH_C6,
        PITCH_CS3, PITCH_CS4, PITCH_CS5, PITCH_CS6,
        PITCH_D3, PITCH_D4, PITCH_D5, PITCH_D6,
        PITCH_DS3, PITCH_DS4, PITCH_DS5, PITCH_DS6,
        PITCH_E3, PITCH_E4, PITCH_E5, PITCH_E6,
        PITCH_F3, PITCH_F4, PITCH_F5, PITCH_F6,
        PITCH_FS3, PITCH_FS4, PITCH_FS5, PITCH_FS6,
        PITCH_G3, PITCH_G4, PITCH_G5, PITCH_G6,
        PITCH_GS3, PITCH_GS4, PITCH_GS5, PITCH_GS6,
        SILENCE
    """

    def __setattr__(self, name, value):
        if name == "volume":
            self.set_volume(value)
        else:
            super().__setattr__(name, value)


class AudioNote(audio.AudioNote):
    """
    Class to represent a musical note

    Args:
        - left_frequency: Frequency for the left channel in Hz
        - right_frequency: Frequency for the right channel in Hz
        - duration_ms: Duration of the note in milliseconds
    """

    def __setattr__(self, name, value):
        if name == "left_frequency":
            self.set_left_frequency(value)
        elif name == "right_frequency":
            self.set_right_frequency(value)
        elif name == "duration_ms":
            self.set_duration_ms(value)
        else:
            super().__setattr__(name, value)


class AudioSong(audio.AudioSong):
    """
    Class to represent a musical song

    Args:
        - name: Name of the song
        - notes: Tuple of AudioNote objects representing the notes in the song
        - description: Optional description of the song
    """
