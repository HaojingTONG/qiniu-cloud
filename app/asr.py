"""
ASR (Automatic Speech Recognition) module with multiple engines.
Supports: Google Speech API, Whisper, and text input.
Includes LLM-based error correction and custom vocabulary.
"""
import logging
from typing import Optional, Literal
import json
from datetime import datetime

from .utils import logger

# Custom vocabulary for common errors (步骤 3)
CUSTOM_VOCABULARY = {
    # 同音字映射 (Homophone corrections)
    "因量": "音量",
    "音亮": "音量",
    "沙发里": "Safari",
    "克隆": "Chrome",
    "搜锁": "搜索",
    "搜缩": "搜索",
    "播方": "播放",
    "暂停止": "暂停",

    # 应用名称 (App names)
    "微心": "微信",
    "记事本": "Notes",

    # 数字规范化 (Number normalization)
    "五十": "50",
    "三十": "30",
    "二十": "20",
    "百分之五十": "50%",
    "百分之三十": "30%",
    "百分之二十": "20%",
}

ASREngine = Literal["text", "google", "whisper"]


class ASR:
    """Multi-engine ASR with error correction."""

    def __init__(
        self,
        engine: ASREngine = "text",
        whisper_model: str = "base",
        enable_llm_correction: bool = True
    ):
        """
        Initialize ASR engine.

        Args:
            engine: ASR engine to use ("text", "google", "whisper")
            whisper_model: Whisper model size (if using whisper engine)
            enable_llm_correction: Enable LLM-based error correction
        """
        self.engine = engine
        self.enable_llm_correction = enable_llm_correction

        # Initialize engine-specific components
        if engine == "google":
            self._init_google()
        elif engine == "whisper":
            self._init_whisper(whisper_model)

        logger.info(f"ASR initialized: engine={engine}, llm_correction={enable_llm_correction}")

    def _init_google(self):
        """Initialize Google Speech Recognition (步骤 4: 优化录音参数)."""
        try:
            import speech_recognition as sr

            self.recognizer = sr.Recognizer()

            # 优化参数 (Optimized parameters)
            self.recognizer.energy_threshold = 4000  # 提高阈值减少噪音
            self.recognizer.dynamic_energy_threshold = True  # 自动调整
            self.recognizer.pause_threshold = 0.8  # 停顿检测（秒）
            self.recognizer.phrase_threshold = 0.3  # 短语识别敏感度
            self.recognizer.non_speaking_duration = 0.5  # 非语音持续时间

            logger.info("✅ Google Speech Recognition initialized with optimized parameters")

        except ImportError:
            raise ImportError(
                "SpeechRecognition not installed. Install with: pip install SpeechRecognition pyaudio"
            )

    def _init_whisper(self, model_size: str):
        """Initialize Whisper ASR."""
        try:
            from .asr_whisper import WhisperASR
            self.whisper = WhisperASR(model_size=model_size)
            logger.info(f"✅ Whisper ASR initialized (model: {model_size})")
        except ImportError:
            raise ImportError(
                "Whisper not installed. Install with: pip install openai-whisper"
            )

    def normalize_text(self, text: str) -> str:
        """
        步骤 3: 使用自定义词汇表规范化文本
        Apply custom vocabulary corrections.

        Args:
            text: Raw transcribed text

        Returns:
            Normalized text
        """
        original = text

        # Apply custom vocabulary mappings
        for wrong, correct in CUSTOM_VOCABULARY.items():
            text = text.replace(wrong, correct)

        if text != original:
            logger.info(f"📝 Vocabulary correction: '{original}' → '{text}'")

        return text

    def correct_with_llm(self, text: str) -> str:
        """
        步骤 2: 使用 LLM 纠正 ASR 错误
        Use LLM to correct ASR errors.

        Args:
            text: Raw transcribed text

        Returns:
            Corrected text
        """
        if not self.enable_llm_correction:
            return text

        try:
            from .llm import get_llm_client

            llm_client = get_llm_client()

            prompt = f"""你是一个语音识别纠错助手。用户通过语音输入了以下文本，但可能存在识别错误。

原始识别文本："{text}"

请根据上下文纠正可能的错误，输出纠正后的文本。只输出纠正后的文本，不要解释。

常见错误模式：
- 同音字错误："把音量调到30%" 可能被识别为 "把因量调到30%"
- 数字识别错误："50%" 可能被识别为 "五十"
- 应用名称错误："Safari" 可能被识别为 "沙发里"
- "搜索" 可能被识别为 "搜锁" 或 "搜缩"
- "播放" 可能被识别为 "播方"

如果原文本没有明显错误，就直接返回原文本。

纠正后的文本："""

            result = llm_client.client.messages.create(
                model=llm_client.model,
                max_tokens=200,
                temperature=0.0,  # 低温度确保稳定输出
                messages=[{"role": "user", "content": prompt}]
            )

            corrected = result.content[0].text.strip()

            # Remove quotes if LLM wrapped the result
            corrected = corrected.strip('"').strip("'")

            if corrected != text:
                logger.info(f"🤖 LLM correction: '{text}' → '{corrected}'")

            return corrected

        except Exception as e:
            logger.warning(f"⚠️ LLM correction failed: {e}, using original text")
            return text

    def transcribe_once(self, language: str = "zh-CN") -> Optional[str]:
        """
        Transcribe one utterance from user.

        Args:
            language: Language code (zh-CN for Chinese, en-US for English)

        Returns:
            Transcribed and corrected text, or None if cancelled
        """
        # Step 1: Get raw transcription from engine
        if self.engine == "text":
            raw_text = self._transcribe_text()
        elif self.engine == "google":
            raw_text = self._transcribe_google(language)
        elif self.engine == "whisper":
            # Extract language code (zh-CN -> zh)
            lang = language.split("-")[0]
            raw_text = self._transcribe_whisper(lang)
        else:
            logger.error(f"Unknown engine: {self.engine}")
            return None

        if not raw_text:
            return None

        # Step 2: Apply custom vocabulary normalization (步骤 3)
        normalized_text = self.normalize_text(raw_text)

        # Step 3: Apply LLM correction (步骤 2)
        corrected_text = self.correct_with_llm(normalized_text)

        return corrected_text

    def _transcribe_text(self) -> Optional[str]:
        """Text input mode."""
        try:
            print("\n🎤 请说话（或直接输入文字）: ", end="", flush=True)
            text = input().strip()

            if not text:
                return None

            # Handle exit commands
            if text.lower() in ["exit", "quit", "退出", "拜拜"]:
                return None

            logger.info(f"Text input: {text}")
            return text

        except KeyboardInterrupt:
            logger.info("Input cancelled by user")
            return None
        except Exception as e:
            logger.error(f"Text input error: {e}")
            return None

    def _transcribe_google(self, language: str) -> Optional[str]:
        """
        步骤 4: Google Speech Recognition with optimized parameters.

        Args:
            language: Language code

        Returns:
            Transcribed text
        """
        try:
            import speech_recognition as sr

            print("\n🎤 请说话...")

            with sr.Microphone(sample_rate=16000) as source:
                # 步骤 4: 环境噪音自适应 (Ambient noise adjustment)
                logger.info("🔇 调整环境噪音...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                logger.info("🎤 开始录音...")
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)

            logger.info("🤖 识别中...")
            text = self.recognizer.recognize_google(audio, language=language)

            logger.info(f"✅ Google ASR result: {text}")
            return text

        except sr.WaitTimeoutError:
            logger.warning("⚠️ 未检测到语音")
            print("⚠️ 未检测到语音，请重试")
            return None
        except sr.UnknownValueError:
            logger.warning("⚠️ 无法识别语音")
            print("⚠️ 无法识别，请重试")
            return None
        except sr.RequestError as e:
            logger.error(f"❌ Google API error: {e}")
            print(f"❌ API 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Google ASR error: {e}")
            return None

    def _transcribe_whisper(self, language: str) -> Optional[str]:
        """
        步骤 1: Whisper transcription with VAD.

        Args:
            language: Language code (zh, en)

        Returns:
            Transcribed text
        """
        try:
            # Use VAD (Voice Activity Detection) - auto-stop after silence
            text = self.whisper.recognize(language=language, use_vad=True)
            return text
        except Exception as e:
            logger.error(f"❌ Whisper ASR error: {e}")
            return None

    def log_correction(self, raw: str, corrected: str):
        """
        Log ASR corrections for future analysis.

        Args:
            raw: Raw transcribed text
            corrected: User-confirmed corrected text
        """
        log_file = "logs/asr_corrections.jsonl"

        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "engine": self.engine,
            "raw": raw,
            "corrected": corrected
        }

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info(f"📝 Logged correction: '{raw}' → '{corrected}'")
        except Exception as e:
            logger.warning(f"Failed to log correction: {e}")


def create_asr_engine(
    engine: ASREngine = "text",
    whisper_model: str = "base",
    enable_llm_correction: bool = True
) -> ASR:
    """
    Factory function to create ASR engine.

    Args:
        engine: ASR engine ("text", "google", "whisper")
        whisper_model: Whisper model size (tiny, base, small, medium, large)
        enable_llm_correction: Enable LLM-based error correction

    Returns:
        ASR instance
    """
    return ASR(
        engine=engine,
        whisper_model=whisper_model,
        enable_llm_correction=enable_llm_correction
    )
