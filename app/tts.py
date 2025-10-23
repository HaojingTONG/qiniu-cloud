"""
TTS (Text-to-Speech) module using macOS 'say' command.
"""
import subprocess
import logging
from typing import Optional

from .utils import logger


class TTSEngine:
    """TTS engine for text-to-speech conversion."""

    def __init__(self, voice: Optional[str] = None):
        """
        Initialize TTS engine.

        Args:
            voice: Voice name (e.g., "Ting-Ting" for Chinese)
        """
        self.voice = voice or "Ting-Ting"  # Default Chinese voice
        logger.info(f"TTS initialized with voice: {self.voice}")

    def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Speak text using macOS 'say' command.

        Args:
            text: Text to speak
            blocking: If True, wait for speech to complete

        Returns:
            True if successful
        """
        if not text:
            return False

        try:
            logger.info(f"TTS speaking: {text}")
            print(f"\n🔊 {text}")

            cmd = ["say", "-v", self.voice, text]

            if blocking:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.returncode == 0
            else:
                # Non-blocking
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True

        except subprocess.TimeoutExpired:
            logger.error("TTS timeout")
            return False
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop current speech.

        Returns:
            True if successful
        """
        try:
            subprocess.run(["killall", "say"], check=False)
            return True
        except Exception as e:
            logger.error(f"Failed to stop TTS: {e}")
            return False


def create_tts_engine(voice: Optional[str] = None) -> TTSEngine:
    """Factory function to create TTS engine."""
    return TTSEngine(voice=voice)
