"""Audio recorder - captures microphone input to WAV with voice activity detection."""
import io
import time
import wave
import threading
import numpy as np

try:
    import sounddevice as sd
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class AudioRecorder:
    """Records audio from the default microphone to an in-memory WAV buffer.

    Supports auto-stop via voice activity detection: after speech is detected,
    recording stops automatically when silence persists for `silence_duration` seconds.
    Uses callback-based streaming for compatibility with all Windows audio backends.
    """

    RATE = 16000
    CHANNELS = 1
    CHUNK = 1024

    def __init__(self):
        self._recording = False
        self._frames: list[bytes] = []
        self._stream = None
        self._stop_event = threading.Event()

        # VAD settings
        self._speech_threshold = 0.02   # amplitude above this = speech
        self._silence_duration = 0.5    # seconds of silence before auto-stop
        self._min_speech_duration = 0.2 # must have at least this much speech before auto-stop kicks in

        # VAD state
        self._speech_detected = False
        self._silence_start: float | None = None
        self._speech_frames = 0

        # Callback for auto-stop
        self.on_silence_detected: callable | None = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        if not HAS_AUDIO:
            raise RuntimeError("sounddevice not installed")
        if self._recording:
            return

        self._frames = []
        self._recording = True
        self._speech_detected = False
        self._silence_start = None
        self._speech_frames = 0
        self._stop_event.clear()

        try:
            self._stream = sd.InputStream(
                samplerate=self.RATE,
                channels=self.CHANNELS,
                dtype="int16",
                blocksize=self.CHUNK,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            print(f"[AudioRecorder] Failed to start: {e}")
            self._recording = False

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        self._recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if not self._frames:
            return b""

        return self._frames_to_wav()

    def get_amplitude(self) -> float:
        """Get current amplitude for waveform visualization (0.0-1.0)."""
        if not self._frames:
            return 0.0
        try:
            last_frame = self._frames[-1]
            data = np.frombuffer(last_frame, dtype=np.int16)
            rms = np.sqrt(np.mean(data.astype(np.float64) ** 2))
            return min(1.0, rms / 16000.0)
        except Exception:
            return 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if not self._recording:
            return

        raw = bytes(indata)
        self._frames.append(raw)

        # Voice activity detection
        data = np.frombuffer(raw, dtype=np.int16)
        rms = np.sqrt(np.mean(data.astype(np.float64) ** 2))
        amplitude = min(1.0, rms / 16000.0)

        if amplitude > self._speech_threshold:
            self._speech_detected = True
            self._speech_frames += 1
            self._silence_start = None
        elif self._speech_detected:
            min_frames = int(self._min_speech_duration * self.RATE / self.CHUNK)
            if self._speech_frames >= min_frames:
                if self._silence_start is None:
                    self._silence_start = time.monotonic()
                elif time.monotonic() - self._silence_start >= self._silence_duration:
                    # Silence long enough after speech — auto-stop
                    self._recording = False
                    if self.on_silence_detected:
                        self.on_silence_detected()

    def _frames_to_wav(self) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.RATE)
            wf.writeframes(b"".join(self._frames))
        return buf.getvalue()
