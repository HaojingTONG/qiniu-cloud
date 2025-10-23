"""
Intent schema definitions using Pydantic.
All LLM outputs must conform to these models.
"""
from typing import Any, Dict, Literal
from pydantic import BaseModel, Field


IntentName = Literal[
    "system_setting",
    "play_music",
    "web_search",
    "write_note",
    "control_app",
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


class ExecutionResult(BaseModel):
    """Result from executor."""
    success: bool
    message: str
    output: str = ""
    error: str = ""
