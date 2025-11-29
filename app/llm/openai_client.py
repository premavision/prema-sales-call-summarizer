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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content  # type: ignore[index]
        data: dict[str, Any] = json.loads(content or "{}")
        return CallAnalysisResult(
            summary=data.get("summary", ""),
            pain_points=data.get("pain_points"),
            objections=data.get("objections"),
            action_items=data.get("action_items") or [],
            follow_up_message=data.get("follow_up_message"),
            metadata={"provider": "openai", "model": self.model},
        )
