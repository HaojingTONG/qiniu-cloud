"""
LLM client for Anthropic Claude API.
Only produces JSON output, with retry on failure.
"""
import json
import logging
from typing import Optional

import anthropic
from pydantic import ValidationError

from .config import config
from .schema import Intent
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


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
