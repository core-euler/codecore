"""Disk-backed AIDD knowledge index for docs/ markdown files."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..context.token_budget import estimate_text_tokens


@dataclass(slots=True, frozen=True)
class KnowledgeDocument:
    doc_id: str
    path: str
    title: str
    tokens: int
    updated_at: str
    sections: tuple[str, ...] = ()
    status: str | None = None
    result: str | None = None


@dataclass(slots=True, frozen=True)
class KnowledgeMatch:
    doc_id: str
    path: str
    title: str
    score: int
    excerpt: str


class KnowledgeBaseStore:
    def __init__(self, project_root: Path, config_dir: Path, index_path: Path) -> None:
        self._project_root = project_root.resolve()
        self._docs_dir = (self._project_root / "docs").resolve()
        self._config_dir = config_dir.resolve()
        self._knowledge_dir = index_path.parent.resolve()
        self._index_path = index_path.resolve()
        self._knowledge_dir.mkdir(parents=True, exist_ok=True)

    @property
    def index_path(self) -> Path:
        return self._index_path

    def init_structure(self) -> tuple[Path, ...]:
        created: list[Path] = []
        for path, content in (
            (self._docs_dir / "spec.md", "# Spec\n\nProject specification.\n"),
            (self._docs_dir / "changelog.md", "# Changelog\n\n"),
            (self._docs_dir / "issues.md", "# Issues\n\n"),
            (self._docs_dir / "antipatterns.md", "# Antipatterns\n\n"),
            (self._docs_dir / "phases" / ".gitkeep", ""),
            (self._docs_dir / "results" / ".gitkeep", ""),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                continue
            path.write_text(content, encoding="utf-8")
            created.append(path)
        self.index_docs()
        return tuple(created)

    def index_docs(self) -> tuple[KnowledgeDocument, ...]:
        self._docs_dir.mkdir(parents=True, exist_ok=True)
        documents: list[KnowledgeDocument] = []
        for path in sorted(self._docs_dir.rglob("*.md")):
            relative = path.relative_to(self._project_root)
            content = path.read_text(encoding="utf-8", errors="replace")
            sections = tuple(
                line.lstrip("#").strip()
                for line in content.splitlines()
                if line.startswith("#") and line.lstrip("#").strip()
            )
            title = sections[0] if sections else path.stem.replace("-", " ").title()
            status = "complete" if relative.parts[:2] == ("docs", "results") else None
            result = str(relative) if status == "complete" else None
            documents.append(
                KnowledgeDocument(
                    doc_id=self._doc_id_for(relative),
                    path=str(relative),
                    title=title,
                    tokens=estimate_text_tokens(content),
                    updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date().isoformat(),
                    sections=sections[1:8] if len(sections) > 1 else (),
                    status=status,
                    result=result,
                )
            )
        payload = {"documents": [asdict(item) for item in documents]}
        self._index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return tuple(documents)

    def add_document(self, raw_path: str) -> KnowledgeDocument:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (self._project_root / raw_path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(raw_path)
        if path.suffix.lower() != ".md":
            raise ValueError("Knowledge base only indexes markdown files.")
        self.index_docs()
        relative = str(path.relative_to(self._project_root))
        for item in self.load_documents():
            if item.path == relative:
                return item
        raise RuntimeError(f"Indexed document not found after add: {relative}")

    def load_documents(self) -> tuple[KnowledgeDocument, ...]:
        if not self._index_path.exists():
            return ()
        payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        documents: list[KnowledgeDocument] = []
        for item in payload.get("documents", []):
            if not isinstance(item, dict):
                continue
            documents.append(
                KnowledgeDocument(
                    doc_id=str(item.get("doc_id", "")),
                    path=str(item.get("path", "")),
                    title=str(item.get("title", "")),
                    tokens=int(item.get("tokens", 0)),
                    updated_at=str(item.get("updated_at", "")),
                    sections=tuple(item.get("sections", ())),
                    status=item.get("status"),
                    result=item.get("result"),
                )
            )
        return tuple(documents)

    def edit_document(self, target: str, *, editor: str | None = None) -> Path:
        path = self._resolve_document(target)
        command = shlex.split(editor or "") if editor else []
        if not command:
            command = ["vi"]
        subprocess.run([*command, str(path)], check=True)
        self.index_docs()
        return path

    def complete_phase(self, phase_name: str) -> Path:
        safe = phase_name.strip().lower()
        if not safe:
            raise ValueError("Phase name is required.")
        results_dir = self._docs_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        target = results_dir / f"{safe}-result.md"
        title = safe.replace("-", " ").title()
        date = datetime.now(timezone.utc).date().isoformat()
        if not target.exists():
            target.write_text(
                (
                    f"# Result: {title}\n\n"
                    f"## Status\nCompleted successfully · {date}\n\n"
                    "## What Was Implemented\n- TODO\n\n"
                    "## Testing\n- TODO\n\n"
                    "## Known Limitations\n- TODO\n"
                ),
                encoding="utf-8",
            )
        self.index_docs()
        return target

    def lookup(self, query: str, *, limit: int = 3, excerpt_lines: int = 8) -> tuple[KnowledgeMatch, ...]:
        normalized = query.strip().lower()
        if not normalized:
            return ()
        terms = tuple(term for term in normalized.replace("/", " ").replace("-", " ").split() if len(term) >= 2)
        documents = self.load_documents()
        if not documents:
            documents = self.index_docs()
        scored: list[KnowledgeMatch] = []
        for item in documents:
            path = self._project_root / item.path
            if not path.exists() or not path.is_file():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            score = self._score_document(item, content, terms, normalized)
            if score <= 0:
                continue
            excerpt = self._build_excerpt(content, terms, max_lines=excerpt_lines)
            scored.append(
                KnowledgeMatch(
                    doc_id=item.doc_id,
                    path=item.path,
                    title=item.title,
                    score=score,
                    excerpt=excerpt,
                )
            )
        scored.sort(key=lambda item: (item.score, item.path), reverse=True)
        return tuple(scored[:limit])

    def _resolve_document(self, target: str) -> Path:
        for item in self.load_documents():
            if item.doc_id == target or item.path == target:
                return self._project_root / item.path
        raw = (self._project_root / target).resolve()
        if raw.exists() and raw.is_file():
            return raw
        raise FileNotFoundError(target)

    @staticmethod
    def _score_document(item: KnowledgeDocument, content: str, terms: tuple[str, ...], normalized: str) -> int:
        haystack = "\n".join((item.doc_id, item.path, item.title, " ".join(item.sections), content)).lower()
        score = 0
        if normalized in haystack:
            score += 8
        for term in terms:
            if term in item.title.lower():
                score += 6
            if term in item.doc_id.lower() or term in item.path.lower():
                score += 5
            score += haystack.count(term)
        return score

    @staticmethod
    def _build_excerpt(content: str, terms: tuple[str, ...], *, max_lines: int) -> str:
        lines = content.splitlines()
        if not lines:
            return ""
        focus = 0
        lowered_lines = [line.lower() for line in lines]
        for index, line in enumerate(lowered_lines):
            if any(term in line for term in terms):
                focus = index
                break
        start = max(0, focus - 2)
        end = min(len(lines), start + max_lines)
        excerpt = "\n".join(lines[start:end]).strip()
        if end < len(lines):
            excerpt += "\n...<truncated>"
        return excerpt

    @staticmethod
    def _doc_id_for(relative: Path) -> str:
        parts = list(relative.with_suffix("").parts)
        if parts and parts[0] == "docs":
            parts = parts[1:]
        return "-".join(parts) or "doc"
