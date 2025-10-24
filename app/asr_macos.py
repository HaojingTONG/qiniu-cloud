"""
ASR engine using macOS native speech recognition.
Uses SpeechRecognition library with Google Speech API (free).
"""
import logging
from typing import Optional
import speech_recognition as sr

from .utils import logger


class MacOSASREngine:
    """ASR engine using SpeechRecognition library."""

    def __init__(self, language="zh-CN"):
        """
        Initialize macOS ASR engine.

        Args:
            language: Language code (zh-CN for Chinese, en-US for English)
        """
        self.mode = "macos_speech_recognition"
        self.language = language
        self.recognizer = sr.Recognizer()

        # 调整识别参数
        self.recognizer.energy_threshold = 4000  # 提高噪音阈值
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # 停顿0.8秒视为结束

        logger.info(f"ASR initialized in mode: {self.mode}, language: {self.language}")

    def transcribe_once(self, timeout=5, phrase_time_limit=10) -> Optional[str]:
        """
        Record audio and transcribe to text.

        Args:
            timeout: Seconds to wait for speech to start
            phrase_time_limit: Maximum seconds to record

        Returns:
            Transcribed text or None if failed
        """
        try:
            print(f"\n🎤 请说话（最多 {phrase_time_limit} 秒）...")

            # 使用麦克风录音
            with sr.Microphone() as source:
                # 调整环境噪音
                logger.debug("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                # 开始录音
                logger.debug("Listening...")
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_time_limit
                    )
                except sr.WaitTimeoutError:
                    print("⏱️  超时：未检测到声音")
                    return None

            print("🤖 正在识别...")

            # 使用 Google Speech Recognition（免费）
            try:
                text = self.recognizer.recognize_google(
                    audio,
                    language=self.language
                )

                if text:
                    print(f"✅ 识别结果: {text}")
                    logger.info(f"ASR transcribed: {text}")

                    # 处理退出命令
                    if text.lower() in ["退出", "拜拜", "再见", "exit", "quit"]:
                        return None

                    return text
                else:
                    print("⚠️  未识别到内容")
                    return None

            except sr.UnknownValueError:
                print("❌ 无法识别，请重试")
                logger.warning("Speech recognition could not understand audio")
                return None

            except sr.RequestError as e:
                print(f"❌ 识别服务错误: {e}")
                logger.error(f"Speech recognition service error: {e}")
                return None

        except KeyboardInterrupt:
            print("\n⚠️  已取消")
            logger.info("ASR cancelled by user")
            return None

        except Exception as e:
            logger.error(f"ASR error: {e}")
            print(f"❌ 错误: {e}")
            return None

    def test_microphone(self):
        """测试麦克风是否可用"""
        try:
            print("🎤 测试麦克风...")
            mic_list = sr.Microphone.list_microphone_names()

            if not mic_list:
                print("❌ 未找到麦克风设备")
                return False

            print(f"✅ 找到 {len(mic_list)} 个音频设备:")
            for i, name in enumerate(mic_list):
                print(f"  [{i}] {name}")

            print("\n✅ 麦克风设备检测成功！")
            return True

        except Exception as e:
            print(f"❌ 麦克风测试失败: {e}")
            logger.error(f"Microphone test failed: {e}")
            return False


def create_asr_engine(language="zh-CN") -> MacOSASREngine:
    """
    Factory function to create macOS ASR engine.

    Args:
        language: Language code (zh-CN, en-US, etc.)

    Returns:
        MacOSASREngine instance
    """
    return MacOSASREngine(language=language)
