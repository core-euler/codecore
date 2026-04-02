"""Disk-backed session and transcript persistence."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..domain.enums import TaskTag
from ..domain.models import ChatMessage
from ..kernel.runtime_state import RuntimeState
from ..kernel.session import SessionRuntime


@dataclass(slots=True)
class SessionStateStore:
    session_path: Path
    context_path: Path
    snapshot_dir: Path

    def __post_init__(self) -> None:
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def load_into(self, session: SessionRuntime, runtime_state: RuntimeState) -> bool:
        if not self.session_path.exists():
            return False
        payload = json.loads(self.session_path.read_text(encoding="utf-8"))
        transcript = payload.get("transcript", [])
        session.session_id = self._as_text(payload.get("session_id"), default=session.session_id)
        session.started_at = self._parse_datetime(payload.get("started_at"), default=session.started_at)
        session.task_tag = self._parse_task_tag(payload.get("task_tag"), default=session.task_tag)
        session.transcript = self._parse_messages(transcript)
        session.active_files = self._parse_text_list(payload.get("active_files"))
        session.active_skills = self._parse_text_list(payload.get("active_skills"))
        session.request_count = self._as_int(payload.get("request_count"), default=session.request_count)
        session.total_cost_usd = self._as_float(payload.get("total_cost_usd"), default=session.total_cost_usd)
        session.last_model_alias = self._as_optional_text(payload.get("last_model_alias"))
        session.last_turn_id = self._as_optional_text(payload.get("last_turn_id"))
        session.last_rating = self._as_optional_int(payload.get("last_rating"))
        session.last_user_prompt = self._as_optional_text(payload.get("last_user_prompt"))
        session.last_verification_summary = self._as_optional_text(payload.get("last_verification_summary"))
        session.allowed_action_types = self._parse_text_list(payload.get("allowed_action_types"))
        session.recent_proofs = self._parse_text_maps(payload.get("recent_proofs"))
        runtime_state.manual_model_alias = self._as_optional_text(payload.get("manual_model_alias"))
        runtime_state.active_skills = list(self._parse_text_list(payload.get("pinned_skills")))
        runtime_state.active_files = list(session.active_files)
        self.write_context_markdown(session)
        return True

    def save(self, session: SessionRuntime, runtime_state: RuntimeState) -> None:
        payload = {
            "session_id": session.session_id,
            "started_at": session.started_at.isoformat(),
            "task_tag": session.task_tag.value,
            "transcript": [{"role": item.role, "content": item.content} for item in session.transcript],
            "active_files": list(session.active_files),
            "active_skills": list(session.active_skills),
            "request_count": session.request_count,
            "total_cost_usd": round(session.total_cost_usd, 6),
            "last_model_alias": session.last_model_alias,
            "last_turn_id": session.last_turn_id,
            "last_rating": session.last_rating,
            "last_user_prompt": session.last_user_prompt,
            "last_verification_summary": session.last_verification_summary,
            "allowed_action_types": list(session.allowed_action_types),
            "recent_proofs": list(session.recent_proofs),
            "manual_model_alias": runtime_state.manual_model_alias,
            "pinned_skills": list(runtime_state.active_skills),
        }
        self.session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.write_context_markdown(session)

    def write_context_markdown(self, session: SessionRuntime) -> Path:
        self.context_path.write_text(self.render_markdown(session), encoding="utf-8")
        return self.context_path

    def load_from_markdown(self, path: Path) -> list[ChatMessage]:
        return self.parse_markdown(path.read_text(encoding="utf-8"))

    def save_snapshot(self, name: str, session: SessionRuntime) -> Path:
        target = self.snapshot_dir / f"{self._sanitize_name(name)}.md"
        target.write_text(self.render_markdown(session), encoding="utf-8")
        return target

    def load_snapshot(self, name: str) -> list[ChatMessage]:
        target = self.snapshot_dir / f"{self._sanitize_name(name)}.md"
        return self.load_from_markdown(target)

    def list_snapshots(self) -> tuple[str, ...]:
        return tuple(sorted(path.stem for path in self.snapshot_dir.glob("*.md")))

    def edit_context(self, session: SessionRuntime, *, editor: str | None = None) -> list[ChatMessage]:
        target = self.write_context_markdown(session)
        command = shlex.split(editor or "") if editor else shlex.split("")
        if not command:
            command = shlex.split(self._default_editor())
        subprocess.run([*command, str(target)], check=True)
        return self.load_from_markdown(target)

    def render_markdown(self, session: SessionRuntime) -> str:
        header = f"# Context · {session.session_id}"
        if not session.transcript:
            return header + "\n\n<!-- empty -->\n"
        blocks = [header]
        for message in session.transcript:
            blocks.append(f"\n## [{message.role}]\n{message.content.rstrip()}\n")
        return "\n".join(blocks).rstrip() + "\n"

    def parse_markdown(self, markdown: str) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        current_role: str | None = None
        current_lines: list[str] = []
        for raw_line in markdown.splitlines():
            line = raw_line.rstrip("\n")
            if line.startswith("## [") and line.endswith("]"):
                self._flush_message(messages, current_role, current_lines)
                current_role = line[4:-1].strip()
                current_lines = []
                continue
            if line.startswith("# Context ·") and current_role is None:
                continue
            if current_role is None:
                continue
            current_lines.append(raw_line)
        self._flush_message(messages, current_role, current_lines)
        return messages

    @staticmethod
    def _flush_message(messages: list[ChatMessage], role: str | None, lines: list[str]) -> None:
        if role is None:
            return
        content = "\n".join(lines).strip()
        if not content:
            return
        messages.append(ChatMessage(role=role, content=content))

    @staticmethod
    def _sanitize_name(value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip().lower())
        cleaned = "-".join(part for part in cleaned.split("-") if part)
        return cleaned or "snapshot"

    @staticmethod
    def _default_editor() -> str:
        return "vi"

    @staticmethod
    def _parse_messages(payload: Any) -> list[ChatMessage]:
        if not isinstance(payload, list):
            return []
        messages: list[ChatMessage] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                messages.append(ChatMessage(role=role, content=content))
        return messages

    @staticmethod
    def _parse_text_list(payload: Any) -> list[str]:
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, str)]

    @staticmethod
    def _parse_text_maps(payload: Any) -> list[dict[str, str]]:
        if not isinstance(payload, list):
            return []
        parsed: list[dict[str, str]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            text_map = {str(key): value for key, value in item.items() if isinstance(key, str) and isinstance(value, str)}
            if text_map:
                parsed.append(text_map)
        return parsed

    @staticmethod
    def _parse_task_tag(payload: Any, *, default: TaskTag) -> TaskTag:
        if not isinstance(payload, str):
            return default
        try:
            return TaskTag(payload)
        except ValueError:
            return default

    @staticmethod
    def _parse_datetime(payload: Any, *, default: datetime) -> datetime:
        if not isinstance(payload, str):
            return default
        try:
            return datetime.fromisoformat(payload)
        except ValueError:
            return default

    @staticmethod
    def _as_text(payload: Any, *, default: str) -> str:
        return payload if isinstance(payload, str) and payload else default

    @staticmethod
    def _as_optional_text(payload: Any) -> str | None:
        return payload if isinstance(payload, str) and payload else None

    @staticmethod
    def _as_int(payload: Any, *, default: int) -> int:
        return payload if isinstance(payload, int) else default

    @staticmethod
    def _as_optional_int(payload: Any) -> int | None:
        return payload if isinstance(payload, int) else None

    @staticmethod
    def _as_float(payload: Any, *, default: float) -> float:
        if isinstance(payload, (float, int)):
            return float(payload)
        return default
