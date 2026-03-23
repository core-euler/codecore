"""Coder role helpers for structured edit generation."""

from __future__ import annotations

import re

from ..context.manager import ContextManager
from ..domain.enums import TaskTag
from ..domain.models import ChatMessage, ChatRequest
from ..execution.editing import EditOperation, EditPlan, StructuredEditParser
from .models import PlannerOutput

AUTOEDIT_SYSTEM_PROMPT = """Return only JSON with exact text replacements.
Schema:
{
  "edits": [
    {
      "path": "relative/path.py",
      "old": "exact existing text",
      "new": "replacement text",
      "reason": "short explanation"
    }
  ]
}
Rules:
- edit only active files provided in context
- each file may appear at most once
- use exact snippets that exist exactly once
- do not include markdown, prose, or code fences unless the entire response is a json code fence
"""

_CHANGE_PATTERNS = (
    re.compile(r'change\s+"([^"]+)"\s+to\s+"([^"]+)"', re.IGNORECASE),
    re.compile(r"change\s+'([^']+)'\s+to\s+'([^']+)'", re.IGNORECASE),
    re.compile(r'replace\s+"([^"]+)"\s+with\s+"([^"]+)"', re.IGNORECASE),
    re.compile(r"replace\s+'([^']+)'\s+with\s+'([^']+)'", re.IGNORECASE),
    re.compile(r"\bchange\s+([A-Za-z0-9_\-./:]+)\s+to\s+([A-Za-z0-9_\-./:]+)", re.IGNORECASE),
    re.compile(r"\breplace\s+([A-Za-z0-9_\-./:]+)\s+with\s+([A-Za-z0-9_\-./:]+)", re.IGNORECASE),
)


class CoderAgent:
    def __init__(self, parser: StructuredEditParser | None = None) -> None:
        self._parser = parser or StructuredEditParser()

    def build_request(
        self,
        *,
        instruction: str,
        plan: PlannerOutput,
        active_files: tuple[str, ...],
        context_manager: ContextManager,
        task_tag: TaskTag,
        model_hint: str | None = None,
    ) -> ChatRequest:
        file_context = context_manager.render_file_context(list(active_files))
        plan_text = "\n".join(f"- {step.title}: {step.detail}" for step in plan.steps)
        prompt = (
            f"Task: {instruction}\n"
            f"Planned steps:\n{plan_text}\n\n"
            f"Active files allowed for editing:\n"
            + "\n".join(f"- {path}" for path in active_files)
            + "\n\nReturn only a structured edit plan in JSON.\n\n"
            + file_context
        )
        return ChatRequest(
            messages=(ChatMessage(role="user", content=prompt),),
            system_prompt=AUTOEDIT_SYSTEM_PROMPT,
            task_tag=task_tag,
            model_hint=model_hint,
            max_output_tokens=1400,
            metadata={"mode": "autoedit", "agent_role": "coder"},
        )

    def plan_edits(
        self,
        *,
        instruction: str,
        active_files: tuple[str, ...],
        context_manager: ContextManager,
        model_response: str,
    ) -> EditPlan:
        try:
            return self._parser.parse(model_response, allowed_paths=active_files)
        except ValueError:
            return self._heuristic_fallback(instruction, active_files, context_manager)

    def _heuristic_fallback(
        self,
        instruction: str,
        active_files: tuple[str, ...],
        context_manager: ContextManager,
    ) -> EditPlan:
        pair = self._extract_change_pair(instruction)
        if pair is None:
            raise ValueError("Model output is invalid and heuristic fallback could not infer a replace operation.")
        old, new = pair
        candidates: list[str] = []
        for path in active_files:
            content = context_manager.read_text(path, truncate=False)
            if content is None:
                continue
            if content.count(old) == 1:
                candidates.append(path)
        if len(candidates) != 1:
            raise ValueError(
                "Model output is invalid and heuristic fallback needs exactly one active file with a unique match."
            )
        return EditPlan(
            edits=(EditOperation(path=candidates[0], old=old, new=new, reason="heuristic fallback from instruction"),),
            raw_response="",
        )

    def _extract_change_pair(self, instruction: str) -> tuple[str, str] | None:
        for pattern in _CHANGE_PATTERNS:
            match = pattern.search(instruction)
            if match:
                return match.group(1), match.group(2)
        return None
