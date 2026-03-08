"""Text-to-speech using ElevenLabs streaming API."""
import os
import logging
import numpy as np
import sounddevice as sd
import threading
import httpx

log = logging.getLogger("ahh")


class TTSClient:
    """Generates and plays speech using ElevenLabs streaming API."""

    def __init__(self):
        self._api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self._voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        self._model_id = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
        self._playing = False
        self._stop_flag = False
        self._current_text = ""
        self.on_play_start = None
        self.on_play_stop = None

    def speak(self, text: str, voice: str = ""):
        """Generate speech from text and play it. Uses streaming download + sd.play()."""
        if not text:
            return

        self._current_text = text
        self._stop_flag = False
        voice_id = voice or self._voice_id

        try:
            # Stream download for lower latency on first byte
            chunks = []
            with httpx.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": self._model_id,
                    "optimize_streaming_latency": 3,
                },
                params={"output_format": "pcm_24000"},
                timeout=30.0,
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=4800):
                    if self._stop_flag:
                        return
                    chunks.append(chunk)

            if not chunks or self._stop_flag:
                return

            pcm_data = b"".join(chunks)
            self._play_pcm(pcm_data)

        except Exception as e:
            log.error(f"ElevenLabs TTS failed: {e}")

    def speak_async(self, text: str, voice: str = ""):
        """Generate and play speech in a background thread."""
        thread = threading.Thread(target=self.speak, args=(text, voice), daemon=True)
        thread.start()
        return thread

    def _play_pcm(self, pcm_data: bytes):
        """Play raw PCM audio data through speakers."""
        self._playing = True
        if self.on_play_start:
            try:
                self.on_play_start(self._current_text)
            except Exception:
                pass
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            sd.play(audio_array, samplerate=24000, blocking=True)
        except Exception as e:
            log.error(f"Audio playback error: {e}")
        finally:
            self._playing = False
            if self.on_play_stop:
                try:
                    self.on_play_stop()
                except Exception:
                    pass

    def stop(self):
        """Stop any currently playing audio."""
        self._stop_flag = True
        self._playing = False
        try:
            sd.stop()
        except Exception:
            pass
