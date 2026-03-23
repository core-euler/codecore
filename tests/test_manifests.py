from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.infra.manifest_loader import (
    load_mcp_registry,
    load_project_manifest,
    load_provider_registry,
    load_skill_manifest,
)


class ManifestLoaderTest(unittest.TestCase):
    def test_project_manifest_loads(self) -> None:
        manifest = load_project_manifest(ROOT / ".codecore" / "project.yaml")
        self.assertEqual(manifest.project_id, "codecore")
        self.assertEqual(manifest.policies.approval_policy, "on-write")

    def test_provider_registry_loads(self) -> None:
        registry = load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml")
        self.assertGreaterEqual(len(registry.providers), 3)
        self.assertEqual(registry.providers[0].provider_id, "deepseek")
        self.assertEqual(registry.providers[0].models[0].alias, "ds-v3")

    def test_mcp_registry_loads(self) -> None:
        registry = load_mcp_registry(ROOT / ".codecore" / "mcp" / "servers.yaml")
        self.assertEqual(len(registry.servers), 2)
        self.assertEqual(registry.servers[0].server_id, "filesystem")

    def test_skill_frontmatter_loads(self) -> None:
        manifest = load_skill_manifest(ROOT / "tests" / "fixtures" / "sample_skill" / "SKILL.md")
        self.assertEqual(manifest.name, "architecture-review")
        self.assertIn("boundary", manifest.triggers)


if __name__ == "__main__":
    unittest.main()
