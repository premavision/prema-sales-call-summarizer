import logging

from app.llm.base import CallAnalysisResult, CallContext, LLMClient

logger = logging.getLogger(__name__)


class StubLLMClient(LLMClient):
    def analyze_call(self, transcript: str, context: CallContext) -> CallAnalysisResult:
        logger.info("Stub analyzing call %s", context.call.id)
        summary = (
            "Call covered product fit, pricing expectations, deployment timeline, and next steps."
        )
        pain_points = "Needs faster onboarding and clearer pricing."
        objections = "Concern about integration effort."
        action_items = [
            "Send pricing proposal with tier comparison",
            "Share onboarding playbook",
            "Schedule technical validation call",
        ]
        follow_up = (
            "Thanks for the call today. Here's a recap and proposed next steps: "
            "1) pricing proposal, 2) onboarding plan, 3) technical session scheduling."
        )
        return CallAnalysisResult(
            summary=summary,
            pain_points=pain_points,
            objections=objections,
            action_items=action_items,
            follow_up_message=follow_up,
            metadata={"mode": "stub"},
        )
