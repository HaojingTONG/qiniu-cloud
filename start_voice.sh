#!/bin/bash
# 启动语音助手的快捷脚本

echo "🎤 启动语音助手..."
echo "================================"
echo ""

# 激活虚拟环境
source venv/bin/activate

# 检查配置
echo "📋 当前配置："
grep "ASR_ENGINE" .env
grep "ASR_LANGUAGE" .env
echo ""

echo "✅ 准备就绪！"
echo ""
echo "说明："
echo "  - 等待提示后对着麦克风说话"
echo "  - 例如: '把音量调到50%'"
echo "  - 说 '退出' 可以结束程序"
echo ""
echo "================================"
echo ""

# 运行程序
# 使用 LLM 模式（需要 API Key）
python app/main.py run

# 如果不想用 LLM，可以改为：
# python app/main.py run --no-llm
