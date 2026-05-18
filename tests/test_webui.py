import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.settings import Settings
from src.webui import HistoryLogger, KeeperRuntime, WebUIService, proxy_label


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
        self.assertNotIn("cpaToken", status["settings"])
        self.assertNotIn("super-secret", str(status))

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

    def test_proxy_test_reports_unconfigured_proxy(self):
        settings = Settings(cpa_endpoint="https://example.com", cpa_token="secret")
        runtime = KeeperRuntime(settings)

        result = runtime.test_proxy_latency()

        self.assertFalse(result["ok"])
        self.assertFalse(result["configured"])
        self.assertEqual(result["error"], "CPA_PROXY is not configured")

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

    def test_proxy_label_sanitizes_without_port_validation(self):
        self.assertEqual(proxy_label("http://user:pass@127.0.0.1:notaport"), "http://127.0.0.1:notaport")


if __name__ == "__main__":
    unittest.main()
