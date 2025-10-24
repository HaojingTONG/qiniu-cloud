"""
Planner orchestrates intent recognition.
Priority: LLM → rule-based fallback on failure.
支持单步 Intent 和多步 Plan。(Supports single-step Intent and multi-step Plan)
"""
import logging
import re
from typing import Optional, Union

from .config import config
from .schema import Intent, Plan
from .llm import get_llm_client
from .utils import logger


class Planner:
    """Intent planning with LLM and rule-based fallback."""

    # Rule-based keyword mapping
    INTENT_KEYWORDS = {
        "system_setting": [
            r"音量|声音|volume",
            r"亮度|brightness",
            r"截图|screenshot",
            r"静音|mute"
        ],
        "play_music": [
            r"播放|play",
            r"暂停|pause",
            r"音乐|歌曲|music|song",
            r"下一首|上一首|next|previous"
        ],
        "web_search": [
            r"搜索|查找|search|google|百度",
            r"找一下|查一下"
        ],
        "write_note": [
            r"记录|笔记|备忘|note|memo",
            r"写下|记下"
        ],
        "control_app": [
            r"打开.*应用|打开.*app|open.*app",
            r"启动|关闭|quit",
            r"safari|chrome|微信|wechat"
        ]
    }

    # Dangerous keywords requiring confirmation
    DANGEROUS_KEYWORDS = [
        r"删除|delete|remove",
        r"清空|清除|clear|clean",
        r"格式化|format",
        r"关闭.*网络|断网|disconnect",
        r"重启|关机|shutdown|restart",
        r"卸载|uninstall"
    ]

    def __init__(self, use_llm: bool = True):
        """
        Initialize planner.

        Args:
            use_llm: Whether to use LLM (False for testing)
        """
        self.use_llm = use_llm
        self.llm_client = get_llm_client() if use_llm else None

    def plan(self, text: str, dry_run: bool = False) -> Intent:
        """
        Plan intent from user text.

        Args:
            text: User utterance
            dry_run: If True, skip actual LLM call

        Returns:
            Intent object
        """
        logger.info(f"Planning for text: {text}")

        # Try LLM first
        if self.use_llm and not dry_run:
            try:
                intent = self.llm_client.call_llm_to_intent(text)
                logger.info(f"LLM returned intent: {intent.intent}")

                # Enhance safety check
                intent = self._enhance_safety(intent, text)
                return intent
            except Exception as e:
                logger.error(f"LLM planning failed: {e}, falling back to rules")

        # Fallback to rule-based
        return self._rule_based_plan(text)

    def parse_plan_or_intent(self, text: str, dry_run: bool = False) -> Union[Intent, Plan]:
        """
        解析用户输入，返回单步 Intent 或多步 Plan。
        (Parse user input and return either a single Intent or a multi-step Plan)

        策略：LLM 判断是否为多步任务，输出 Intent 或 Plan。
        (Strategy: LLM determines if it's multi-step and outputs Intent or Plan)

        Args:
            text: User utterance
            dry_run: If True, skip actual LLM call

        Returns:
            Union[Intent, Plan]: Either a single Intent or a Plan with multiple Intents
        """
        logger.info(f"Parsing plan or intent for text: {text}")

        # Try LLM first
        if self.use_llm and not dry_run:
            try:
                result = self.llm_client.call_llm_to_plan(text)

                # Check if result is Plan or Intent
                if isinstance(result, Plan):
                    logger.info(f"LLM returned Plan with {len(result.plan)} steps")
                    # Enhance safety check for each intent in plan
                    for i, intent in enumerate(result.plan):
                        result.plan[i] = self._enhance_safety(intent, text)
                    return result
                else:
                    logger.info(f"LLM returned single Intent: {result.intent}")
                    result = self._enhance_safety(result, text)
                    return result

            except Exception as e:
                logger.error(f"LLM planning failed: {e}, falling back to single intent")

        # Fallback: check if text contains multi-step indicators
        if self._is_multi_step_text(text):
            # Split by common delimiters and create Plan
            intents = self._split_to_intents(text)
            if len(intents) > 1:
                return Plan(
                    plan=intents,
                    summary=f"执行{len(intents)}个任务"
                )

        # Default to single intent
        return self._rule_based_plan(text)

    def _is_multi_step_text(self, text: str) -> bool:
        """
        检测文本是否包含多步骤指示词。
        (Detect if text contains multi-step indicators)
        """
        multi_step_keywords = [
            r"然后|接着|之后|再|完成后",  # then, next, after, again
            r"，.{3,}，",  # Multiple clauses separated by commas
            r"。.{3,}。",  # Multiple sentences
            r"接下来|下一步|最后",  # next, next step, finally
        ]

        for pattern in multi_step_keywords:
            if re.search(pattern, text):
                logger.info(f"Multi-step indicator detected: {pattern}")
                return True
        return False

    def _split_to_intents(self, text: str) -> list[Intent]:
        """
        简单拆分多步任务为单步 Intent 列表（规则引擎回退逻辑）。
        (Simple splitting of multi-step task into list of Intents - rule engine fallback)
        """
        # Split by common delimiters
        parts = re.split(r'[，。、]|然后|接着|之后|再|接下来', text)
        intents = []

        for part in parts:
            part = part.strip()
            if len(part) > 2:  # Skip very short parts
                try:
                    intent = self._rule_based_plan(part)
                    if intent.intent != "clarify":  # Only add valid intents
                        intents.append(intent)
                except Exception as e:
                    logger.warning(f"Failed to parse part '{part}': {e}")
                    continue

        return intents if intents else [self._rule_based_plan(text)]

    def _rule_based_plan(self, text: str) -> Intent:
        """
        Rule-based intent recognition as fallback.

        Args:
            text: User utterance

        Returns:
            Intent object
        """
        logger.info("Using rule-based planning")

        text_lower = text.lower()

        # Check dangerous keywords first
        is_dangerous = self._check_dangerous(text)
        if is_dangerous:
            return Intent(
                intent="clarify",
                confirm=True,
                speak_back=f"您确定要执行「{text}」吗？这可能有风险。",
                safety={"risk": "high", "reason": "Dangerous operation detected"}
            )

        # Match intent by keywords
        for intent_name, patterns in self.INTENT_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    slots = self._extract_slots(text, intent_name)
                    return Intent(
                        intent=intent_name,
                        slots=slots,
                        confirm=False,
                        speak_back=f"好的，{self._get_confirmation_text(intent_name, slots)}",
                        safety={"risk": "low", "reason": ""}
                    )

        # No match, return clarify
        return Intent(
            intent="clarify",
            confirm=True,
            speak_back="抱歉，我不太理解您的意思，能具体说说吗？",
            safety={"risk": "low", "reason": "No matching intent"}
        )

    def _check_dangerous(self, text: str) -> bool:
        """Check if text contains dangerous keywords."""
        text_lower = text.lower()
        for pattern in self.DANGEROUS_KEYWORDS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _enhance_safety(self, intent: Intent, text: str) -> Intent:
        """Enhance safety check on LLM-generated intent."""
        if self._check_dangerous(text) and intent.safety.get("risk") == "low":
            intent.safety["risk"] = "high"
            intent.safety["reason"] = "Dangerous keyword detected"
            if config.CONFIRM_DANGEROUS:
                intent.confirm = True
        return intent

    def _extract_slots(self, text: str, intent: str) -> dict:
        """Extract slots from text based on intent."""
        slots = {}

        if intent == "system_setting":
            # Extract volume percentage
            volume_match = re.search(r'(\d+)\s*%|音量.*?(\d+)', text)
            if volume_match:
                volume = volume_match.group(1) or volume_match.group(2)
                slots["setting"] = "volume"
                slots["value"] = int(volume)

        elif intent == "web_search":
            # Extract query after search keyword
            query_match = re.search(r'(?:搜索|查找|search)\s*(.+)', text, re.IGNORECASE)
            if query_match:
                slots["query"] = query_match.group(1).strip()
            else:
                slots["query"] = text

        elif intent == "write_note":
            # Try to extract title and body
            note_match = re.search(r'(?:记录|笔记|note)\s*[:：]?\s*(.+)', text, re.IGNORECASE)
            if note_match:
                content = note_match.group(1).strip()
                slots["title"] = content[:20]  # First 20 chars as title
                slots["body"] = content
            else:
                slots["title"] = "Quick Note"
                slots["body"] = text

        elif intent == "control_app":
            # Extract app name and action
            open_match = re.search(r'打开\s*(\w+)', text)
            if open_match:
                slots["app"] = open_match.group(1)
                slots["action"] = "open"

        return slots

    def _get_confirmation_text(self, intent: str, slots: dict) -> str:
        """Generate confirmation text for intent."""
        if intent == "system_setting":
            if slots.get("setting") == "volume":
                return f"把音量调到{slots.get('value')}%"
        elif intent == "web_search":
            return f"搜索{slots.get('query', '内容')}"
        elif intent == "write_note":
            return f"创建笔记"
        elif intent == "control_app":
            return f"{slots.get('action', '操作')}{slots.get('app', '应用')}"

        return "执行操作"


def create_planner(use_llm: bool = True) -> Planner:
    """Factory function to create planner."""
    return Planner(use_llm=use_llm)
