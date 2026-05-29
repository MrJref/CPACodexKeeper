import os
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.settings import SettingsError, load_settings, update_config_file


class SettingsTests(unittest.TestCase):
    def _make_env_file(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        env_path = Path(temp_dir.name) / ".env"
        env_path.write_text(content, encoding="utf-8")
        return env_path

    def _make_config_file(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config_path = Path(temp_dir.name) / "config.yml"
        config_path.write_text(content, encoding="utf-8")
        return config_path

    def test_load_settings_reads_required_values(self):
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret"}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.cpa_endpoint, "https://example.com")
        self.assertEqual(settings.cpa_token, "secret")
        self.assertEqual(settings.cron_expression, "0 0/10 * * * ?")
        self.assertIsNone(settings.interval_min_seconds)
        self.assertIsNone(settings.interval_max_seconds)
        self.assertEqual(settings.quota_threshold, 1)
        self.assertEqual(settings.worker_threads, 8)
        self.assertTrue(settings.enable_refresh)
        self.assertTrue(settings.enable_auto_delete)
        self.assertFalse(settings.webui_enabled)
        self.assertEqual(settings.app_port, 8765)
        self.assertFalse(settings.auth_enabled)
        self.assertEqual(settings.log_max_lines, 500)

    def test_load_settings_reads_from_project_env_file(self):
        env_file = self._make_env_file(
            "CPA_ENDPOINT=https://env-file.example.com\n"
            "CPA_TOKEN=file-secret\n"
            "OPENAI_PROXY=http://127.0.0.1:7890\n"
            "CPA_CRON=0 0/5 * * * ?\n"
            "CPA_INTERVAL_MIN=5m\n"
            "CPA_INTERVAL_MAX=15m\n"
            "CPA_WORKER_THREADS=6\n"
            "WEBUI_ENABLED=true\n"
            "APP_PORT=9090\n"
            "LOG_MAX_LINES=1200\n"
            "AUTH_ENABLED=true\n"
            "LOGIN_PASSWORD=web-secret\n"
            "AUTH_SESSION_TTL=12h\n"
        )
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(env_file=env_file)
        self.assertEqual(settings.cpa_endpoint, "https://env-file.example.com")
        self.assertEqual(settings.cpa_token, "file-secret")
        self.assertEqual(settings.proxy, "http://127.0.0.1:7890")
        self.assertEqual(settings.cron_expression, "0 0/5 * * * ?")
        self.assertEqual(settings.interval_min_seconds, 5 * 60)
        self.assertEqual(settings.interval_max_seconds, 15 * 60)
        self.assertEqual(settings.worker_threads, 6)
        self.assertTrue(settings.webui_enabled)
        self.assertEqual(settings.app_port, 9090)
        self.assertEqual(settings.log_max_lines, 1200)
        self.assertTrue(settings.auth_enabled)
        self.assertEqual(settings.login_password, "web-secret")
        self.assertEqual(settings.auth_session_ttl_seconds, 12 * 60 * 60)

    def test_environment_variables_override_project_env_file(self):
        env_file = self._make_env_file("CPA_ENDPOINT=https://env-file.example.com\nCPA_TOKEN=file-secret\nCPA_WORKER_THREADS=4\n")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://shell.example.com", "CPA_TOKEN": "shell-secret", "CPA_WORKER_THREADS": "12"}, clear=True):
            settings = load_settings(env_file=env_file)
        self.assertEqual(settings.cpa_endpoint, "https://shell.example.com")
        self.assertEqual(settings.cpa_token, "shell-secret")
        self.assertEqual(settings.worker_threads, 12)

    def test_config_file_overrides_environment_variables(self):
        config_file = self._make_config_file(
            "cpa:\n"
            "  endpoint: https://config.example.com\n"
            "  token: config-secret\n"
            "  worker_threads: 3\n"
            "  enable_auto_delete: false\n"
            "openai:\n"
            "  proxy: http://127.0.0.1:7890\n"
            "webui:\n"
            "  enabled: true\n"
            "  port: 9091\n"
            "  log_max_lines: 42\n"
        )
        with patch.dict(
            os.environ,
            {"CPA_ENDPOINT": "https://shell.example.com", "CPA_TOKEN": "shell-secret", "CPA_WORKER_THREADS": "12", "WEBUI_ENABLED": "false"},
            clear=True,
        ):
            settings = load_settings(config_file=config_file)
        self.assertEqual(settings.cpa_endpoint, "https://config.example.com")
        self.assertEqual(settings.cpa_token, "config-secret")
        self.assertEqual(settings.proxy, "http://127.0.0.1:7890")
        self.assertEqual(settings.worker_threads, 3)
        self.assertFalse(settings.enable_auto_delete)
        self.assertTrue(settings.webui_enabled)
        self.assertEqual(settings.app_port, 9091)
        self.assertEqual(settings.log_max_lines, 42)

    def test_load_settings_accepts_legacy_cpa_proxy(self):
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_PROXY": "http://127.0.0.1:7890"}, clear=True):
            settings = load_settings()
        self.assertEqual(settings.proxy, "http://127.0.0.1:7890")

    def test_load_settings_accepts_legacy_cpa_proxy_config_key(self):
        config_file = self._make_config_file(
            "cpa:\n"
            "  endpoint: https://config.example.com\n"
            "  token: config-secret\n"
            "  proxy: http://127.0.0.1:7890\n"
        )
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(config_file=config_file)
        self.assertEqual(settings.proxy, "http://127.0.0.1:7890")

    def test_openai_proxy_overrides_legacy_cpa_proxy(self):
        with patch.dict(
            os.environ,
            {
                "CPA_ENDPOINT": "https://example.com",
                "CPA_TOKEN": "secret",
                "OPENAI_PROXY": "http://127.0.0.1:7890",
                "CPA_PROXY": "http://127.0.0.1:8888",
            },
            clear=True,
        ):
            settings = load_settings()
        self.assertEqual(settings.proxy, "http://127.0.0.1:7890")

    def test_load_settings_rejects_missing_endpoint(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_TOKEN": "secret"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_converts_legacy_interval_to_cron(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_INTERVAL": "120"}, clear=True):
            settings = load_settings(env_file=env_file)

        self.assertEqual(settings.cron_expression, "0 0/2 * * * ?")

    def test_load_settings_rejects_bad_cron(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_CRON": "bad cron"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_rejects_bad_legacy_interval(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_INTERVAL": "abc"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_rejects_partial_cron_offset_bounds(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_INTERVAL_MIN": "10m"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_accepts_left_offset_greater_than_right_offset(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(
            os.environ,
            {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_INTERVAL_MIN": "30m", "CPA_INTERVAL_MAX": "10m"},
            clear=True,
        ):
            settings = load_settings(env_file=env_file)

        self.assertEqual(settings.interval_min_seconds, 30 * 60)
        self.assertEqual(settings.interval_max_seconds, 10 * 60)

    def test_load_settings_rejects_non_integer_worker_threads(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_WORKER_THREADS": "abc"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_rejects_zero_worker_threads(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "CPA_WORKER_THREADS": "0"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_requires_login_password_when_auth_enabled(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "AUTH_ENABLED": "true"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_rejects_bad_auth_session_ttl(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "AUTH_SESSION_TTL": "0s"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_load_settings_rejects_zero_log_max_lines(self):
        env_file = Path("does-not-exist.env")
        with patch.dict(os.environ, {"CPA_ENDPOINT": "https://example.com", "CPA_TOKEN": "secret", "LOG_MAX_LINES": "0"}, clear=True):
            with self.assertRaises(SettingsError):
                load_settings(env_file=env_file)

    def test_update_config_file_writes_active_sections(self):
        config_file = self._make_config_file(
            "# template\n"
            "# cpa:\n"
            "#   quota_threshold: 1\n"
        )

        update_config_file(
            {
                "cpa": {"endpoint": "https://config.example.com", "token": "secret", "quota_threshold": 30},
                "openai": {"proxy": "http://127.0.0.1:7890"},
                "webui": {"enabled": True, "log_max_lines": 42},
            },
            config_file=config_file,
        )

        text = config_file.read_text(encoding="utf-8")
        self.assertIn("cpa:\n", text)
        self.assertIn('  endpoint: "https://config.example.com"\n', text)
        self.assertIn("  quota_threshold: 30\n", text)
        self.assertIn("openai:\n", text)
        self.assertIn('  proxy: "http://127.0.0.1:7890"\n', text)
        self.assertIn("webui:\n", text)
        self.assertIn("  enabled: true\n", text)
