"""JSON schema for the LLM planner output."""
from pydantic import BaseModel, Field
from typing import Optional


class ClarifyItem(BaseModel):
    question: str = Field(description="Question to ask the user")
    choices: list[str] = Field(description="2-3 choices for the user", min_length=2, max_length=3)


class Step(BaseModel):
    id: int = Field(description="Step number")
    title: str = Field(description="Short title for the step")
    teach: str = Field(description="One sentence explanation of what this step does and why")


class Action(BaseModel):
    step_id: int = Field(description="Which step this action belongs to")
    type: str = Field(description="Action type: navigate, click, type, scroll, wait, read")
    params: dict = Field(default_factory=dict, description="Action parameters")
    narrate: str = Field(default="", description="Short friendly narration for this specific action, spoken aloud while pointing")


class PlanResponse(BaseModel):
    clarify: list[ClarifyItem] = Field(default_factory=list,
        description="0-1 questions needing user clarification before proceeding",
        max_length=1)
    steps: list[Step] = Field(default_factory=list,
        description="Ordered list of steps in the plan")
    actions: list[Action] = Field(default_factory=list,
        description="Ordered list of actions to execute")


PLAN_SCHEMA_DESCRIPTION = """
You must output STRICT JSON matching this schema (no markdown, no extra text):

{
  "clarify": [
    {"question": "...", "choices": ["A", "B", "C"]}
  ],
  "steps": [
    {"id": 1, "title": "...", "teach": "..."}
  ],
  "actions": [
    {"step_id": 1, "type": "navigate", "params": {"url": "https://..."}, "narrate": "Let's open up this website first."},
    {"step_id": 1, "type": "click", "params": {"selector": "CSS selector", "description": "what to click"}, "narrate": "See this button right here? Let's click on it."},
    {"step_id": 1, "type": "type", "params": {"selector": "CSS selector", "text": "text to type"}, "narrate": "Now I'll type in what we're looking for right here in this box."},
    {"step_id": 2, "type": "wait", "params": {"seconds": 2}, "narrate": "Let's give it a moment to load."},
    {"step_id": 2, "type": "scroll", "params": {"direction": "down", "amount": 300}, "narrate": "Let me scroll down so we can see more."},
    {"step_id": 2, "type": "read", "params": {"selector": "CSS selector", "purpose": "read the result"}, "narrate": "Take a look at this part right here — this is what we were looking for."}
  ]
}

Rules:
- Almost ALWAYS proceed with a plan. Make reasonable assumptions instead of asking. Only use "clarify" (max 1 question) if the request is truly ambiguous and you cannot guess what the user wants at all.
- If you can proceed, leave "clarify" empty and fill steps + actions.
- Action types: navigate, click, type, scroll, wait, read
- For "navigate": params must have "url"
- For "click": params must have "selector" (CSS) and "description"
- For "type": params must have "selector" (CSS) and "text"
- For "scroll": params must have "direction" (up/down) and "amount" (pixels)
- For "wait": params must have "seconds"
- For "read": params must have "selector" and "purpose"
- Each step should have a clear "teach" explaining WHAT you're doing and WHY.
- Every action MUST have a "narrate" field — a short, friendly sentence spoken aloud while pointing at the element. Be specific about what the user is seeing: "See this search bar at the top?", "This is the login button over here", "Look at these results that came up". Make the user feel guided, like a friend is showing them around the screen.
- Keep it simple. Use common CSS selectors. Prefer input[name=...], button, a, etc.
- For Google search: navigate to google.com, type in textarea[name="q"], then click input[name="btnK"] or press Enter.
"""
