# 语音识别集成方案

## 当前状态

❌ **不支持真实语音识别** - 只能文本输入（`input()`）

---

## 三种集成方案对比

| 方案 | 难度 | 时间 | 准确率 | 离线 | 推荐度 |
|------|------|------|--------|------|--------|
| **macOS 听写 API** | ⭐ 简单 | 20 分钟 | 80% | ❌ 需联网 | ⭐⭐⭐⭐ |
| **Whisper (CPU)** | ⭐⭐ 中等 | 1 小时 | 95% | ✅ 离线 | ⭐⭐⭐⭐⭐ |
| **录音 + 云 API** | ⭐⭐⭐ 复杂 | 2 小时 | 90% | ❌ 需联网 | ⭐⭐⭐ |

---

## 🚀 方案一：macOS 系统听写（最快）

### 优点
- ✅ 无需安装额外依赖
- ✅ 支持中文
- ✅ 系统级优化，速度快
- ✅ 20 分钟即可完成

### 缺点
- ⚠️ 需要在系统设置中启用听写功能
- ⚠️ 需要联网（首次使用）
- ⚠️ 准确率一般（~80%）

### 实现代码

```python
# app/asr.py (替换现有代码)

import subprocess
import tempfile
import os
from pathlib import Path

class MacOSDictationASR:
    """使用 macOS 系统听写的 ASR 引擎"""

    def __init__(self):
        self.mode = "macos_dictation"
        logger.info(f"ASR initialized in mode: {self.mode}")
        self._check_dictation_enabled()

    def _check_dictation_enabled(self):
        """检查系统听写是否启用"""
        # 可以通过 AppleScript 检查
        script = '''
        tell application "System Events"
            return "System dictation is available"
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            logger.info("✅ macOS dictation is available")
        except:
            logger.warning("⚠️ macOS dictation may need to be enabled in System Preferences")

    def transcribe_once(self) -> Optional[str]:
        """使用 macOS 听写录音并转文字"""
        try:
            print("\n🎤 请说话（按 Fn 键两次开始听写）...")

            # 方法 1: 使用 AppleScript 触发系统听写
            # 这会打开听写界面，用户说话后自动转文字
            script = '''
            tell application "System Events"
                keystroke "x" using {function down, function down}
            end tell
            '''

            # 这里需要用户手动触发听写
            # 更好的方案是下面的方法 2

            print("提示：在 macOS 中按 Fn 键两次激活听写")
            print("或者使用下面的 Whisper 方案实现真正的自动语音识别")

            # 目前仍使用文本输入作为回退
            text = input("或直接输入文字: ").strip()

            if text and text.lower() not in ["exit", "quit", "退出"]:
                logger.info(f"ASR transcribed: {text}")
                return text

            return None

        except Exception as e:
            logger.error(f"ASR error: {e}")
            return None
```

### 启用步骤
1. 系统设置 → 键盘 → 听写 → 开启
2. 运行程序
3. 按 Fn 键两次开始说话

### 限制
- 需要用户手动触发听写（无法完全自动化）
- 更适合作为辅助方案

---

## 🎯 方案二：Whisper（推荐！）⭐⭐⭐⭐⭐

### 优点
- ✅ 准确率极高（95%+）
- ✅ 完全离线
- ✅ 支持中英文混合
- ✅ 自动化程度高
- ✅ 在 Mac M1/M2 上速度快

### 缺点
- ⚠️ 首次需要下载模型（~150MB）
- ⚠️ 需要安装依赖

### 安装步骤

```bash
# 1. 安装音频处理库
pip install pyaudio faster-whisper

# 2. 如果 pyaudio 安装失败，用 brew
brew install portaudio
pip install pyaudio
```

### 实现代码

```python
# app/asr_whisper.py (新文件)

import wave
import pyaudio
from faster_whisper import WhisperModel
from pathlib import Path
import tempfile

class WhisperASR:
    """基于 Faster Whisper 的 ASR 引擎"""

    def __init__(self, model_size="base"):
        """
        初始化 Whisper ASR

        Args:
            model_size: tiny/base/small/medium/large
                       base 推荐（速度快，准确率高）
        """
        self.mode = "whisper"
        print(f"🎤 正在加载 Whisper 模型（{model_size}）...")

        # 加载模型（首次会自动下载）
        self.model = WhisperModel(
            model_size,
            device="cpu",  # Mac M1/M2 可以用 "auto"
            compute_type="int8"  # 量化加速
        )

        # 录音参数
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1

        logger.info(f"✅ Whisper ASR initialized")

    def record_audio(self, duration=5):
        """
        录音指定秒数

        Args:
            duration: 录音时长（秒）

        Returns:
            音频文件路径
        """
        print(f"🎤 开始录音（{duration}秒）...")

        # PyAudio 录音
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )

        frames = []
        for i in range(0, int(self.sample_rate / self.chunk_size * duration)):
            data = stream.read(self.chunk_size)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # 保存为临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wf = wave.open(temp_file.name, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        print("✅ 录音完成")
        return temp_file.name

    def transcribe_once(self, duration=5) -> Optional[str]:
        """
        录音并转文字

        Args:
            duration: 录音时长（秒）

        Returns:
            转录文本
        """
        try:
            # 1. 录音
            audio_file = self.record_audio(duration)

            # 2. 转录
            print("🤖 正在识别...")
            segments, info = self.model.transcribe(
                audio_file,
                language="zh",  # 中文
                beam_size=5
            )

            # 3. 合并所有片段
            text = "".join([seg.text for seg in segments]).strip()

            # 清理临时文件
            Path(audio_file).unlink()

            if text:
                print(f"✅ 识别结果: {text}")
                logger.info(f"ASR transcribed: {text}")
                return text
            else:
                print("⚠️ 未识别到内容")
                return None

        except KeyboardInterrupt:
            print("\n⚠️ 已取消")
            return None
        except Exception as e:
            logger.error(f"ASR error: {e}")
            print(f"❌ 识别失败: {e}")
            return None

    def transcribe_until_silence(self):
        """
        持续录音直到检测到静音
        （高级功能，需要 VAD）
        """
        # TODO: 实现 Voice Activity Detection
        pass


def create_asr_engine(engine="whisper"):
    """
    创建 ASR 引擎

    Args:
        engine: "whisper" | "text" | "macos"
    """
    if engine == "whisper":
        return WhisperASR(model_size="base")
    elif engine == "text":
        from .asr import ASREngine
        return ASREngine()  # 文本输入模式
    else:
        raise ValueError(f"Unknown engine: {engine}")
```

### 使用方法

```python
# 在 main.py 中修改

# 创建 Whisper ASR
from app.asr_whisper import WhisperASR
asr = WhisperASR(model_size="base")

# 录音 5 秒并识别
text = asr.transcribe_once(duration=5)
print(f"你说: {text}")
```

### 模型选择

| 模型 | 大小 | 速度 | 准确率 | 推荐 |
|------|------|------|--------|------|
| tiny | 39 MB | 最快 | 70% | ❌ |
| base | 74 MB | 快 | 85% | ✅ 推荐 |
| small | 244 MB | 中 | 90% | ⭐ 平衡 |
| medium | 769 MB | 慢 | 95% | 高精度 |

---

## 🔧 方案三：录音 + OpenAI Whisper API

### 优点
- ✅ 准确率最高
- ✅ 无需本地模型
- ✅ 支持多语言

### 缺点
- ❌ 需要联网
- ❌ 需要 API Key
- ❌ 有费用（$0.006/分钟）

### 实现代码

```python
import openai
import pyaudio
import wave

class OpenAIWhisperASR:
    def __init__(self, api_key):
        openai.api_key = api_key
        self.mode = "openai_whisper"

    def transcribe_once(self, duration=5):
        # 1. 录音（同方案二）
        audio_file = self.record_audio(duration)

        # 2. 调用 OpenAI API
        with open(audio_file, "rb") as f:
            transcript = openai.Audio.transcribe("whisper-1", f)

        return transcript["text"]
```

---

## 📊 推荐流程

### 第 1 步：快速体验（5 分钟）
保持当前的文本输入模式，先把其他功能完善

### 第 2 步：生产级语音（1 小时）
集成 Faster Whisper，实现真正的语音识别

### 第 3 步：优化体验（可选）
- VAD（语音活动检测）自动开始/停止录音
- 背景噪音消除
- 唤醒词检测

---

## ⚡ 立即实现 Whisper

如果你想立即实现真实语音识别，运行：

```bash
# 1. 安装依赖
pip install pyaudio faster-whisper

# 2. 创建新文件
# (参考上面的 app/asr_whisper.py 代码)

# 3. 修改 main.py
# from app.asr import create_asr_engine  # 旧的
# from app.asr_whisper import WhisperASR  # 新的

# 4. 测试
python -c "from app.asr_whisper import WhisperASR; asr = WhisperASR(); text = asr.transcribe_once(3); print(text)"
```

---

## ✅ 选择建议

| 你的目标 | 推荐方案 | 理由 |
|----------|----------|------|
| **快速演示项目** | 保持文本输入 | 不耽误其他功能开发 |
| **真实产品** | Whisper (方案二) | 准确率高、离线、开源 |
| **最高精度** | OpenAI API (方案三) | 云端最强，但有成本 |

---

## 🎯 我的建议

1. **现在**：保持文本输入，优先完成多步骤组合和内容创作功能
2. **然后**：花 1 小时集成 Faster Whisper
3. **最后**：优化录音体验（VAD、降噪等）

这样能确保核心功能完整，同时也有真实的语音能力！

---

**需要我帮你立即实现 Whisper 语音识别吗？**
