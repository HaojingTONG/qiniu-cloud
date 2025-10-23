"""
ASR (Automatic Speech Recognition) module.
Placeholder implementation using text input.
TODO: Integrate faster-whisper or system speech recognition.
"""
import logging
from typing import Optional

from .utils import logger


class ASREngine:
    """ASR engine for speech-to-text conversion."""

    def __init__(self):
        """Initialize ASR engine."""
        self.mode = "text_input"  # Placeholder mode
        logger.info(f"ASR initialized in mode: {self.mode}")

    def transcribe_once(self) -> Optional[str]:
        """
        Transcribe one utterance from user.

        Returns:
            Transcribed text or None if cancelled
        """
        try:
            print("\n🎤 请说话（或直接输入文字）: ", end="", flush=True)
            text = input().strip()

            if not text:
                return None

            # Handle exit commands
            if text.lower() in ["exit", "quit", "退出", "拜拜"]:
                return None

            logger.info(f"ASR transcribed: {text}")
            return text

        except KeyboardInterrupt:
            logger.info("ASR cancelled by user")
            return None
        except Exception as e:
            logger.error(f"ASR error: {e}")
            return None

    def transcribe_from_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe from audio file.
        TODO: Implement with faster-whisper.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        logger.warning("Audio transcription not implemented yet")
        return None


def create_asr_engine() -> ASREngine:
    """Factory function to create ASR engine."""
    return ASREngine()
