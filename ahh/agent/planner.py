"""LLM Planner - calls Anthropic Claude to produce a structured plan."""
import os
import json
import logging
from anthropic import Anthropic

from .schema import PlanResponse, PLAN_SCHEMA_DESCRIPTION

log = logging.getLogger("ahh")


class Planner:
    """Plans task execution using Anthropic Claude API."""

    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.model = "claude-haiku-4-5-20251001"

    def plan(self, user_request: str, context: str = "") -> PlanResponse:
        """Generate a plan for the user's request.

        Args:
            user_request: What the user wants to do.
            context: Optional context (e.g., clarification answers).

        Returns:
            PlanResponse with clarify/steps/actions.
        """
        system_prompt = f"""You are a warm, patient, and friendly teaching assistant helping someone learn to use their computer. You speak like a kind friend — not a robot.

You plan browser tasks step by step and control a real browser via Playwright.

{PLAN_SCHEMA_DESCRIPTION}

Important:
- Use real URLs and CSS selectors.
- For search tasks, use Google (https://www.google.com).
- Keep plans simple with 3-7 steps max.
- The "teach" field is READ ALOUD as a voice overview for the step. Keep it to 1 short sentence.
- The "narrate" field on EVERY action is READ ALOUD while a pointing hand shows the user exactly where to look. Be specific and visual: reference what the user sees on screen ("See this search bar at the top?", "Right here is where we type", "Look, these results just popped up!"). Make it feel like a friend is sitting next to them pointing at their screen. Keep each narrate to 1 short sentence.
- Output ONLY valid JSON. No markdown fences, no explanation text.
"""

        user_msg = f"User request: {user_request}"
        if context:
            user_msg += f"\n\nAdditional context: {context}"

        # Try up to 2 times for valid JSON
        for attempt in range(2):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_msg}],
                )

                text = response.content[0].text.strip()

                # Strip markdown fences if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                    text = text.strip()

                plan = PlanResponse.model_validate_json(text)
                return plan

            except Exception as e:
                log.error(f"Planner attempt {attempt + 1} failed: {e}")
                err_str = str(e).lower()
                # If rate limited, don't retry
                if "429" in err_str or "rate_limit" in err_str or "rate limit" in err_str:
                    raise RuntimeError("API rate limited. Wait a moment and try again.") from e
                # If auth error, don't retry
                if "401" in err_str or "authentication" in err_str or "invalid" in err_str:
                    raise RuntimeError("Invalid API key. Check your ANTHROPIC_API_KEY in .env") from e
                if "403" in err_str or "permission" in err_str:
                    raise RuntimeError("API permission denied. Check your ANTHROPIC_API_KEY.") from e
                if attempt == 0:
                    user_msg = (
                        f"Your previous response was not valid JSON. Error: {e}\n"
                        f"Please output ONLY valid JSON matching the schema.\n"
                        f"Original request: {user_request}"
                    )
                    if context:
                        user_msg += f"\nContext: {context}"

        # Fallback: return empty plan
        log.warning("Failed to get valid plan after retries")
        return PlanResponse(clarify=[], steps=[], actions=[])

    def replan_with_answer(self, user_request: str, question: str, answer: str) -> PlanResponse:
        """Re-plan after user answered a clarification question."""
        context = f"The user was asked: '{question}' and answered: '{answer}'"
        return self.plan(user_request, context)
