"""
Whisper ASR implementation for high-accuracy speech recognition.
Uses OpenAI Whisper model (offline, no API required).
"""
import os
import tempfile
import logging
import time
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)


class WhisperASR:
    """High-accuracy ASR using OpenAI Whisper model."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper ASR.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
                - tiny: Fastest, ~80% accuracy, 39M params
                - base: Balanced, ~85% accuracy, 74M params (RECOMMENDED)
                - small: Slower, ~90% accuracy, 244M params
                - medium: Slow, ~95% accuracy, 769M params
                - large: Slowest, ~98% accuracy, 1550M params
        """
        try:
            import whisper
            self.whisper = whisper
        except ImportError:
            raise ImportError(
                "Whisper not installed. Install with: pip install openai-whisper"
            )

        logger.info(f"Loading Whisper model: {model_size}...")
        self.model = self.whisper.load_model(model_size)
        self.model_size = model_size
        logger.info(f"✅ Whisper ({model_size}) model loaded successfully")

    def listen_with_vad(
        self,
        sample_rate: int = 16000,
        device: Optional[int] = None,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 30.0
    ) -> np.ndarray:
        """
        Record audio with Voice Activity Detection (VAD).
        Stops recording after detecting silence.

        Args:
            sample_rate: Sample rate (16000 recommended for Whisper)
            device: Audio input device index (None for default)
            silence_threshold: Energy threshold for silence detection (lower = more sensitive)
            silence_duration: Duration of silence to stop recording (seconds)
            max_duration: Maximum recording duration (seconds)

        Returns:
            numpy array of audio data
        """
        logger.info("🎤 Start speaking... (will auto-stop after silence)")
        print("🎤 请说话... (说完自动停止)")

        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(sample_rate * chunk_duration)

        audio_data = []
        silence_chunks = 0
        silence_chunks_needed = int(silence_duration / chunk_duration)
        max_chunks = int(max_duration / chunk_duration)

        is_speaking = False
        speech_started = False

        def audio_callback(indata, frames, time_info, status):
            nonlocal silence_chunks, is_speaking, speech_started

            # Calculate energy of current chunk
            energy = np.sqrt(np.mean(indata**2))

            # Check if currently speaking
            if energy > silence_threshold:
                is_speaking = True
                speech_started = True
                silence_chunks = 0
            else:
                is_speaking = False
                if speech_started:
                    silence_chunks += 1

            # Store audio data
            audio_data.append(indata.copy())

        # Start recording
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
            blocksize=chunk_samples,
            device=device,
            callback=audio_callback
        ):
            chunk_count = 0

            # Wait for speech to start
            while not speech_started and chunk_count < max_chunks:
                time.sleep(chunk_duration)
                chunk_count += 1

            if not speech_started:
                logger.warning("⚠️ No speech detected")
                print("⚠️ 未检测到语音")
                return np.array([[0.0]], dtype=np.float32)

            logger.info("🗣️ Speech detected, recording...")
            print("🗣️ 检测到语音，正在录音...")

            # Continue recording until silence or max duration
            while silence_chunks < silence_chunks_needed and chunk_count < max_chunks:
                time.sleep(chunk_duration)
                chunk_count += 1

            if silence_chunks >= silence_chunks_needed:
                logger.info("✅ Silence detected, stopping...")
                print("✅ 检测到静音，停止录音")
            else:
                logger.info("⏱️ Max duration reached")
                print("⏱️ 达到最大录音时长")

        # Concatenate all chunks
        if audio_data:
            audio = np.concatenate(audio_data, axis=0)
            logger.info(f"✅ Recording complete ({len(audio)/sample_rate:.1f}s)")
            return audio
        else:
            return np.array([[0.0]], dtype=np.float32)

    def listen(
        self,
        duration: int = 5,
        sample_rate: int = 16000,
        device: Optional[int] = None
    ) -> np.ndarray:
        """
        Record audio from microphone (fixed duration).

        Args:
            duration: Recording duration in seconds
            sample_rate: Sample rate (16000 recommended for Whisper)
            device: Audio input device index (None for default)

        Returns:
            numpy array of audio data
        """
        logger.info(f"🎤 Recording for {duration} seconds...")
        print(f"🎤 请说话... (录音 {duration} 秒)")

        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
            device=device
        )
        sd.wait()  # Wait until recording is finished

        logger.info("✅ Recording complete")
        return audio

    def recognize(
        self,
        audio: Optional[np.ndarray] = None,
        duration: int = None,
        language: str = "zh",
        device: Optional[int] = None,
        use_vad: bool = True
    ) -> str:
        """
        Recognize speech from audio.

        Args:
            audio: Audio data (numpy array). If None, will record from mic.
            duration: Recording duration if audio is None (ignored if use_vad=True)
            language: Language code (zh for Chinese, en for English, None for auto-detect)
            device: Audio input device index
            use_vad: Use Voice Activity Detection (auto-stop after silence)

        Returns:
            Recognized text
        """
        # Record if no audio provided
        if audio is None:
            if use_vad:
                audio = self.listen_with_vad(device=device)
            else:
                audio = self.listen(duration=duration or 10, device=device)

        # Save to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            sf.write(temp_path, audio, 16000)

        try:
            # Transcribe with Whisper
            logger.info("🤖 Transcribing with Whisper...")
            result = self.model.transcribe(
                temp_path,
                language=language,  # 'zh' for Chinese, 'en' for English, None for auto
                task="transcribe",
                fp16=False,  # Set to False for CPU or Mac
                verbose=False
            )

            text = result["text"].strip()
            logger.info(f"✅ Whisper result: {text}")
            print(f"✅ 识别结果: {text}")

            return text

        except Exception as e:
            logger.error(f"❌ Whisper transcription failed: {e}")
            raise

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

    def list_devices(self):
        """List available audio input devices."""
        print("\n可用的音频设备：")
        print(sd.query_devices())


def create_whisper_asr(model_size: str = "base") -> WhisperASR:
    """Factory function to create Whisper ASR instance."""
    return WhisperASR(model_size=model_size)


if __name__ == "__main__":
    # Test Whisper ASR
    print("Testing Whisper ASR...")

    # List devices
    asr = WhisperASR(model_size="base")
    asr.list_devices()

    # Test recognition
    text = asr.recognize(duration=5, language="zh")
    print(f"\n你说的是: {text}")
