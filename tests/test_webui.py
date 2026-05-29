import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.settings import Settings
from src.webui import APP_VERSION, HistoryLogger, KeeperRuntime, WebUIService, proxy_label
from src.webui_assets import APP_CSS, APP_JS, INDEX_HTML


class FakeHandler:
    def __init__(self, cookie: str = ""):
        self.headers = {"Cookie": cookie} if cookie else {}


class WebUITests(unittest.TestCase):
    def test_history_logger_records_normal_and_buffered_logs(self):
        logger = HistoryLogger(max_lines=3)

        with redirect_stdout(StringIO()):
            logger.log("INFO", "one")
            logger.emit_lines(["two", "three", "four"])

        self.assertEqual(logger.snapshot(), ["two", "three", "four"])

    def test_history_logger_can_clear_logs(self):
        logger = HistoryLogger(max_lines=3)

        with redirect_stdout(StringIO()):
            logger.log("INFO", "one")
        logger.clear()

        self.assertEqual(logger.snapshot(), [])

    def test_auth_login_creates_session_cookie_token(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            auth_enabled=True,
            login_password="web-secret",
            auth_session_ttl_seconds=3600,
        )
        service = WebUIService(KeeperRuntime(settings))

        ok, token, max_age = service.login("web-secret")

        self.assertTrue(ok)
        self.assertIsNotNone(token)
        self.assertEqual(max_age, 3600)
        self.assertTrue(service.is_authenticated(FakeHandler(f"cpacodexkeeper_session={token}")))

    def test_auth_login_rejects_bad_password(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            auth_enabled=True,
            login_password="web-secret",
        )
        service = WebUIService(KeeperRuntime(settings))

        ok, token, max_age = service.login("bad")

        self.assertFalse(ok)
        self.assertIsNone(token)
        self.assertIsNone(max_age)

    def test_status_exposes_safe_settings_without_token(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="super-secret",
            webui_enabled=True,
        )
        runtime = KeeperRuntime(settings)

        status = runtime.status()

        self.assertEqual(status["settings"]["cpaEndpoint"], "https://example.com")
        self.assertEqual(status["appVersion"], APP_VERSION)
        self.assertNotIn("cpaToken", status["settings"])
        self.assertNotIn("super-secret", str(status))

    def test_session_payload_exposes_app_version(self):
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret")
        service = WebUIService(KeeperRuntime(settings))

        payload = service.session_payload(FakeHandler())

        self.assertEqual(payload["appVersion"], APP_VERSION)
        self.assertTrue(payload["authenticated"])

    def test_runtime_service_is_stopped_by_default(self):
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret")
        runtime = KeeperRuntime(settings)

        status = runtime.status()

        self.assertFalse(status["serviceRunning"])
        self.assertIsNone(status["nextRunAt"])
        self.assertEqual(status["settings"]["appPort"], 8765)

    def test_runtime_can_start_and_stop_scheduler(self):
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret", cron_expression="* * * * * ?")
        runtime = KeeperRuntime(settings)

        def idle_scheduler():
            runtime._stop_event.wait(5)

        with patch.object(runtime, "_scheduler_loop", idle_scheduler):
            self.assertTrue(runtime.start_scheduler())
            self.assertTrue(runtime.status()["serviceRunning"])
            self.assertTrue(runtime.stop_scheduler())
        self.assertFalse(runtime.status()["serviceRunning"])

    def test_scheduler_logs_round_completion_time(self):
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret", cron_expression="* * * * * ?")
        runtime = KeeperRuntime(settings)

        def execute_round():
            runtime._stop_event.set()
            return True

        runtime._execute_round = Mock(side_effect=execute_round)

        with patch("src.webui.next_inspection_timestamp", return_value=0), patch("src.webui.current_log_time", return_value="2026-05-19 12:34:56"):
            with redirect_stdout(StringIO()):
                runtime._scheduler_loop()

        self.assertIn("[*] 第 1 轮巡检结束，完成时间: 2026-05-19 12:34:56", runtime.logger.snapshot())

    def test_runtime_uses_configured_log_max_lines(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            log_max_lines=2,
        )
        runtime = KeeperRuntime(settings)

        with redirect_stdout(StringIO()):
            runtime.logger.emit_lines(["one", "two", "three"])

        self.assertEqual(runtime.status()["settings"]["logMaxLines"], 2)
        self.assertEqual(runtime.status()["logs"], ["two", "three"])

    def test_runtime_update_config_writes_file_and_hot_reloads_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = pathlib.Path(temp_dir) / "config.yml"
            config_path.write_text(
                "cpa:\n"
                "  endpoint: https://example.com\n"
                "  token: secret\n"
                "  quota_threshold: 0\n"
                "  enable_auto_delete: true\n"
                "webui:\n"
                "  log_max_lines: 5\n",
                encoding="utf-8",
            )
            settings = Settings(
                cpa_endpoint="https://example.com",
                cpa_token="secret",
                quota_threshold=0,
                log_max_lines=5,
                enable_auto_delete=True,
            )
            runtime = KeeperRuntime(settings)

            with patch("src.webui.PROJECT_CONFIG_FILE", config_path), patch("src.settings.PROJECT_CONFIG_FILE", config_path), patch.dict(os.environ, {}, clear=True):
                result = runtime.update_config({
                    "cpaEndpoint": "https://example.com",
                    "cronExpression": "0 0/15 * * * ?",
                    "intervalMinSeconds": "600",
                    "intervalMaxSeconds": "1800",
                    "quotaThreshold": 30,
                    "enableAutoDelete": False,
                })

            self.assertEqual(runtime.settings.cron_expression, "0 0/15 * * * ?")
            self.assertEqual(runtime.settings.interval_min_seconds, 600)
            self.assertEqual(runtime.settings.interval_max_seconds, 1800)
            self.assertEqual(runtime.settings.quota_threshold, 30)
            self.assertFalse(runtime.settings.enable_auto_delete)
            self.assertEqual(runtime.keeper.settings.quota_threshold, 30)
            self.assertEqual(runtime.logger.max_lines, 5)
            self.assertEqual(result["values"]["cronExpression"], "0 0/15 * * * ?")
            self.assertEqual(result["values"]["intervalMinSeconds"], 600)
            self.assertEqual(result["values"]["intervalMaxSeconds"], 1800)
            self.assertEqual(result["values"]["quotaThreshold"], 30)
            self.assertFalse(result["values"]["enableAutoDelete"])
            text = config_path.read_text(encoding="utf-8")
            self.assertIn("  cron: \"0 0/15 * * * ?\"\n", text)
            self.assertIn("  interval_min: 600\n", text)
            self.assertIn("  interval_max: 1800\n", text)
            self.assertIn("  quota_threshold: 30\n", text)
            self.assertIn("  enable_auto_delete: false\n", text)
            self.assertIn("  log_max_lines: 5\n", text)

    def test_runtime_update_log_settings_writes_file_and_hot_reloads_log_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = pathlib.Path(temp_dir) / "config.yml"
            config_path.write_text(
                "cpa:\n"
                "  endpoint: https://example.com\n"
                "  token: secret\n"
                "webui:\n"
                "  log_max_lines: 5\n",
                encoding="utf-8",
            )
            settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret", log_max_lines=5)
            runtime = KeeperRuntime(settings)

            with patch("src.webui.PROJECT_CONFIG_FILE", config_path), patch("src.settings.PROJECT_CONFIG_FILE", config_path), patch.dict(os.environ, {}, clear=True):
                result = runtime.update_log_settings({"logMaxLines": 2})

            self.assertEqual(runtime.settings.log_max_lines, 2)
            self.assertEqual(runtime.logger.max_lines, 2)
            self.assertEqual(result["values"]["logMaxLines"], 2)
            text = config_path.read_text(encoding="utf-8")
            self.assertIn("  log_max_lines: 2\n", text)

    def test_proxy_test_reports_unconfigured_proxy(self):
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret")
        runtime = KeeperRuntime(settings)

        result = runtime.test_proxy_latency()

        self.assertFalse(result["ok"])
        self.assertFalse(result["configured"])
        self.assertEqual(result["error"], "OPENAI_PROXY is not configured")

    @patch("src.webui.requests.get")
    def test_proxy_test_reports_latency_and_sanitizes_proxy(self, get_mock):
        get_mock.return_value = Mock(status_code=200)
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            proxy="http://user:pass@127.0.0.1:7890",
        )
        runtime = KeeperRuntime(settings)

        result = runtime.test_proxy_latency()

        self.assertTrue(result["ok"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["proxy"], "http://127.0.0.1:7890")
        self.assertIsInstance(result["latencyMs"], int)
        get_mock.assert_called_once()

    @patch("src.webui.requests.get")
    def test_proxy_test_accepts_unsaved_proxy_override(self, get_mock):
        get_mock.return_value = Mock(status_code=200)
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret")
        runtime = KeeperRuntime(settings)

        result = runtime.test_proxy_latency("http://127.0.0.1:7890")

        self.assertTrue(result["ok"])
        self.assertEqual(result["proxy"], "http://127.0.0.1:7890")
        get_mock.assert_called_once()

    def test_proxy_label_sanitizes_without_port_validation(self):
        self.assertEqual(proxy_label("http://user:pass@127.0.0.1:notaport"), "http://127.0.0.1:notaport")

    def test_webui_assets_include_log_search_shortcut(self):
        self.assertIn('id="logSearchBar"', INDEX_HTML)
        self.assertIn('id="logSearchInput"', INDEX_HTML)
        self.assertIn('tabindex="0"', INDEX_HTML)
        self.assertIn("handleLogSearchShortcut", APP_JS)
        self.assertIn("event.ctrlKey", APP_JS)
        self.assertIn("event.metaKey", APP_JS)

    def test_webui_assets_include_log_auto_scroll_guard(self):
        self.assertIn("logAutoScroll: true", APP_JS)
        self.assertIn("isLogScrolledToBottom", APP_JS)
        self.assertIn("settleLogScroll", APP_JS)
        self.assertIn("addEventListener('scroll', syncLogAutoScroll)", APP_JS)

    def test_config_interval_inputs_accept_integer_minutes(self):
        self.assertIn('id="configIntervalMin" name="intervalMinMinutes" type="number" min="0.0167" step="any"', INDEX_HTML)
        self.assertIn('id="configIntervalMax" name="intervalMaxMinutes" type="number" min="0.0167" step="any"', INDEX_HTML)

    def test_config_form_uses_stable_grid_layout(self):
        self.assertIn("scrollbar-gutter: stable;", APP_CSS)
        self.assertIn("grid-template-columns: repeat(2, minmax(220px, 1fr));", APP_CSS)

    def test_log_output_uses_fixed_height(self):
        self.assertIn(".log-output {\n  height: 520px;", APP_CSS)
        self.assertIn(".log-output { height: 420px; }", APP_CSS)


if __name__ == "__main__":
    unittest.main()
