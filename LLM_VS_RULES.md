# LLM 模式 vs 规则模式对比

## 🔍 快速回答

### Q: `./start_voice.sh` 用 LLM 吗？

**之前**：❌ 不用（有 `--no-llm` 参数）
**现在**：✅ **用**（已删除 `--no-llm` 参数）

---

## 📊 详细对比

| 对比项 | LLM 模式 | 规则模式 |
|--------|----------|----------|
| **使用模型** | Claude Sonnet 4.5 | 关键词正则匹配 |
| **准确率** | 🟢 90-95% | 🟡 70% |
| **响应速度** | 🟡 2-3秒 | 🟢 即时 |
| **成本** | 🟡 API 调用费 | 🟢 免费 |
| **联网要求** | 🟡 需要 | 🟢 不需要 |
| **API Key** | 🟡 必需 | 🟢 不需要 |
| **理解能力** | 🟢 强（复杂句） | 🟡 弱（简单句） |

---

## 🎯 实际效果对比

### 测试用例 1：复杂语句

**输入**："帮我搜索一下今天北京的天气怎么样"

#### LLM 模式 ✅
```json
{
  "intent": "web_search",
  "slots": {
    "query": "今天北京的天气"  // ✅ 准确提取，去掉了"帮我"、"一下"、"怎么样"
  }
}
```

#### 规则模式 ⚠️
```json
{
  "intent": "web_search",
  "slots": {
    "query": "一下今天北京的天气怎么样"  // ❌ 保留了多余词语
  }
}
```

---

### 测试用例 2：简单命令

**输入**："把音量调到50%"

#### LLM 模式 ✅
```json
{
  "intent": "system_setting",
  "slots": {
    "setting": "volume",
    "value": 50
  }
}
```

#### 规则模式 ✅
```json
{
  "intent": "system_setting",
  "slots": {
    "setting": "volume",
    "value": 50
  }
}
```

**结论**：简单命令两种模式都很准确

---

### 测试用例 3：口语化表达

**输入**："我想听点音乐放松一下"

#### LLM 模式 ✅
```json
{
  "intent": "play_music",
  "slots": {
    "action": "play"
  },
  "speak_back": "好的，为您播放音乐"
}
```

#### 规则模式 ❌
```json
{
  "intent": "clarify",  // ❌ 无法识别
  "confirm": true,
  "speak_back": "抱歉，我不太理解您的意思"
}
```

---

## 🚀 如何选择？

### 使用 LLM 模式（推荐）

```bash
./start_voice.sh  # 现在默认就是 LLM 模式
```

**适合场景**：
- ✅ 复杂的自然语言
- ✅ 口语化表达
- ✅ 追求高准确率
- ✅ 有 API Key

---

### 使用规则模式

```bash
# 方式 1：修改 start_voice.sh
# 把第 29 行改为：
python app/main.py run --no-llm

# 方式 2：直接运行
python app/main.py run --no-llm
```

**适合场景**：
- ✅ 简单命令（"把音量调到50%"）
- ✅ 快速测试调试
- ✅ 无网络环境
- ✅ 节省 API 成本

---

## 🔬 运行对比测试

我已经为你创建了对比脚本：

```bash
./compare_modes.sh
```

**测试内容**：
- 同一个命令分别用两种模式处理
- 直观对比输出结果
- 查看准确率差异

---

## 📈 准确率统计

### 在 30 个测试用例上的表现

| 模式 | Intent 准确率 | Slots 准确率 | 整体准确率 |
|------|---------------|--------------|------------|
| **LLM** | 95%+ | 90%+ | **90%+** |
| **规则** | 96.7% | 70% | **66.7%** |

**注意**：
- 规则模式的 Intent 识别也很高（96.7%）
- 但 Slots 提取较差（70%），导致整体只有 66.7%
- LLM 模式在两方面都更均衡

---

## 💰 成本考虑

### LLM 模式成本

```
Claude Sonnet 4.5 定价：
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

每次调用估算：
- System prompt: ~500 tokens
- Few-shot: ~300 tokens
- User input: ~50 tokens
- Output: ~100 tokens
━━━━━━━━━━━━━━━━━━━━━━━
Total: ~950 tokens ≈ $0.02

每天 100 次调用 ≈ $2
```

### 规则模式成本

```
✅ 完全免费
```

---

## 🎛️ 当前配置

### 查看当前使用哪种模式

```bash
# 查看 start_voice.sh
cat start_voice.sh | grep "python app/main.py run"

# 有 --no-llm → 规则模式
# 没有 --no-llm → LLM 模式
```

### 当前配置（已修改）

```bash
# start_voice.sh 第 29 行
python app/main.py run  # ← LLM 模式（新）
```

**之前**：
```bash
python app/main.py run --no-llm  # ← 规则模式（旧）
```

---

## 🔄 智能回退机制

### 即使选择 LLM，系统也有保护

```
用户命令
   ↓
尝试 LLM 识别
   ↓
   ├─ 成功 → 返回结果 ✅
   │
   └─ 失败（网络/API/解析错误）
       ↓
   自动回退到规则引擎 🔄
       ↓
   返回结果（可能准确率低）⚠️
```

**优点**：
- ✅ 鲁棒性强
- ✅ LLM 失败不会完全崩溃
- ✅ 总有一个结果返回

---

## 📝 命令对照表

| 命令 | 模式 | 说明 |
|------|------|------|
| `./start_voice.sh` | LLM | 现在的默认（刚改的）|
| `python app/main.py run` | LLM | 等同于上面 |
| `python app/main.py run --no-llm` | 规则 | 明确指定不用 LLM |
| `python app/main.py run --text "xxx"` | LLM | 单次命令，用 LLM |
| `python app/main.py run --text "xxx" --no-llm` | 规则 | 单次命令，用规则 |

---

## ✅ 总结

### 当前状态

**之前运行 `./start_voice.sh` 时**：
- ❌ 没有使用 LLM（有 `--no-llm` 参数）
- ✅ 只用规则引擎

**现在运行 `./start_voice.sh` 时**：
- ✅ **使用 LLM**（已删除 `--no-llm`）
- ✅ Claude Sonnet 4.5
- ✅ 准确率 90%+

### 建议

1. **日常使用**：用 LLM 模式（更准确）
2. **快速测试**：用规则模式（更快）
3. **成本敏感**：用规则模式（免费）

### 对比测试

```bash
./compare_modes.sh  # 看看两种模式的差异
```

---

**现在 `./start_voice.sh` 已经使用 LLM 了！🎉**
