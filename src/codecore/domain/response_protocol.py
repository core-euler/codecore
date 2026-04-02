"""Canonical JSON response protocol for model outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


GENERAL_RESPONSE_SCHEMA = """Return exactly one JSON object and nothing else.
Schema:
{
  "type": "final" | "ask" | "tool_call",
  "message": "markdown for the user",
  "requested_action": {
    "kind": "apply_last_prompt",
    "label": "Apply changes"
  },
  "tool_call": {
    "name": "list" | "search" | "read" | "repo_map" | "knowledge_lookup",
    "args": {}
  }
}
Rules:
- Use type=final when you can answer now.
- Use type=ask when you need user confirmation or one missing input.
- Use requested_action only when the UI should offer a concrete follow-up action.
- Use type=tool_call only when you need one built-in repository tool before answering.
- Never emit prose, markdown fences, shell snippets, or explanations outside the JSON object.
"""


AUTOEDIT_RESPONSE_SCHEMA = """Return exactly one JSON object and nothing else.
Schema:
{
  "type": "edit_plan",
  "message": "one short summary of intended edits",
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
- never emit prose, markdown fences, or any text outside the JSON object
"""


@dataclass(slots=True, frozen=True)
class RequestedAction:
    kind: str
    label: str | None = None


@dataclass(slots=True, frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ModelResponseEnvelope:
    response_type: str
    message: str = ""
    requested_action: RequestedAction | None = None
    tool_call: ToolCall | None = None
    edits: tuple[dict[str, Any], ...] = ()
    raw_payload: dict[str, Any] = field(default_factory=dict)


class ModelResponseParser:
    def parse(
        self,
        text: str,
        *,
        allowed_types: tuple[str, ...],
    ) -> ModelResponseEnvelope:
        payload = self._normalize_payload(self._load_payload(text))
        response_type = payload.get("type")
        if not isinstance(response_type, str) or response_type not in allowed_types:
            allowed = ", ".join(allowed_types)
            raise ValueError(f"Model response must include type in {{{allowed}}}.")

        message = payload.get("message", "")
        if message is None:
            message = ""
        if not isinstance(message, str):
            raise ValueError("Model response field 'message' must be a string.")

        requested_action = None
        requested_action_payload = payload.get("requested_action")
        if requested_action_payload is not None:
            if not isinstance(requested_action_payload, dict):
                raise ValueError("Model response field 'requested_action' must be an object.")
            kind = requested_action_payload.get("kind")
            label = requested_action_payload.get("label")
            if not isinstance(kind, str) or not kind:
                raise ValueError("Model response requested_action.kind must be a non-empty string.")
            if label is not None and not isinstance(label, str):
                raise ValueError("Model response requested_action.label must be a string when present.")
            requested_action = RequestedAction(kind=kind, label=label)

        tool_call = None
        tool_call_payload = payload.get("tool_call")
        if tool_call_payload is not None:
            if not isinstance(tool_call_payload, dict):
                raise ValueError("Model response field 'tool_call' must be an object.")
            name = tool_call_payload.get("name")
            args = tool_call_payload.get("args", {})
            if not isinstance(name, str) or not name:
                raise ValueError("Model response tool_call.name must be a non-empty string.")
            if not isinstance(args, dict):
                raise ValueError("Model response tool_call.args must be an object.")
            tool_call = ToolCall(name=name, args=args)

        edits_payload = payload.get("edits", ())
        if edits_payload == ():
            edits: tuple[dict[str, Any], ...] = ()
        else:
            if not isinstance(edits_payload, list):
                raise ValueError("Model response field 'edits' must be a list.")
            edits = tuple(item for item in edits_payload if isinstance(item, dict))
            if len(edits) != len(edits_payload):
                raise ValueError("Model response 'edits' items must be objects.")

        return ModelResponseEnvelope(
            response_type=response_type,
            message=message.strip(),
            requested_action=requested_action,
            tool_call=tool_call,
            edits=edits,
            raw_payload=payload,
        )

    def _load_payload(self, text: str) -> dict[str, Any]:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) < 3:
                raise ValueError("Model response is wrapped in an incomplete code fence.")
            candidate = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Model response is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Model response must be a JSON object.")
        return payload

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "type" in payload:
            return payload
        action = payload.get("action")
        if action == "answer":
            return {"type": "final", "message": payload.get("answer", "")}
        if action == "tool":
            return {
                "type": "tool_call",
                "message": payload.get("message", ""),
                "tool_call": {
                    "name": payload.get("tool"),
                    "args": payload.get("args", {}),
                },
            }
        if "edits" in payload:
            normalized = dict(payload)
            normalized["type"] = "edit_plan"
            normalized.setdefault("message", "")
            return normalized
        return payload
