from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.infra.llm_setup import LLMSetupService, load_auth_env
from codecore.infra.manifest_loader import load_project_manifest, load_provider_registry
from codecore.infra.settings import load_settings
from codecore.kernel.runtime_state import RuntimeState
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class LLMSetupServiceTest(unittest.TestCase):
    def test_save_persists_auth_env_and_default_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous = Path.cwd()
            os.chdir(temp_path)
            try:
                settings = load_settings()
                project_manifest = load_project_manifest(settings.project_config_path)
                registry = ProviderRegistry(load_provider_registry(settings.provider_registry_path))
                runtime_state = RuntimeState.default()
                service = LLMSetupService(
                    settings=settings,
                    project_manifest=project_manifest,
                    registry=registry,
                    health_service=ProviderHealthService(registry, AdapterFactory()),
                    runtime_state=runtime_state,
                )

                saved = service.save(alias="ds-v3", api_key="secret-key")

                self.assertEqual(saved.alias, "ds-v3")
                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "secret-key")
                self.assertIn("DEEPSEEK_API_KEY=secret-key", settings.auth_env_path.read_text(encoding="utf-8"))
                project_yaml = settings.project_config_path.read_text(encoding="utf-8")
                self.assertIn("preferred_aliases:", project_yaml)
                self.assertIn("- ds-v3", project_yaml)
                self.assertEqual(runtime_state.manual_model_alias, "ds-v3")
            finally:
                os.environ.pop("DEEPSEEK_API_KEY", None)
                os.chdir(previous)

    def test_load_auth_env_restores_saved_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            auth_env_path = Path(temp_dir) / "auth.env"
            auth_env_path.write_text("DEEPSEEK_API_KEY=persisted\n", encoding="utf-8")
            os.environ.pop("DEEPSEEK_API_KEY", None)

            load_auth_env(auth_env_path)

            self.assertEqual(os.environ.get("DEEPSEEK_API_KEY"), "persisted")

    def test_service_reports_ready_when_key_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous = Path.cwd()
            os.chdir(temp_path)
            try:
                settings = load_settings()
                project_manifest = load_project_manifest(settings.project_config_path)
                registry = ProviderRegistry(load_provider_registry(settings.provider_registry_path))
                runtime_state = RuntimeState.default()
                service = LLMSetupService(
                    settings=settings,
                    project_manifest=project_manifest,
                    registry=registry,
                    health_service=ProviderHealthService(registry, AdapterFactory()),
                    runtime_state=runtime_state,
                )
                os.environ["DEEPSEEK_API_KEY"] = "test-key"

                self.assertTrue(asyncio.run(service.is_ready()))
            finally:
                os.environ.pop("DEEPSEEK_API_KEY", None)
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
