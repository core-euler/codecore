"""Project scaffold helpers for first-run bootstrap."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MCP_REGISTRY = """servers:
  - server_id: filesystem
    transport: stdio
    command: npx
    args: [\"-y\", \"@modelcontextprotocol/server-filesystem\", \".\"]
    trust_level: project
    risk_class: readwrite
  - server_id: git
    transport: stdio
    command: uvx
    args: [\"mcp-server-git\"]
    trust_level: project
    risk_class: readonly
"""

DEFAULT_PROVIDER_REGISTRY = """providers:
  - provider_id: deepseek
    transport: openai-compatible
    base_url: https://api.deepseek.com
    auth_strategy: env:DEEPSEEK_API_KEY
    priority: 1
    vpn_required: false
    models:
      - id: deepseek-chat
        alias: ds-v3
        max_context: 128000
        supports_tools: true
        supports_json: true
        cost_per_1k_in: 0.00014
        cost_per_1k_out: 0.00028
      - id: deepseek-reasoner
        alias: ds-r1
        max_context: 128000
        supports_tools: true
        supports_json: true
        cost_per_1k_in: 0.00055
        cost_per_1k_out: 0.00219
  - provider_id: mistral
    transport: openai-compatible
    base_url: https://api.mistral.ai
    auth_strategy: env:MISTRAL_API_KEY
    priority: 2
    vpn_required: false
    models:
      - id: codestral-latest
        alias: codestral
        max_context: 32000
        supports_tools: true
        supports_json: true
  - provider_id: openrouter
    transport: openai-compatible
    base_url: https://openrouter.ai/api/v1
    auth_strategy: env:OPENROUTER_API_KEY
    priority: 3
    vpn_required: true
    models:
      - id: anthropic/claude-sonnet-4-5
        alias: claude
        max_context: 200000
        supports_tools: true
        supports_json: true
  - provider_id: mock
    transport: internal
    priority: 999
    vpn_required: false
    models:
      - id: mock-chat
        alias: mock
        max_context: 16000
        supports_tools: false
        supports_json: true
"""

DEFAULT_PROJECT_TEMPLATE = """version: 1
project_id: {project_id}
default_task_tag: general
context:
  max_prompt_tokens: 24000
  auto_compact_threshold_pct: 80
skills:
  auto_activate: true
  defaults: []
providers:
  preferred_aliases: [ds-v3, codestral]
  allow_vpn_routes: false
policies:
  approval_policy: on-write
"""

_IDENT_RE = re.compile(r"[^a-z0-9-]+")


@dataclass(slots=True, frozen=True)
class ScaffoldPaths:
    config_dir: Path
    project_manifest_path: Path
    provider_registry_path: Path
    mcp_registry_path: Path
    skills_dir: Path
    legacy_skills_dir: Path


def ensure_project_scaffold(project_root: Path) -> ScaffoldPaths:
    config_dir = project_root / ".codecore"
    provider_dir = config_dir / "providers"
    mcp_dir = config_dir / "mcp"
    skills_dir = config_dir / "skills"
    legacy_provider_path = project_root / "providers" / "registry.yaml"
    legacy_mcp_path = project_root / "mcp" / "servers.yaml"
    legacy_skills_dir = project_root / "skills"
    project_manifest_path = config_dir / "project.yaml"
    provider_registry_path = provider_dir / "registry.yaml"
    mcp_registry_path = mcp_dir / "servers.yaml"

    config_dir.mkdir(parents=True, exist_ok=True)
    provider_dir.mkdir(parents=True, exist_ok=True)
    mcp_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    if not project_manifest_path.exists():
        project_manifest_path.write_text(
            DEFAULT_PROJECT_TEMPLATE.format(project_id=_project_id_for_root(project_root)),
            encoding="utf-8",
        )
    if not provider_registry_path.exists():
        _seed_file(provider_registry_path, legacy_provider_path, DEFAULT_PROVIDER_REGISTRY)
    if not mcp_registry_path.exists():
        _seed_file(mcp_registry_path, legacy_mcp_path, DEFAULT_MCP_REGISTRY)

    return ScaffoldPaths(
        config_dir=config_dir,
        project_manifest_path=project_manifest_path,
        provider_registry_path=provider_registry_path,
        mcp_registry_path=mcp_registry_path,
        skills_dir=skills_dir,
        legacy_skills_dir=legacy_skills_dir,
    )


def _seed_file(target: Path, legacy: Path, default_text: str) -> None:
    if legacy.exists():
        target.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
        return
    target.write_text(default_text, encoding="utf-8")


def _project_id_for_root(project_root: Path) -> str:
    base = project_root.name.lower().replace("_", "-")
    normalized = _IDENT_RE.sub("-", base).strip("-")
    return normalized or "codecore-project"
