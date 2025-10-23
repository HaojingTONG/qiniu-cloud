# 🚀 快速开始指南

## 📋 项目功能一览

这是一个**语音对话式 macOS 助手**，可以通过自然语言控制你的 Mac。

### 支持的功能

| 功能 | 示例命令 | 说明 |
|------|---------|------|
| 🔊 **系统设置** | "把音量调到30%" | 调整系统音量 |
| 🎵 **音乐控制** | "播放音乐"、"暂停" | 控制 Music 应用 |
| 🔍 **网页搜索** | "搜索Python教程" | 在 Safari 中搜索 |
| 📝 **创建笔记** | "记录明天开会" | 在 Notes 应用创建笔记 |
| 📱 **应用控制** | "打开Safari" | 启动应用程序 |
| 🛡️ **安全检查** | 自动拦截危险命令 | 删除、格式化等需确认 |

---

## 🎯 启动步骤

### 1️⃣ 激活虚拟环境

每次使用前都需要激活：

```bash
source venv/bin/activate
```

### 2️⃣ 运行命令

#### 方式 A：单条命令（推荐学习）

```bash
# 音量控制（真实执行）
python app/main.py run --text "把音量调到30%" --no-llm

# 网页搜索（dry-run 模式，不实际执行）
python app/main.py run --text "搜索Python教程" --no-llm --dry-run

# 音乐控制
python app/main.py run --text "播放音乐" --no-llm --dry-run

# 创建笔记
python app/main.py run --text "记录今天学习Python" --no-llm --dry-run

# 打开应用
python app/main.py run --text "打开Safari" --no-llm --dry-run
```

#### 方式 B：交互模式

```bash
python app/main.py run --no-llm

# 然后输入命令，例如：
# 🎤 请说话（或直接输入文字）: 把音量调到50%
# 🎤 请说话（或直接输入文字）: 搜索人工智能
# 🎤 请说话（或直接输入文字）: exit  # 退出
```

---

## 🧪 测试和验证

### 运行测试套件

```bash
# 运行 30 个测试用例
python tests/replay.py

# 查看准确率报告
```

### 快速功能测试

```bash
# 运行内置测试
python app/main.py test
```

---

## 📚 命令示例

### ✅ 简单命令（高准确率）

| 输入 | 结果 |
|------|------|
| "把音量调到30%" | ✅ 设置音量为 30% |
| "播放音乐" | ✅ 播放 Music 应用 |
| "暂停" | ✅ 暂停音乐 |
| "搜索Python" | ✅ 打开 Safari 搜索 |
| "打开Safari" | ✅ 启动 Safari |

### ⚠️ 危险命令（会被拦截）

| 输入 | 结果 |
|------|------|
| "删除所有文件" | 🛡️ 要求确认（高风险） |
| "格式化硬盘" | 🛡️ 要求确认（高风险） |
| "关闭网络" | 🛡️ 要求确认（高风险） |

---

## 🔧 常用选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `--text "命令"` | 直接输入文本 | `--text "播放音乐"` |
| `--no-llm` | 不使用 LLM（推荐） | `--no-llm` |
| `--dry-run` | 只显示不执行 | `--dry-run` |
| `--loop` | 循环模式 | `--loop` |

---

## 🎮 实践练习

### 练习 1：音量控制

```bash
# 试试不同音量
python app/main.py run --text "把音量调到50%" --no-llm
python app/main.py run --text "把音量调到20%" --no-llm
```

### 练习 2：搜索功能

```bash
# 搜索不同内容
python app/main.py run --text "搜索macOS教程" --no-llm --dry-run
python app/main.py run --text "查找今天的新闻" --no-llm --dry-run
```

### 练习 3：安全测试

```bash
# 看看安全机制如何工作
python app/main.py run --text "删除文件" --no-llm --dry-run
python app/main.py run --text "格式化硬盘" --no-llm --dry-run
```

---

## 🚀 进阶：使用 LLM 模式

如果你有 Anthropic API Key，可以获得更高准确率：

### 1. 配置 API Key

```bash
# 编辑 .env 文件
nano .env

# 修改这一行：
ANTHROPIC_API_KEY=sk-ant-你的API密钥
```

### 2. 使用 LLM 模式

```bash
# 去掉 --no-llm 标志
python app/main.py run --text "帮我搜索一下今天的天气怎么样"

# LLM 模式准确率可达 90%+
python tests/replay.py --llm
```

---

## ❓ 常见问题

### Q: 每次都要 `source venv/bin/activate` 吗？
A: 是的，每次打开新终端都需要激活虚拟环境。

### Q: 为什么推荐用 `--no-llm`？
A: 因为不需要 API Key，免费且即时响应。对于简单命令准确率已经很高（96.7%）。

### Q: `--dry-run` 是什么意思？
A: 只显示将要执行的操作，不实际执行。用于测试和学习。

### Q: 可以说英文命令吗？
A: 可以！比如 "set volume to 50%"、"search Python tutorials"

---

## 🎉 开始使用吧！

现在你可以：

1. ✅ 启动项目（`source venv/bin/activate`）
2. ✅ 运行命令（`python app/main.py run --text "..."`）
3. ✅ 查看测试（`python tests/replay.py`）
4. ✅ 探索更多功能

**记住**：先用 `--dry-run` 模式测试，确认无误后再实际执行！
