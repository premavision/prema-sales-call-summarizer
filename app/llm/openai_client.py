import json
import logging
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from app.llm.base import CallAnalysisResult, CallContext, LLMClient
from app.llm.prompts import ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if OpenAI is None:
            raise ImportError("openai package is required for OpenAILLMClient")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze_call(self, transcript: str, context: CallContext) -> CallAnalysisResult:
        logger.info("Analyzing call %s with OpenAI model %s", context.call.id, self.model)
        payload = {
            "transcript": transcript,
            "call": {
                "title": context.call.title,
                "call_type": context.call.call_type,
                "contact_name": context.call.contact_name,
                "company": context.call.company,
            },
        }
        messages = [
            {"role": "system", "content": ANALYSIS_PROMPT.strip()},
            {
                "role": "user",
                "content": f"Return JSON with keys: summary, pain_points, objections, action_items (list), follow_up_message. Input: {json.dumps(payload)}",
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content  # type: ignore[index]
            data: dict[str, Any] = json.loads(content or "{}")
            
            # Normalize the response - handle cases where LLM returns lists instead of strings
            def normalize_to_string(value: Any) -> str:
                """Convert value to string, handling lists and other types."""
                if value is None:
                    return ""
                if isinstance(value, list):
                    # Join list items with newlines or spaces
                    return "\n".join(str(item) for item in value)
                return str(value)
            
            def normalize_action_items(value: Any) -> list[str]:
                """Ensure action_items is always a list of strings."""
                if value is None:
                    return []
                if isinstance(value, str):
                    # Try to parse if it's a JSON string
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            return [str(item) for item in parsed]
                        return [str(parsed)]
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, treat as single item
                        return [value] if value.strip() else []
                if isinstance(value, list):
                    return [str(item) for item in value]
                return [str(value)]
            
            return CallAnalysisResult(
                summary=normalize_to_string(data.get("summary", "")),
                pain_points=normalize_to_string(data.get("pain_points")),
                objections=normalize_to_string(data.get("objections")),
                action_items=normalize_action_items(data.get("action_items")),
                follow_up_message=normalize_to_string(data.get("follow_up_message")),
                metadata={"provider": "openai", "model": self.model},
            )
        except Exception as e:
            error_msg = str(e)
            # Check for API key errors
            if "api_key" in error_msg.lower() or "401" in error_msg or "invalid" in error_msg.lower():
                logger.error("OpenAI API key error: %s", error_msg)
                raise ValueError(
                    f"Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env file. "
                    f"API keys should start with 'sk-'. Error: {error_msg}"
                )
            # Re-raise other errors as-is
            logger.error("Analysis error: %s", error_msg)
            raise
