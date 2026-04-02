"""Lightweight web research helpers for docs, search, and dependency freshness."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

_PKG_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
_RESULT_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>(?P<tail>.*?)(?=<a[^>]+class="[^"]*result__a|$)',
    re.DOTALL,
)
_SNIPPET_RE = re.compile(r'class="[^"]*result__snippet[^"]*"[^>]*>(?P<snippet>.*?)</', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(slots=True, frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass(slots=True, frozen=True)
class ProofRecord:
    claim: str
    title: str
    url: str
    snippet: str
    checked_at: str


@dataclass(slots=True, frozen=True)
class DependencyStatus:
    package: str
    used: str
    latest: str
    status: str
    docs_url: str | None = None


class WebResearchService:
    def __init__(
        self,
        *,
        fetch_text: Callable[[str], str] | None = None,
        fetch_json: Callable[[str], dict[str, object]] | None = None,
    ) -> None:
        self._fetch_text = fetch_text or self._default_fetch_text
        self._fetch_json = fetch_json or self._default_fetch_json

    def search(self, query: str, *, limit: int = 5) -> tuple[SearchResult, ...]:
        if not query.strip():
            return ()
        html = self._fetch_text(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
        results: list[SearchResult] = []
        for match in _RESULT_RE.finditer(html):
            title = _clean_html(match.group("title"))
            url = _normalize_result_url(match.group("href"))
            if not title or not url:
                continue
            snippet_match = _SNIPPET_RE.search(match.group("tail"))
            snippet = _clean_html(snippet_match.group("snippet")) if snippet_match else ""
            results.append(SearchResult(title=title, url=url, snippet=snippet))
            if len(results) >= limit:
                break
        return tuple(results)

    def docs(self, package: str) -> DependencyStatus:
        payload = self._fetch_json(f"https://pypi.org/pypi/{quote_plus(package)}/json")
        info = payload.get("info", {})
        if not isinstance(info, dict):
            raise ValueError(f"PyPI metadata for {package} is malformed.")
        latest = str(info.get("version", "")).strip() or "unknown"
        project_urls = info.get("project_urls", {})
        docs_url = None
        if isinstance(project_urls, dict):
            for key in ("Documentation", "Homepage", "Source", "Repository"):
                value = project_urls.get(key)
                if isinstance(value, str) and value.strip():
                    docs_url = value.strip()
                    break
        if docs_url is None:
            home_page = info.get("home_page")
            if isinstance(home_page, str) and home_page.strip():
                docs_url = home_page.strip()
        return DependencyStatus(package=package, used=package, latest=latest, status="docs", docs_url=docs_url)

    def verify(self, claim: str, *, limit: int = 3) -> tuple[ProofRecord, ...]:
        checked_at = datetime.now(timezone.utc).date().isoformat()
        return tuple(
            ProofRecord(
                claim=claim,
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                checked_at=checked_at,
            )
            for item in self.search(claim, limit=limit)
        )

    def inspect_dependencies(self, project_root: Path) -> tuple[DependencyStatus, ...]:
        specs = self._load_dependency_specs(project_root)
        statuses: list[DependencyStatus] = []
        for package, used in specs:
            try:
                docs = self.docs(package)
            except Exception:
                statuses.append(DependencyStatus(package=package, used=used, latest="unknown", status="unresolved"))
                continue
            statuses.append(
                DependencyStatus(
                    package=package,
                    used=used,
                    latest=docs.latest,
                    status=_compare_dependency_versions(used, docs.latest),
                    docs_url=docs.docs_url,
                )
            )
        return tuple(statuses)

    def _load_dependency_specs(self, project_root: Path) -> tuple[tuple[str, str], ...]:
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = payload.get("project", {})
            dependencies = project.get("dependencies", []) if isinstance(project, dict) else []
            if isinstance(dependencies, list):
                parsed = [self._parse_dep_spec(str(item)) for item in dependencies]
                return tuple(item for item in parsed if item is not None)
        requirements = project_root / "requirements.txt"
        if requirements.exists():
            parsed = [self._parse_dep_spec(line) for line in requirements.read_text(encoding="utf-8").splitlines()]
            return tuple(item for item in parsed if item is not None)
        return ()

    @staticmethod
    def _parse_dep_spec(raw: str) -> tuple[str, str] | None:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            return None
        match = _PKG_RE.match(stripped)
        if not match:
            return None
        package = match.group(1).replace("_", "-")
        return package, stripped

    @staticmethod
    def _default_fetch_text(url: str) -> str:
        request = Request(url, headers={"User-Agent": "CodeCore/0.1 (+https://github.com/core-euler/codecore)"})
        with urlopen(request, timeout=12) as response:
            return response.read().decode("utf-8", errors="replace")

    @classmethod
    def _default_fetch_json(cls, url: str) -> dict[str, object]:
        payload = cls._default_fetch_text(url)
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise ValueError(f"Expected JSON object from {url}")
        return decoded


def _normalize_result_url(raw: str) -> str:
    if raw.startswith("//"):
        return "https:" + raw
    if "duckduckgo.com/l/?" not in raw:
        return raw
    parsed = urlparse(raw)
    target = parse_qs(parsed.query).get("uddg")
    if target:
        return unquote(target[0])
    return raw


def _clean_html(raw: str) -> str:
    text = unescape(_TAG_RE.sub("", raw or ""))
    return " ".join(text.split())


def _compare_dependency_versions(used_spec: str, latest: str) -> str:
    if "==" not in used_spec and any(marker in used_spec for marker in (">", "<", "~", ",")):
        return "range"
    pinned = _extract_version(used_spec)
    latest_parts = _version_parts(latest)
    pinned_parts = _version_parts(pinned) if pinned else ()
    if not latest_parts:
        return "unknown"
    if not pinned_parts:
        return "range"
    if pinned_parts == latest_parts:
        return "up-to-date"
    if pinned_parts[:1] != latest_parts[:1]:
        return "major-gap"
    if pinned_parts[0] == 0 and pinned_parts[:2] != latest_parts[:2]:
        return "major-gap"
    if pinned_parts[:2] != latest_parts[:2]:
        return "minor-gap"
    return "patch-gap"


def _extract_version(spec: str) -> str | None:
    for marker in ("==", ">=", "~=", "<=", ">", "<"):
        if marker in spec:
            candidate = spec.split(marker, 1)[1].split(",", 1)[0].strip()
            return candidate or None
    return None


def _version_parts(raw: str | None) -> tuple[int, ...]:
    if not raw:
        return ()
    parts: list[int] = []
    for token in raw.split("."):
        digits = "".join(char for char in token if char.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)
