from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.context.composer import DefaultContextComposer
from codecore.context.manager import ContextManager
from codecore.infra.manifest_loader import load_provider_registry
from codecore.infra.project_manifest import ProjectManifest
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.mcp.control_plane import MCPControlPlane
from codecore.mcp.manifests import MCPRegistryManifest, MCPServerManifest
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class MCPControlPlaneTest(unittest.TestCase):
    def test_disable_enable_and_add_persist_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "servers.yaml"
            registry = MCPRegistryManifest(
                servers=[
                    MCPServerManifest(
                        server_id="filesystem",
                        enabled=True,
                        transport="stdio",
                        command="npx",
                        args=["-y", "@modelcontextprotocol/server-filesystem", "."],
                    )
                ]
            )
            control = MCPControlPlane(registry_path, registry)

            disabled = control.disable_server("filesystem")
            added = control.add_server("git")
            enabled = control.enable_server("filesystem")

            text = registry_path.read_text(encoding="utf-8")
            self.assertFalse(disabled.enabled)
            self.assertTrue(enabled.enabled)
            self.assertEqual(added.server_id, "git")
            self.assertIn("server_id: filesystem", text)
            self.assertIn("server_id: git", text)


class MCPCommandTest(unittest.TestCase):
    def test_mcp_commands_list_status_disable_enable_add(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry_path = temp_path / ".codecore" / "mcp" / "servers.yaml"
            registry_path.parent.mkdir(parents=True)
            control = MCPControlPlane(
                registry_path,
                MCPRegistryManifest(
                    servers=[
                        MCPServerManifest(
                            server_id="filesystem",
                            enabled=True,
                            transport="stdio",
                            command="npx",
                            args=["-y", "@modelcontextprotocol/server-filesystem", "."],
                            trust_level="project",
                            risk_class="readwrite",
                        )
                    ]
                ),
            )
            control.disable_server("filesystem")
            provider_registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(provider_registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=provider_registry,
                broker=PolicyDrivenBroker(provider_registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="mcp-test"),
                ),
                event_bus=EventBus(sinks=[]),
                mcp_control_plane=control,
            )

            async def run():
                listed = await orchestrator.handle_line("/mcp list")
                status = await orchestrator.handle_line("/mcp status")
                enabled = await orchestrator.handle_line("/mcp enable filesystem")
                added = await orchestrator.handle_line("/mcp add git")
                return listed, status, enabled, added

            listed, status, enabled, added = asyncio.run(run())

            self.assertIn("filesystem", listed.output)
            self.assertIn("enabled=no", status.output)
            self.assertIn("Enabled MCP server: filesystem", enabled.output)
            self.assertIn("Added MCP server: git", added.output)
