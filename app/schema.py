"""
Intent schema definitions using Pydantic.
All LLM outputs must conform to these models.
"""
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field


IntentName = Literal[
    "system_setting",
    "play_music",
    "web_search",
    "write_note",
    "write_article",  # 文章写作 (Article writing)
    "control_app",
    "file_read",      # 文件读取 (File read)
    "file_write",     # 文件写入 (File write)
    "file_move",      # 文件移动 (File move)
    "file_copy",      # 文件复制 (File copy)
    "file_delete",    # 文件删除 (File delete)
    "file_list",      # 列出文件 (List files)
    "clarify"
]


class Intent(BaseModel):
    """Structured intent output from LLM or rule-based planner."""
    intent: IntentName
    slots: Dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False
    speak_back: str = ""
    safety: Dict[str, Any] = Field(
        default_factory=lambda: {"risk": "low", "reason": ""}
    )

    class Config:
        frozen = False


class Plan(BaseModel):
    """多步骤任务计划 (Multi-step task plan)

    LLM 可输出单个 Intent 或者 Plan (List[Intent])。
    (LLM can output either a single Intent or a Plan containing multiple Intents)
    """
    plan: List[Intent]  # 子任务序列 (subtask sequence)
    summary: str = ""   # 整体摘要，用于日志和 TTS 播报 (overall summary for logging/TTS)


class ExecutionResult(BaseModel):
    """Result from executor."""
    success: bool
    message: str
    output: str = ""
    error: str = ""
    file_path: str = ""  # 文件路径（用于文件操作）
