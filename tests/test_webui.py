import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.settings import Settings
from src.webui import HistoryLogger, KeeperRuntime, WebUIService


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


if __name__ == "__main__":
    unittest.main()
