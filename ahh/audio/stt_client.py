"""Speech-to-text using ElevenLabs API."""
import os
import io
import logging
import httpx

log = logging.getLogger("ahh")


class STTClient:
    """Transcribes audio using ElevenLabs Speech-to-Text API."""

    def __init__(self):
        self.api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self.url = "https://api.elevenlabs.io/v1/speech-to-text"

    def transcribe(self, wav_bytes: bytes) -> str:
        """Transcribe WAV audio bytes to text.

        Args:
            wav_bytes: Raw WAV file bytes.

        Returns:
            Transcribed text string.
        """
        if not wav_bytes:
            return ""

        try:
            response = httpx.post(
                self.url,
                headers={"xi-api-key": self.api_key},
                files={"file": ("recording.wav", wav_bytes, "audio/wav")},
                data={"model_id": "scribe_v1"},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            text = result.get("text", "").strip()
            log.info(f"Transcribed: {text}")
            return text
        except Exception as e:
            log.error(f"ElevenLabs STT failed: {e}")
            return ""
