"""
Configuration management using python-dotenv.
Reads .env file and provides default values.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


class Config:
    """Global configuration."""

    # Anthropic API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv(
        "CLAUDE_MODEL",
        "claude-3-5-sonnet-20241022"
    )

    # Language
    LANG: str = os.getenv("LANG", "zh")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Safety
    CONFIRM_DANGEROUS: bool = os.getenv("CONFIRM_DANGEROUS", "true").lower() == "true"

    # LLM settings
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # ASR settings
    ASR_ENGINE: str = os.getenv("ASR_ENGINE", "macos")  # macos, text, whisper
    ASR_LANGUAGE: str = os.getenv("ASR_LANGUAGE", "zh-CN")  # zh-CN, en-US
    ASR_TIMEOUT: int = int(os.getenv("ASR_TIMEOUT", "5"))
    ASR_PHRASE_LIMIT: int = int(os.getenv("ASR_PHRASE_LIMIT", "10"))

    # Paths
    PROJECT_ROOT: Path = project_root
    PROMPTS_DIR: Path = project_root / "prompts"
    EXECUTOR_DIR: Path = project_root / "executor"

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.ANTHROPIC_API_KEY:
            return False
        return True


config = Config()
