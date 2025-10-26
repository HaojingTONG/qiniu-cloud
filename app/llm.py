"""
LLM client for Anthropic Claude API.
Only produces JSON output, with retry on failure.
支持单步 Intent 和多步 Plan。(Supports single-step Intent and multi-step Plan)
"""
import json
import logging
from typing import Optional, Union

import anthropic
from pydantic import ValidationError

from .config import config
from .schema import Intent, Plan
from .utils import logger


class LLMClient:
    """Anthropic Claude API client for intent parsing."""

    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.CLAUDE_MODEL
        self.temperature = config.LLM_TEMPERATURE
        self.max_tokens = config.LLM_MAX_TOKENS

    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        prompt_path = config.PROMPTS_DIR / "system.txt"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
        return self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file doesn't exist."""
        return """You are a Command Planner for a macOS voice assistant.

Your ONLY job is to output valid JSON with this exact structure:
{
  "intent": "system_setting|play_music|web_search|write_note|control_app|clarify",
  "slots": {},
  "confirm": false,
  "speak_back": "",
  "safety": {"risk": "low|medium|high", "reason": ""}
}

Rules:
1. Output ONLY minified JSON, no markdown, no prose, no explanations
2. If user request is unsafe/ambiguous → intent="clarify", confirm=true, brief speak_back
3. For dangerous operations (delete/format/shutdown) → safety.risk="high"
4. speak_back should be brief (< 20 words) in user's language
5. slots contain extracted parameters as key-value pairs"""

    def _load_fewshot_examples(self) -> str:
        """Load few-shot examples from JSONL file."""
        fewshot_path = config.PROMPTS_DIR / "fewshot.jsonl"
        if not fewshot_path.exists():
            return ""

        examples = []
        try:
            with open(fewshot_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        examples.append(json.loads(line))
        except Exception as e:
            logger.warning(f"Failed to load few-shot examples: {e}")
            return ""

        if not examples:
            return ""

        # Format as user/assistant pairs
        formatted = "\n\nExamples:\n"
        for ex in examples:
            formatted += f"\nUser: {ex.get('user', '')}\n"
            formatted += f"Assistant: {json.dumps(ex.get('assistant', {}), ensure_ascii=False)}\n"

        return formatted

    def call_llm_to_intent(self, text: str) -> Intent:
        """
        Call LLM to parse user text into Intent.

        Args:
            text: User utterance

        Returns:
            Intent object

        Raises:
            ValueError: If all retries fail
        """
        system_prompt = self._load_system_prompt()
        fewshot = self._load_fewshot_examples()

        user_message = f"{fewshot}\n\nNow parse this user request:\nUser: {text}\n\nOutput only JSON:"

        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                logger.info(f"LLM call attempt {attempt + 1}/{config.LLM_MAX_RETRIES}")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                )

                # Extract text content
                response_text = ""
                for block in message.content:
                    if block.type == "text":
                        response_text += block.text

                logger.debug(f"LLM response: {response_text}")

                # Try to parse JSON
                parsed = self._extract_json(response_text)
                if parsed:
                    # Validate with Pydantic
                    intent = Intent(**parsed)
                    logger.info(f"Successfully parsed intent: {intent.intent}")
                    return intent

                # If first attempt failed, retry with correction prompt
                if attempt == 0:
                    user_message = f"The previous output was invalid. Please output ONLY valid JSON matching the schema. User request: {text}"
                    continue

            except ValidationError as e:
                logger.error(f"Pydantic validation failed: {e}")
            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        # All retries failed, return clarify intent
        logger.warning("All LLM retries failed, returning clarify intent")
        return Intent(
            intent="clarify",
            confirm=True,
            speak_back="抱歉，我没理解您的意思，能再说一遍吗？",
            safety={"risk": "low", "reason": "LLM parsing failed"}
        )

    def call_llm_to_plan(self, text: str) -> Union[Intent, Plan]:
        """
        调用 LLM 解析用户输入，返回单步 Intent 或多步 Plan。
        (Call LLM to parse user text into either Intent or Plan)

        Args:
            text: User utterance

        Returns:
            Union[Intent, Plan]: Either a single Intent or a Plan with multiple Intents

        Raises:
            ValueError: If all retries fail
        """
        system_prompt = self._load_plan_system_prompt()
        fewshot = self._load_fewshot_examples()

        user_message = f"{fewshot}\n\nNow parse this user request:\nUser: {text}\n\nOutput only JSON:"

        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                logger.info(f"LLM plan call attempt {attempt + 1}/{config.LLM_MAX_RETRIES}")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                )

                # Extract text content
                response_text = ""
                for block in message.content:
                    if block.type == "text":
                        response_text += block.text

                logger.debug(f"LLM response: {response_text}")

                # Try to parse JSON
                parsed = self._extract_json(response_text)
                if parsed:
                    # Try Plan first (has "plan" key), then Intent
                    if "plan" in parsed:
                        try:
                            plan = Plan(**parsed)
                            logger.info(f"Successfully parsed Plan with {len(plan.plan)} steps")
                            return plan
                        except ValidationError as e:
                            logger.error(f"Plan validation failed: {e}")
                    else:
                        try:
                            intent = Intent(**parsed)
                            logger.info(f"Successfully parsed single Intent: {intent.intent}")
                            return intent
                        except ValidationError as e:
                            logger.error(f"Intent validation failed: {e}")

                # If first attempt failed, retry with correction prompt
                if attempt == 0:
                    user_message = f"The previous output was invalid. Please output ONLY valid JSON matching the schema. User request: {text}"
                    continue

            except Exception as e:
                logger.error(f"LLM call failed: {e}")

        # All retries failed, return clarify intent
        logger.warning("All LLM retries failed, returning clarify intent")
        return Intent(
            intent="clarify",
            confirm=True,
            speak_back="抱歉，我没理解您的意思，能再说一遍吗？",
            safety={"risk": "low", "reason": "LLM parsing failed"}
        )

    def _load_plan_system_prompt(self) -> str:
        """
        加载支持多步骤规划的 system prompt。
        (Load system prompt that supports multi-step planning)
        """
        prompt_path = config.PROMPTS_DIR / "system_plan.txt"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()

        # Fallback to default multi-step prompt
        return """You are a Command Planner for a macOS voice assistant.

Your job is to parse user requests and output valid JSON.

For SINGLE-STEP tasks, output:
{
  "intent": "system_setting|play_music|web_search|write_note|control_app|clarify",
  "slots": {},
  "confirm": false,
  "speak_back": "",
  "safety": {"risk": "low|medium|high", "reason": ""}
}

For MULTI-STEP tasks (e.g., "open Safari then search Python tutorial, then set volume to 30%"), output:
{
  "plan": [
    {"intent": "...", "slots": {...}, "confirm": false, "speak_back": "...", "safety": {...}},
    {"intent": "...", "slots": {...}, "confirm": false, "speak_back": "...", "safety": {...}}
  ],
  "summary": "Brief description of the plan"
}

Rules:
1. Output ONLY minified JSON, no markdown, no prose, no explanations
2. For multi-step: detect keywords like "然后|接着|之后|再|，" (then, next, after, again, comma)
3. Each step in "plan" must be a valid Intent object
4. If any step is unsafe/ambiguous → that step has confirm=true, safety.risk="high"
5. speak_back should be brief (< 20 words) in user's language
6. summary explains the overall plan in one sentence"""

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from response text."""
        # Remove markdown code blocks
        text = text.strip()
        if text.startswith("```"):
            # Find the JSON content between ```
            lines = text.split("\n")
            json_lines = []
            in_code = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code or not line.strip().startswith("```"):
                    json_lines.append(line)
            text = "\n".join(json_lines)

        # Try to parse
        try:
            # Find JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")

        return None

    def generate_article(
        self,
        topic: str,
        tone: str = "informative",
        length: int = 1000
    ) -> dict:
        """
        生成完整文章（标题、引言、主体、结论）。
        (Generate a complete article with title, introduction, body, conclusion)

        Args:
            topic: 文章主题 (Article topic)
            tone: 语气风格 (Tone: informative, personal, academic, casual)
            length: 目标字数 (Target word count)

        Returns:
            dict: {
                "title": "文章标题",
                "content": "完整Markdown内容",
                "summary": "一句话摘要"
            }
        """
        logger.info(f"Generating article on topic: {topic}, tone: {tone}, length: {length}")

        # 构建 prompt (Build prompt)
        system_prompt = """你是一名专业的文章作者，擅长撰写结构清晰、内容丰富的文章。
你的任务是根据用户提供的主题，创作一篇完整的文章。

You are a professional article writer skilled at creating well-structured, informative articles.
Your task is to write a complete article based on the user's topic."""

        user_prompt = f"""请根据以下要求写一篇完整的文章：

**主题 (Topic)**: {topic}
**语气 (Tone)**: {tone}
**目标长度 (Target Length)**: 约 {length} 字 (around {length} characters)

**要求 (Requirements)**:
1. 使用 Markdown 格式
2. 包含以下结构：
   - 标题 (# Title)
   - 引言 (Introduction) - 简要介绍主题背景和重要性
   - 主体内容 (Body) - 2-3个小节，深入探讨主题
   - 总结 (Conclusion) - 概括要点和展望未来
3. 语言流畅，逻辑清晰
4. 内容原创，有深度

请直接输出 Markdown 格式的完整文章，不要包含任何解释性文字。"""

        try:
            # 调用 Claude API (Call Claude API)
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # 文章需要更多 tokens (Articles need more tokens)
                temperature=0.7,  # 创作性任务提高温度 (Higher temperature for creative tasks)
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # 提取文章内容 (Extract article content)
            article_text = ""
            for block in message.content:
                if block.type == "text":
                    article_text += block.text

            logger.debug(f"Generated article length: {len(article_text)} chars")

            # 解析标题 (Parse title)
            title = "未命名文章"
            title_match = article_text.split("\n")[0]
            if title_match.startswith("#"):
                title = title_match.strip("# ").strip()

            # 生成摘要 (Generate summary)
            # 提取第一段作为摘要 (Use first paragraph as summary)
            lines = article_text.split("\n")
            summary_lines = []
            for line in lines[1:]:  # Skip title
                line = line.strip()
                if line and not line.startswith("#"):
                    summary_lines.append(line)
                    if len(summary_lines) >= 2:  # 取前两个非标题段落 (Take first 2 non-title paragraphs)
                        break

            summary = " ".join(summary_lines)[:200] + "..." if summary_lines else "文章已生成"

            result = {
                "title": title,
                "content": article_text,
                "summary": summary
            }

            logger.info(f"Article generated successfully: {title}")
            return result

        except Exception as e:
            logger.error(f"Article generation failed: {e}")
            # 返回错误文章 (Return error article)
            return {
                "title": f"关于{topic}的文章",
                "content": f"# 关于{topic}的文章\n\n抱歉，文章生成失败。请稍后重试。\n\n错误信息：{str(e)}",
                "summary": "文章生成失败"
            }


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
