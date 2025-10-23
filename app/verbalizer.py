"""
Verbalizer generates natural language responses for TTS.
Converts intent execution results into user-friendly speech.
"""
from typing import Dict, Any

from .schema import Intent, ExecutionResult


class Verbalizer:
    """Generate natural language responses from intents and results."""

    def generate_confirmation(self, intent: Intent) -> str:
        """
        Generate confirmation message before execution.

        Args:
            intent: Intent to confirm

        Returns:
            Confirmation text
        """
        # Use speak_back from intent if available
        if intent.speak_back:
            return intent.speak_back

        # Generate default confirmation
        intent_name = intent.intent
        slots = intent.slots

        if intent_name == "system_setting":
            setting = slots.get("setting", "设置")
            value = slots.get("value", "")
            return f"好的，正在调整{setting}到{value}"

        elif intent_name == "play_music":
            action = slots.get("action", "播放")
            query = slots.get("query", "音乐")
            return f"好的，{action}{query}"

        elif intent_name == "web_search":
            query = slots.get("query", "内容")
            return f"好的，帮您搜索{query}"

        elif intent_name == "write_note":
            title = slots.get("title", "笔记")
            return f"好的，正在创建笔记：{title}"

        elif intent_name == "control_app":
            app = slots.get("app", "应用")
            action = slots.get("action", "打开")
            return f"好的，{action}{app}"

        elif intent_name == "clarify":
            return intent.speak_back or "抱歉，我没理解您的意思"

        return "好的，正在执行"

    def generate_result_message(self, intent: Intent, result: ExecutionResult) -> str:
        """
        Generate result message after execution.

        Args:
            intent: Executed intent
            result: Execution result

        Returns:
            Result text for TTS
        """
        if result.success:
            return self._success_message(intent, result)
        else:
            return self._error_message(intent, result)

    def _success_message(self, intent: Intent, result: ExecutionResult) -> str:
        """Generate success message."""
        intent_name = intent.intent

        if intent_name == "system_setting":
            return "设置已完成"

        elif intent_name == "play_music":
            return "已为您播放"

        elif intent_name == "web_search":
            return "已打开搜索结果"

        elif intent_name == "write_note":
            return "笔记已创建"

        elif intent_name == "control_app":
            return "操作已完成"

        return "操作成功"

    def _error_message(self, intent: Intent, result: ExecutionResult) -> str:
        """Generate error message."""
        error = result.error or result.message
        return f"抱歉，操作失败了：{error}"

    def generate_dry_run_message(self, intent: Intent) -> str:
        """
        Generate dry-run message (what would be executed).

        Args:
            intent: Intent to describe

        Returns:
            Description text
        """
        return f"[DRY RUN] 将执行：{intent.intent}，参数：{intent.slots}"


def create_verbalizer() -> Verbalizer:
    """Factory function to create verbalizer."""
    return Verbalizer()
