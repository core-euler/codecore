"""Structured model-generated edit plans."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EditOperation:
    path: str
    old: str
    new: str
    reason: str = ""


@dataclass(slots=True, frozen=True)
class EditPlan:
    edits: tuple[EditOperation, ...]
    raw_response: str


class StructuredEditParser:
    def parse(self, text: str, *, allowed_paths: tuple[str, ...]) -> EditPlan:
        payload = self._load_payload(text)
        edits_payload = payload.get("edits")
        if not isinstance(edits_payload, list) or not edits_payload:
            raise ValueError("Structured edit response must contain a non-empty 'edits' list.")

        allowed = set(allowed_paths)
        seen_paths: set[str] = set()
        edits: list[EditOperation] = []
        for index, item in enumerate(edits_payload, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Edit #{index} must be an object.")
            path = item.get("path")
            old = item.get("old")
            new = item.get("new")
            reason = item.get("reason", "")
            if not isinstance(path, str) or not path:
                raise ValueError(f"Edit #{index} is missing a valid 'path'.")
            if allowed and path not in allowed:
                raise ValueError(f"Edit #{index} targets a non-active file: {path}")
            if path in seen_paths:
                raise ValueError(f"Multiple edits for the same file are not allowed in one plan: {path}")
            if not isinstance(old, str) or not old:
                raise ValueError(f"Edit #{index} is missing a valid 'old' snippet.")
            if not isinstance(new, str):
                raise ValueError(f"Edit #{index} is missing a valid 'new' snippet.")
            if old == new:
                raise ValueError(f"Edit #{index} does not change anything for {path}.")
            if not isinstance(reason, str):
                raise ValueError(f"Edit #{index} contains an invalid 'reason'.")
            edits.append(EditOperation(path=path, old=old, new=new, reason=reason.strip()))
            seen_paths.add(path)
        return EditPlan(edits=tuple(edits), raw_response=text)

    def _load_payload(self, text: str) -> dict:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) < 3:
                raise ValueError("Structured edit response is wrapped in an incomplete code fence.")
            candidate = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Structured edit response is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Structured edit response must be a JSON object.")
        return payload
