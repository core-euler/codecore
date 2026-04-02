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
from .infra.aidd_docs import AIDDDocsStore
from .infra.knowledge_base import KnowledgeBaseStore
from .infra.session_state import SessionStateStore
from .infra.web_research import WebResearchService
from .kernel.event_bus import EventBus
from .kernel.orchestrator import Orchestrator
from .memory.recall import MemoryRecallComposer
from .memory.store import SQLiteMemoryStore
from .mcp.control_plane import MCPControlPlane
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


@dataclass(slots=True)
class RuntimeDependencies:
    registry: ProviderRegistry
    adapter_factory: AdapterFactory
    health_service: ProviderHealthService
    analytics_service: TelemetryAnalytics
    tool_executor: ShellToolExecutor
    workspace_files: WorkspaceFiles
    patch_service: PatchService
    git_workspace: GitWorkspace
    worktree_manager: WorktreeManager
    file_change_audit: FileChangeAudit
    policy_engine: SimplePolicyEngine
    aidd_docs: AIDDDocsStore
    mcp_control: MCPControlPlane
    knowledge_base: KnowledgeBaseStore
    web_research: WebResearchService
    event_bus: EventBus
    context_manager: ContextManager
    native_tools: NativeRepositoryTools
    skill_registry: LocalSkillRegistry
    skill_resolver: SkillResolver
    tracker: TelemetryTracker
    memory_store: SQLiteMemoryStore


def build_runtime_dependencies(bootstrap: BootstrapContext) -> RuntimeDependencies:
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
    policy_engine = SimplePolicyEngine()
    aidd_docs = AIDDDocsStore(bootstrap.settings.project_root)
    mcp_control = MCPControlPlane(bootstrap.settings.mcp_registry_path, bootstrap.mcp_registry)
    knowledge_base = KnowledgeBaseStore(
        bootstrap.settings.project_root,
        bootstrap.settings.config_dir,
        bootstrap.settings.knowledge_index_path,
    )
    web_research = WebResearchService()
    event_bus = EventBus(sinks=[tracker, memory_store])
    context_manager = ContextManager(bootstrap.settings.project_root)
    native_tools = NativeRepositoryTools(
        context_manager,
        RepoMapBuilder(bootstrap.settings.project_root),
        knowledge_base_store=knowledge_base,
    )
    skill_dirs = [bootstrap.settings.skills_dir]
    if bootstrap.settings.legacy_skills_dir.exists() and bootstrap.settings.legacy_skills_dir != bootstrap.settings.skills_dir:
        skill_dirs.append(bootstrap.settings.legacy_skills_dir)
    skill_registry = LocalSkillRegistry.from_loader(SkillLoader(tuple(skill_dirs)))
    skill_resolver = SkillResolver(
        skill_registry,
        defaults=tuple(bootstrap.project_manifest.skills.defaults),
        auto_activate=bootstrap.project_manifest.skills.auto_activate,
    )
    return RuntimeDependencies(
        registry=registry,
        adapter_factory=adapter_factory,
        health_service=health_service,
        analytics_service=analytics_service,
        tool_executor=tool_executor,
        workspace_files=workspace_files,
        patch_service=patch_service,
        git_workspace=git_workspace,
        worktree_manager=worktree_manager,
        file_change_audit=file_change_audit,
        policy_engine=policy_engine,
        aidd_docs=aidd_docs,
        mcp_control=mcp_control,
        knowledge_base=knowledge_base,
        web_research=web_research,
        event_bus=event_bus,
        context_manager=context_manager,
        native_tools=native_tools,
        skill_registry=skill_registry,
        skill_resolver=skill_resolver,
        tracker=tracker,
        memory_store=memory_store,
    )


def build_orchestrator(
    bootstrap: BootstrapContext,
    deps: RuntimeDependencies,
    *,
    session,
    runtime_state,
    approval_manager: ApprovalManager | None = None,
    verification_engine: VerificationRunner | None = None,
    session_store: SessionStateStore | None = None,
    policy_engine: SimplePolicyEngine | None = None,
) -> Orchestrator:
    verification_runner = verification_engine or VerificationRunner(deps.tool_executor, bootstrap.settings.project_root)
    session_store = session_store or SessionStateStore(
        bootstrap.settings.session_state_path,
        bootstrap.settings.context_edit_path,
        bootstrap.settings.context_snapshot_dir,
    )
    composer = DefaultContextComposer(
        deps.context_manager,
        session,
        runtime_state,
        bootstrap.project_manifest,
        skill_resolver=deps.skill_resolver,
        skill_prompt_composer=SkillPromptComposer(),
        memory_recall_composer=MemoryRecallComposer(deps.memory_store),
        repo_map_builder=RepoMapBuilder(bootstrap.settings.project_root),
    )
    broker = PolicyDrivenBroker(
        deps.registry,
        deps.health_service,
        preferred_aliases=tuple(bootstrap.project_manifest.providers.preferred_aliases),
        allow_vpn_routes=bootstrap.project_manifest.providers.allow_vpn_routes,
    )
    multi_agent_runner = MultiAgentRunner(
        project_root=bootstrap.settings.project_root,
        artifact_dir=bootstrap.settings.artifact_dir,
        session=session,
        runtime_state=runtime_state,
        broker=broker,
        health_service=deps.health_service,
        adapter_factory=deps.adapter_factory,
        event_bus=deps.event_bus,
        worktree_manager=deps.worktree_manager,
    )
    return Orchestrator(
        session=session,
        runtime_state=runtime_state,
        provider_registry=deps.registry,
        broker=broker,
        health_service=deps.health_service,
        adapter_factory=deps.adapter_factory,
        context_manager=deps.context_manager,
        context_composer=composer,
        event_bus=deps.event_bus,
        skill_registry=deps.skill_registry,
        analytics_service=deps.analytics_service,
        multi_agent_runner=multi_agent_runner,
        tool_executor=deps.tool_executor,
        native_tool_executor=deps.native_tools,
        policy_engine=policy_engine or deps.policy_engine,
        git_workspace=deps.git_workspace,
        patch_service=deps.patch_service,
        file_change_audit=deps.file_change_audit,
        approval_manager=approval_manager or ApprovalManager(),
        verification_engine=verification_runner,
        session_store=session_store,
        aidd_docs_store=deps.aidd_docs,
        knowledge_base_store=deps.knowledge_base,
        web_research_service=deps.web_research,
        mcp_control_plane=deps.mcp_control,
    )


def create_app() -> CodeCoreApp:
    bootstrap = bootstrap_application()
    deps = build_runtime_dependencies(bootstrap)
    orchestrator = build_orchestrator(
        bootstrap,
        deps,
        session=bootstrap.session,
        runtime_state=bootstrap.runtime_state,
    )
    repl = Repl(orchestrator=orchestrator, console=Console())
    repl.history_path = str(bootstrap.settings.repl_history_path)
    return CodeCoreApp(bootstrap=bootstrap, repl=repl)


def main() -> int:
    return create_app().run()
