"""Application entrypoint helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from rich.console import Console

from .agents import MultiAgentRunner
from .bootstrap import BootstrapContext, bootstrap_application
from .context.composer import DefaultContextComposer
from .context.manager import ContextManager
from .context.repo_map import RepoMapBuilder
from .execution.audit import FileChangeAudit
from .execution.approvals import ApprovalManager
from .execution.files import WorkspaceFiles
from .execution.git import GitWorkspace
from .execution.native_tools import NativeRepositoryTools
from .execution.patches import PatchService
from .execution.shell import ShellToolExecutor
from .execution.tests import VerificationRunner
from .execution.worktrees import WorktreeManager
from .governance.policy import SimplePolicyEngine
from .kernel.event_bus import EventBus
from .kernel.orchestrator import Orchestrator
from .memory.recall import MemoryRecallComposer
from .memory.store import SQLiteMemoryStore
from .providers.adapters.base import AdapterFactory
from .providers.broker import PolicyDrivenBroker
from .providers.health import ProviderHealthService
from .providers.registry import ProviderRegistry
from .skills.composer import SkillPromptComposer
from .skills.loader import SkillLoader
from .skills.registry import LocalSkillRegistry
from .skills.resolver import SkillResolver
from .telemetry.analytics import TelemetryAnalytics
from .telemetry.tracker import TelemetryTracker
from .ui.repl import Repl


@dataclass(slots=True)
class CodeCoreApp:
    """Application shell for the runnable MVP runtime."""

    bootstrap: BootstrapContext
    repl: Repl

    def run(self) -> int:
        print(self.bootstrap.startup_summary())
        return asyncio.run(self.repl.run())


def create_app() -> CodeCoreApp:
    bootstrap = bootstrap_application()
    registry = ProviderRegistry(bootstrap.provider_registry)
    adapter_factory = AdapterFactory()
    health_service = ProviderHealthService(registry, adapter_factory)
    tracker = TelemetryTracker(
        db_path=bootstrap.settings.telemetry_db_path,
        event_dir=bootstrap.settings.event_log_dir,
    )
    memory_store = SQLiteMemoryStore(bootstrap.settings.telemetry_db_path)
    analytics_service = TelemetryAnalytics(
        db_path=bootstrap.settings.telemetry_db_path,
        event_dir=bootstrap.settings.event_log_dir,
    )
    tool_executor = ShellToolExecutor()
    workspace_files = WorkspaceFiles(bootstrap.settings.project_root, bootstrap.settings.artifact_dir)
    patch_service = PatchService(workspace_files)
    git_workspace = GitWorkspace(bootstrap.settings.project_root)
    worktree_manager = WorktreeManager(bootstrap.settings.project_root, bootstrap.settings.artifact_dir / "worktrees")
    file_change_audit = FileChangeAudit(bootstrap.settings.artifact_dir / "file-changes.jsonl")
    approval_manager = ApprovalManager()
    verification_runner = VerificationRunner(tool_executor, bootstrap.settings.project_root)
    policy_engine = SimplePolicyEngine()
    event_bus = EventBus(sinks=[tracker, memory_store])
    context_manager = ContextManager(bootstrap.settings.project_root)
    native_tools = NativeRepositoryTools(context_manager, RepoMapBuilder(bootstrap.settings.project_root))
    skill_dirs = [bootstrap.settings.skills_dir]
    if bootstrap.settings.legacy_skills_dir.exists() and bootstrap.settings.legacy_skills_dir != bootstrap.settings.skills_dir:
        skill_dirs.append(bootstrap.settings.legacy_skills_dir)
    skill_registry = LocalSkillRegistry.from_loader(SkillLoader(tuple(skill_dirs)))
    skill_resolver = SkillResolver(
        skill_registry,
        defaults=tuple(bootstrap.project_manifest.skills.defaults),
        auto_activate=bootstrap.project_manifest.skills.auto_activate,
    )
    composer = DefaultContextComposer(
        context_manager,
        bootstrap.session,
        bootstrap.runtime_state,
        bootstrap.project_manifest,
        skill_resolver=skill_resolver,
        skill_prompt_composer=SkillPromptComposer(),
        memory_recall_composer=MemoryRecallComposer(memory_store),
        repo_map_builder=RepoMapBuilder(bootstrap.settings.project_root),
    )
    broker = PolicyDrivenBroker(
        registry,
        health_service,
        preferred_aliases=tuple(bootstrap.project_manifest.providers.preferred_aliases),
        allow_vpn_routes=bootstrap.project_manifest.providers.allow_vpn_routes,
    )
    multi_agent_runner = MultiAgentRunner(
        project_root=bootstrap.settings.project_root,
        artifact_dir=bootstrap.settings.artifact_dir,
        session=bootstrap.session,
        runtime_state=bootstrap.runtime_state,
        broker=broker,
        health_service=health_service,
        adapter_factory=adapter_factory,
        event_bus=event_bus,
        worktree_manager=worktree_manager,
    )
    orchestrator = Orchestrator(
        session=bootstrap.session,
        runtime_state=bootstrap.runtime_state,
        provider_registry=registry,
        broker=broker,
        health_service=health_service,
        adapter_factory=adapter_factory,
        context_manager=context_manager,
        context_composer=composer,
        event_bus=event_bus,
        skill_registry=skill_registry,
        analytics_service=analytics_service,
        multi_agent_runner=multi_agent_runner,
        tool_executor=tool_executor,
        native_tool_executor=native_tools,
        policy_engine=policy_engine,
        git_workspace=git_workspace,
        patch_service=patch_service,
        file_change_audit=file_change_audit,
        approval_manager=approval_manager,
        verification_engine=verification_runner,
    )
    repl = Repl(orchestrator=orchestrator, console=Console())
    repl.history_path = str(bootstrap.settings.repl_history_path)
    return CodeCoreApp(bootstrap=bootstrap, repl=repl)


def main() -> int:
    return create_app().run()
