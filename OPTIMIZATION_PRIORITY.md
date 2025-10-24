# 🎯 项目优化优先级清单

## 📊 当前项目状态分析

### ✅ 已完成（70%）

| 功能 | 状态 | 质量 |
|------|------|------|
| 语音识别（ASR） | ✅ | 🟢 良好（85-90%）|
| 语音反馈（TTS） | ✅ | 🟢 良好 |
| LLM 意图识别 | ✅ | 🟢 优秀（90%+）|
| 规则引擎回退 | ✅ | 🟢 良好（70%）|
| 系统控制（音量） | ✅ | 🟢 优秀 |
| 音乐播放 | ✅ | 🟢 良好 |
| 网页搜索 | ✅ | 🟢 良好（刚修复）|
| 创建笔记 | ✅ | 🟢 良好 |
| 应用控制 | ✅ | 🟢 良好 |
| 安全机制 | ✅ | 🟢 优秀 |

### ❌ 缺失（30%）- 议题二核心要求

| 功能 | 状态 | 影响 |
|------|------|------|
| **多步骤任务组合** | ❌ 未实现 | 🔴 致命（议题二核心）|
| **内容创作（写文章）** | ❌ 未实现 | 🔴 致命（议题二核心）|
| 文件操作 | ❌ 未实现 | 🟡 重要 |
| 对话上下文 | ❌ 未实现 | 🟢 可选 |

---

## 🎯 优化优先级（按紧急程度）

---

## 🔴 P0 级：必须实现（满足议题二要求）

### 1. 多步骤任务组合 ⭐⭐⭐⭐⭐

**优先级**：🔴 **最高**（议题二核心要求）

**问题**：
- 当前只能执行单步任务
- 无法组合多个能力
- 不满足"组合这些能力实现复杂场景"的要求

**目标**：
```
用户："帮我写一篇关于 AI 的文章，然后保存到桌面，并用邮件发送给自己"

系统应该：
1. 调用 LLM 生成文章
2. 保存文件到桌面
3. 打开邮件应用
4. 附加文件并创建邮件
```

**实现方案**：

#### 步骤 1：扩展 Intent Schema
```python
# app/schema.py

class MultiStepIntent(BaseModel):
    """多步骤任务"""
    task_name: str
    steps: List[Intent]
    dependencies: List[str] = []  # 步骤依赖关系
    context: Dict[str, Any] = {}   # 共享上下文

class Intent(BaseModel):
    intent: IntentName
    slots: Dict[str, Any]
    # ... 现有字段
    is_multi_step: bool = False    # 是否为多步骤任务
    step_index: Optional[int] = None  # 步骤索引
```

#### 步骤 2：修改 LLM Prompt
```python
# prompts/system.txt 添加：

"支持多步骤任务输出：
{
  \"is_multi_step\": true,
  \"steps\": [
    {\"intent\": \"content_creation\", \"slots\": {...}},
    {\"intent\": \"file_operation\", \"slots\": {...}},
    {\"intent\": \"control_app\", \"slots\": {...}}
  ]
}
"
```

#### 步骤 3：实现 MultiStepExecutor
```python
# app/multi_step_executor.py

class MultiStepExecutor:
    def execute(self, multi_intent: MultiStepIntent):
        context = {}

        for i, step in enumerate(multi_intent.steps):
            print(f"执行步骤 {i+1}/{len(multi_intent.steps)}: {step.intent}")

            # 执行步骤
            result = self.executor.execute(step)

            if not result.success:
                return self._handle_failure(i, result)

            # 保存结果到上下文
            context[f"step_{i}"] = result.output

            # 传递上下文给下一步
            if i < len(multi_intent.steps) - 1:
                self._inject_context(multi_intent.steps[i+1], context)

        return ExecutionResult(success=True, message="所有步骤完成")
```

**工作量**：2-3 天

**验收标准**：
```bash
# 测试命令
python app/main.py run --text "写一篇文章然后保存到桌面"

# 预期结果：
# ✅ 生成文章
# ✅ 保存文件
# ✅ 返回成功
```

---

### 2. 内容创作功能 ⭐⭐⭐⭐⭐

**优先级**：🔴 **最高**（议题二明确要求）

**问题**：
- 当前只能创建简单笔记（几十字）
- 无法"写一篇文章"
- 不满足议题二的"写一篇文章"要求

**目标**：
```
用户："写一篇 500 字关于人工智能的文章"

系统应该：
1. 调用 LLM 生成长文本（500字）
2. 自动分段、格式化
3. 保存到文件或笔记
4. 可选：打开编辑器查看
```

**实现方案**：

#### 步骤 1：添加新意图
```python
# app/schema.py

IntentName = Literal[
    "system_setting",
    "play_music",
    "web_search",
    "write_note",
    "control_app",
    "clarify",
    "content_creation"  # ← 新增
]
```

#### 步骤 2：实现内容生成
```python
# app/executor.py

def _execute_content_creation(self, intent: Intent) -> ExecutionResult:
    """生成内容（文章、代码等）"""
    slots = intent.slots

    content_type = slots.get("type", "article")  # article, code, email
    topic = slots.get("topic", "")
    length = slots.get("length", 500)  # 字数

    # 构建生成 prompt
    prompt = self._build_creation_prompt(content_type, topic, length)

    # 调用 LLM 生成
    content = self.llm_client.generate_content(prompt)

    # 保存文件
    if slots.get("save", True):
        file_path = self._save_content(content, content_type, topic)

        # 可选：打开文件
        if slots.get("open", False):
            os.system(f"open {file_path}")

    return ExecutionResult(
        success=True,
        message=f"已生成 {len(content)} 字的{content_type}",
        output=content
    )
```

#### 步骤 3：LLM 内容生成
```python
# app/llm.py

def generate_content(self, prompt: str, max_tokens=2000) -> str:
    """生成长文本内容"""

    message = self.client.messages.create(
        model=self.model,
        max_tokens=max_tokens,  # 增加到 2000
        temperature=0.7,  # 提高创造性
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text
```

**Few-shot 示例**：
```jsonl
{"user": "写一篇 500 字关于 AI 的文章", "assistant": {"intent": "content_creation", "slots": {"type": "article", "topic": "AI", "length": 500, "save": true}}}
{"user": "帮我写一个 Python 排序函数", "assistant": {"intent": "content_creation", "slots": {"type": "code", "topic": "Python排序函数", "language": "python"}}}
```

**工作量**：1-2 天

**验收标准**：
```bash
# 测试命令
python app/main.py run --text "写一篇 500 字关于人工智能的文章"

# 预期结果：
# ✅ 生成约 500 字文章
# ✅ 内容质量良好
# ✅ 保存到文件
# ✅ 返回文件路径
```

---

### 3. 设计文档完善 ⭐⭐⭐⭐

**优先级**：🔴 **高**（议题二要求提交）

**问题**：
- 已有 `DESIGN_DOC.md` 但需要补充实际实现细节
- 需要回答 4 个问题的完整版本

**目标**：
完善设计文档，包含：
1. 功能需求与优先级（已有）
2. 实现挑战与解决方案（已有）
3. LLM 模型选择对比（已有）
4. 未来规划（已有）
5. **补充：实际实现的代码架构图**
6. **补充：测试结果和准确率数据**

**工作量**：0.5 天

---

## 🟡 P1 级：重要功能（提升完整度）

### 4. 文件操作功能 ⭐⭐⭐⭐

**优先级**：🟡 **中高**

**功能**：
- 读取文件
- 写入文件
- 移动/复制文件
- 删除文件（需确认）

**实现**：
```python
# app/executor.py

def _execute_file_operation(self, intent: Intent):
    slots = intent.slots
    action = slots.get("action")  # read, write, move, delete
    path = slots.get("path")

    if action == "read":
        content = Path(path).read_text()
        return ExecutionResult(success=True, output=content)

    elif action == "write":
        content = slots.get("content")
        Path(path).write_text(content)
        return ExecutionResult(success=True, message=f"已写入 {path}")

    # ...
```

**工作量**：1 天

---

### 5. 系统功能扩展 ⭐⭐⭐

**优先级**：🟡 **中**

**新增功能**：
- 调整屏幕亮度
- 截图
- 锁屏
- 静音/取消静音
- 查看电池电量

**实现**：
```applescript
# executor/macos/system.applescript 扩展

-- 亮度控制
on setBrightness(level)
    do shell script "brightness " & level
end setBrightness

-- 截图
on takeScreenshot()
    do shell script "screencapture ~/Desktop/screenshot.png"
end takeScreenshot
```

**工作量**：1-2 天

---

### 6. 应用深度控制 ⭐⭐⭐

**优先级**：🟡 **中**

**功能**：
- 在应用内执行操作（如 Safari 切换标签）
- 控制音乐应用的播放列表
- 管理日历事件
- 发送微信消息

**示例**：
```applescript
# executor/macos/wechat.applescript

on sendMessage(contact, message)
    tell application "WeChat"
        activate
        -- 发送消息逻辑
    end tell
end sendMessage
```

**工作量**：2-3 天

---

## 🟢 P2 级：优化改进（锦上添花）

### 7. Whisper 离线语音识别 ⭐⭐⭐

**优先级**：🟢 **低**

**优点**：
- ✅ 准确率 95%+（比当前 85% 高）
- ✅ 完全离线
- ✅ 更快（本地推理）

**实现**：
```python
# app/asr_whisper.py（已在 ASR_INTEGRATION.md 中详细说明）

pip install faster-whisper
```

**工作量**：1 天

**优先级低的原因**：
- 当前 ASR 已经可用（85-90%）
- 对核心功能影响不大
- 可以后续优化

---

### 8. 对话上下文记忆 ⭐⭐

**优先级**：🟢 **低**

**功能**：
```
用户："搜索 Python 教程"
系统：[执行搜索]

用户："打开第一个"  # ← 需要理解"第一个"指什么
系统：[打开第一个搜索结果]
```

**实现**：
```python
# app/context_manager.py

class ContextManager:
    def __init__(self):
        self.history = []  # 最近 5 轮对话

    def add_turn(self, user_input, intent, result):
        self.history.append({
            "user": user_input,
            "intent": intent,
            "result": result
        })

        # 只保留最近 5 轮
        if len(self.history) > 5:
            self.history.pop(0)

    def get_context(self):
        return self.history
```

**工作量**：2 天

---

### 9. 自定义工作流 ⭐⭐

**优先级**：🟢 **低**

**功能**：
用户定义快捷场景：
```yaml
# workflows/morning_routine.yaml

name: "早上日常"
trigger: "开始工作"
steps:
  - intent: control_app
    slots: {app: "Safari", action: "open"}
  - intent: web_search
    slots: {query: "今天的新闻"}
  - intent: system_setting
    slots: {setting: "volume", value: 30}
  - intent: play_music
    slots: {action: "play"}
```

**工作量**：3 天

---

### 10. 测试覆盖率提升 ⭐

**优先级**：🟢 **低**

**当前**：30 个测试用例

**目标**：
- 增加到 100 个测试用例
- 覆盖更多边缘情况
- 添加集成测试
- 性能测试

**工作量**：2 天

---

## 📊 总体优先级排序

### 按紧急程度

| # | 功能 | 优先级 | 工作量 | 对议题二影响 | 建议顺序 |
|---|------|--------|--------|--------------|----------|
| 1 | **多步骤任务组合** | 🔴 P0 | 2-3 天 | 致命 | ⭐ 第 1 |
| 2 | **内容创作功能** | 🔴 P0 | 1-2 天 | 致命 | ⭐ 第 2 |
| 3 | **设计文档完善** | 🔴 P0 | 0.5 天 | 重要 | ⭐ 第 3 |
| 4 | 文件操作 | 🟡 P1 | 1 天 | 中等 | 第 4 |
| 5 | 系统功能扩展 | 🟡 P1 | 1-2 天 | 低 | 第 5 |
| 6 | 应用深度控制 | 🟡 P1 | 2-3 天 | 低 | 第 6 |
| 7 | Whisper ASR | 🟢 P2 | 1 天 | 无 | 第 7 |
| 8 | 对话上下文 | 🟢 P2 | 2 天 | 无 | 第 8 |
| 9 | 自定义工作流 | 🟢 P2 | 3 天 | 无 | 第 9 |
| 10 | 测试覆盖率 | 🟢 P2 | 2 天 | 无 | 第 10 |

---

## 🎯 推荐开发路线

### 最小可交付版本（4-5 天）

**满足议题二基本要求**

```
Day 1-2：多步骤任务组合（P0）
  - 修改 Schema 支持多步骤
  - 实现 MultiStepExecutor
  - 测试：写文章→保存

Day 2-3：内容创作功能（P0）
  - 添加 content_creation intent
  - 实现文章/代码生成
  - 测试：生成 500 字文章

Day 3-4：集成与测试
  - 集成两个新功能
  - 端到端测试
  - 修复 bug

Day 4-5：文档完善（P0）
  - 更新 DESIGN_DOC.md
  - 添加实现细节
  - 准备演示
```

---

### 完整版本（7-10 天）

**更完善的产品**

```
Day 1-5：最小可交付版本（上述）

Day 6：文件操作（P1）
  - 实现读写文件
  - 测试：生成文章→保存文件

Day 7-8：系统功能扩展（P1）
  - 亮度、截图、静音等
  - 完善系统控制

Day 9-10：优化与文档
  - Whisper 集成（可选）
  - 完善文档
  - 准备交付
```

---

## ✅ 验收标准

### P0 功能（必须）

- [ ] 多步骤任务：能执行"写文章→保存→发邮件"
- [ ] 内容创作：能生成 500 字文章
- [ ] 设计文档：完整回答 4 个问题

### P1 功能（建议）

- [ ] 文件操作：能读写文件
- [ ] 系统扩展：能调整亮度、截图

### P2 功能（可选）

- [ ] Whisper ASR：准确率 95%+
- [ ] 对话上下文：能理解"打开第一个"

---

## 💡 我的建议

### 如果时间充裕（7+ 天）

**按优先级 1-6 依次实现**
- 完整满足议题二要求
- 产品更完善
- 功能更丰富

### 如果时间紧张（4-5 天）

**只实现 P0（1-3）**
- 多步骤组合
- 内容创作
- 完善文档

**理由**：
- ✅ 满足议题二核心要求
- ✅ 有完整的复杂场景演示
- ✅ 有"写文章"功能
- ✅ 有设计文档

### 如果时间极其紧张（2-3 天）

**只实现 P0 的 1-2**
- 多步骤组合
- 内容创作

**在文档中**：
- 说明架构已支持扩展
- 提供详细的实现方案
- 证明设计能力

---

## 📝 下一步行动

### 立即开始（推荐）

```bash
# 1. 创建开发分支
git checkout -b feature/multi-step-content

# 2. 开始实现多步骤组合
# 参考 DESIGN_DOC.md 第三章 3.1 节

# 3. 实现内容创作功能
# 参考上面的实现方案
```

### 或者先讨论

如果你想讨论：
- 具体实现细节
- 时间安排
- 功能取舍

告诉我，我可以帮你：
- 写代码
- 做设计
- 解答疑问

---

## 🎯 总结

### 当前状态：70% 完成

**已有**：
- ✅ 语音识别、TTS、LLM、规则引擎
- ✅ 基础功能（音量、音乐、搜索、笔记、应用）
- ✅ 安全机制

**缺失（致命）**：
- ❌ 多步骤任务组合
- ❌ 内容创作

### 优先级：

1. 🔴 **P0（必须）**：多步骤 + 内容创作 + 文档（4-5 天）
2. 🟡 **P1（重要）**：文件操作 + 系统扩展（2-3 天）
3. 🟢 **P2（可选）**：Whisper + 上下文 + 工作流（5+ 天）

### 建议：

**先完成 P0（4-5 天）→ 满足议题二要求**

然后根据时间决定是否做 P1、P2。

---

**你希望我帮你实现哪个功能？或者有其他问题？** 🚀
