#!/bin/bash
# 对比 LLM 模式和规则模式

echo "🔬 模式对比测试"
echo "========================================"
echo ""

source venv/bin/activate

TEST_COMMAND="帮我搜索一下今天北京的天气怎么样"

echo "测试命令: $TEST_COMMAND"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣ 规则模式 (--no-llm)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python app/main.py run --text "$TEST_COMMAND" --no-llm --dry-run
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣ LLM 模式 (Claude Sonnet 4.5)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python app/main.py run --text "$TEST_COMMAND" --dry-run
echo ""

echo "========================================"
echo "✅ 对比完成！"
echo ""
echo "观察差异："
echo "  - Slots 提取的准确性"
echo "  - 是否去掉了多余的词（一下、怎么样）"
