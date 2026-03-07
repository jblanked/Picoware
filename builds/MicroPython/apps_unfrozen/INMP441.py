# originally from https://github.com/miketeachman/micropython-i2s-examples/blob/master/examples/record_mic_to_sdcard_non_blocking.py
# modified to work with INMP441 microphone and Pico W
from machine import Pin, I2S

# INP441 -> PicoCalc
# 3v3 -> 3v3
# GND -> GND
# SCK -> GP0
# WS -> GP1
# SD -> GP21


class INMP441:
    """Class to interface with the INMP441 I2S microphone and record audio to a WAV file on an SD card."""

    # Recording state constants
    RECORD = 0
    PAUSE = 1
    RESUME = 2
    STOP = 3
    ERROR = 4

    def __init__(
        self,
        sck_pin: int = 0,
        ws_pin: int = 1,
        sd_pin: int = 21,
        sample_size_in_bits: int = 16,
        sample_rate_in_hz: int = 22_050,
        i2s_format=I2S.MONO,
        buffer_length_in_bytes: int = 60000,
        storage=None,
    ):
        # I2S Configuration
        self.sck_pin = sck_pin
        self.ws_pin = ws_pin
        self.sd_pin = sd_pin

        self.wav_file = None
        self.audio_in = None
        self.mic_samples = bytearray(10000)
        self.mic_samples_mv = memoryview(self.mic_samples)

        self.format = i2s_format
        self.num_channels = 1 if i2s_format == I2S.MONO else 2
        self.sample_size_in_bits = sample_size_in_bits
        self.sample_rate_in_hz = sample_rate_in_hz
        self.buffer_length_in_bytes = buffer_length_in_bytes

        self.sd = storage
        self.is_recording = False
        self.state = INMP441.STOP

        # internal tracking used by the IRQ callback
        self._num_sample_bytes_written = 0
        self._num_read = 0

        self.audio_in = I2S(
            0,
            sck=Pin(self.sck_pin),
            ws=Pin(self.ws_pin),
            sd=Pin(self.sd_pin),
            mode=I2S.RX,
            bits=self.sample_size_in_bits,
            format=self.format,
            rate=self.sample_rate_in_hz,
            ibuf=self.buffer_length_in_bytes,
        )

    def __del__(self):
        if self.wav_file:
            del self.wav_file
            self.wav_file = None
        if self.audio_in:
            self.audio_in.deinit()
            self.audio_in = None
        self.mic_samples = None
        self.mic_samples_mv = None
        self.is_recording = False
        self.state = INMP441.STOP

    def _create_wav_header(
        self, sample_rate, bits_per_sample, num_channels, num_samples
    ):
        datasize = num_samples * num_channels * bits_per_sample // 8
        header = bytes("RIFF", "ascii")
        header += (datasize + 36).to_bytes(4, "little")
        header += bytes("WAVE", "ascii")
        header += bytes("fmt ", "ascii")
        header += (16).to_bytes(4, "little")
        header += (1).to_bytes(2, "little")
        header += (num_channels).to_bytes(2, "little")
        header += (sample_rate).to_bytes(4, "little")
        header += (sample_rate * num_channels * bits_per_sample // 8).to_bytes(
            4, "little"
        )
        header += (num_channels * bits_per_sample // 8).to_bytes(2, "little")
        header += (bits_per_sample).to_bytes(2, "little")
        header += bytes("data", "ascii")
        header += (datasize).to_bytes(4, "little")
        return header

    def record(self, file_name="inmp441.wav", duration: int = 10) -> bool:
        """Start recording using the IRQ callback state machine (non-blocking).

        Returns True immediately after the first DMA read is queued.  The IRQ
        callback drives all file I/O in the background.  Poll is_recording to
        check completion, or call stop() to end early.  A duration of 0 means
        record indefinitely until stop() is called.
        """
        if not self.sd or not self.audio_in:
            return False

        wave_sample_bytes = self.sample_size_in_bits // 8
        wav_sample_size_in_bytes = wave_sample_bytes
        recording_size = (
            duration * self.sample_rate_in_hz * wave_sample_bytes * self.num_channels
            if duration > 0
            else 0
        )

        self.sd.remove(file_name)

        self.wav_file = self.sd.file_open(file_name)
        if not self.wav_file:
            return False

        # Write a 44-byte placeholder; the real header is written at STOP.
        self.sd.file_write(self.wav_file, bytes(44), "wb")

        self._num_sample_bytes_written = 0
        self._num_read = 0
        self.is_recording = True
        self.state = (
            INMP441.PAUSE
        )  # callback will be installed before we switch to RECORD

        def i2s_callback_rx(arg):
            if self.state == INMP441.RECORD:
                if not self.sd.file_write(
                    self.wav_file,
                    self.mic_samples_mv[: self._num_read],
                    "ab",
                ):
                    self.state = INMP441.ERROR
                self._num_sample_bytes_written += self._num_read
                # Auto-stop when duration is reached
                if 0 < recording_size <= self._num_sample_bytes_written:
                    self.state = INMP441.STOP
                else:
                    self._num_read = self.audio_in.readinto(self.mic_samples_mv)
            elif self.state == INMP441.RESUME:
                self.state = INMP441.RECORD
                self._num_read = self.audio_in.readinto(self.mic_samples_mv)
            elif self.state == INMP441.PAUSE:
                # Keep DMA alive without writing to disk
                self._num_read = self.audio_in.readinto(self.mic_samples_mv)
            elif self.state in (INMP441.STOP, INMP441.ERROR):
                # Write real WAV header at byte 0 using actual sample count
                wav_header = self._create_wav_header(
                    self.sample_rate_in_hz,
                    self.sample_size_in_bits,
                    self.num_channels,
                    self._num_sample_bytes_written
                    // (wav_sample_size_in_bytes * self.num_channels),
                )
                self.sd.file_seek(self.wav_file, 0)
                if not self.sd.file_write(self.wav_file, wav_header, "wb"):
                    print("Failed to write WAV header.")
                if self.wav_file:
                    del self.wav_file
                    self.wav_file = None
                self.audio_in.irq(None)
                self.audio_in.deinit()
                self.audio_in = None
                self.is_recording = False

        self.audio_in.irq(i2s_callback_rx)
        # Kick off the first DMA read, then open the pipeline
        self._num_read = self.audio_in.readinto(self.mic_samples_mv)
        self.state = INMP441.RECORD
        return True

    def pause(self) -> None:
        """Pause recording (DMA keeps running; samples are discarded)."""
        if self.state == INMP441.RECORD:
            self.state = INMP441.PAUSE

    def resume(self) -> None:
        """Resume recording after a pause."""
        if self.state == INMP441.PAUSE:
            self.state = INMP441.RESUME

    def stop(self) -> None:
        """Stop recording and finalise the WAV file."""
        self.state = INMP441.STOP


_loading = None
_mic = None


def __loading_run(view_manager, text: str = "Sending...") -> None:
    """Start loading animation"""
    from picoware.gui.loading import Loading

    global _loading

    if not _loading:
        _loading = Loading(view_manager.draw)
        _loading.set_text(text)
    else:
        _loading.animate()


def start(view_manager) -> bool:
    """Start the app"""

    # first show info screen about connection
    d = view_manager.draw
    fg = view_manager.foreground_color
    d.erase()
    d._text(0, 0, "INMP441 I2S Microphone App", fg)
    d._text(0, 20, "Connect the INMP441 to the PicoCalc as follows:", fg)
    d._text(0, 40, "3v3 -> 3v3", fg)
    d._text(0, 60, "GND -> GND", fg)
    d._text(0, 80, "SCK -> GP0 (UART0_TX)", fg)
    d._text(0, 100, "WS -> GP1 (UART0_RX)", fg)
    d._text(0, 120, "SD -> GP21", fg)
    d.swap()

    inp = view_manager.input_manager
    while True:
        but = inp.button
        if but != -1:
            inp.reset()
            break

    view_manager.freq(True)  # set to lower frequency
    view_manager.draw.set_mode(1)

    global _mic
    _mic = INMP441(
        storage=view_manager.storage,
    )
    return _mic is not None


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        if _mic and _mic.is_recording:
            _mic.stop()
        view_manager.back()
        return

    d = view_manager.draw
    fg = view_manager.foreground_color

    if not _mic:
        return

    if _mic.is_recording:
        # Recording is in progress — animate and listen for stop
        if button == BUTTON_CENTER:
            inp.reset()
            _mic.stop()
        else:
            __loading_run(view_manager, "Recording...")
    elif _mic.state == INMP441.ERROR:
        view_manager.alert("An error occurred during recording. Please try again....")
        _mic.state = INMP441.STOP
    else:
        d.erase()
        d._text(
            0,
            0,
            "Press the center button to start recording audio!\n\nPress the center button again to stop recording.\n\nThe audio is saved as 'inmp441.wav' on the SD card.",
            fg,
        )
        d.swap()
        if button == BUTTON_CENTER:
            inp.reset()
            if _mic and not _mic.is_recording:
                _mic.record()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _mic, _loading
    if _mic:
        if _mic.is_recording:
            _mic.stop()
        del _mic
        _mic = None
    if _loading:
        del _loading
        _loading = None
    view_manager.freq()  # set back to higher frequency
    view_manager.draw.set_mode(0)
    collect()
