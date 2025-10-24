#!/usr/bin/env python3
"""
测试 macOS 语音识别功能
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.asr_macos import create_asr_engine


def main():
    print("=" * 60)
    print("🎤 macOS 语音识别测试")
    print("=" * 60)

    # 创建 ASR 引擎
    asr = create_asr_engine(language="zh-CN")

    print("\n1️⃣ 测试麦克风...")
    print("-" * 60)
    if not asr.test_microphone():
        print("\n❌ 麦克风测试失败！")
        print("\n请检查：")
        print("  1. 麦克风是否连接")
        print("  2. 系统设置 → 隐私与安全 → 麦克风 → 允许终端访问")
        return

    print("\n\n2️⃣ 测试语音识别...")
    print("-" * 60)
    print("\n请说一句话测试（例如：把音量调到50%）")

    text = asr.transcribe_once(timeout=5, phrase_time_limit=10)

    if text:
        print(f"\n✅ 测试成功！")
        print(f"   识别结果: {text}")
    else:
        print("\n⚠️  未识别到内容")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试已取消")
    except Exception as e:
        print(f"\n\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
