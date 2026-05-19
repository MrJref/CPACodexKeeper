import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class DockerComposeTests(unittest.TestCase):
    def test_compose_exposes_runtime_toggles(self):
        compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("CPA_ENABLE_REFRESH:", compose_text)
        self.assertIn("CPA_CRON:", compose_text)
        self.assertIn("CPA_ENABLE_REFRESH: ${CPA_ENABLE_REFRESH:-true}", compose_text)
        self.assertIn("CPA_ENABLE_AUTO_DELETE: ${CPA_ENABLE_AUTO_DELETE:-true}", compose_text)
        self.assertIn("CPA_WORKER_THREADS:", compose_text)
        self.assertIn("WEBUI_ENABLED: ${WEBUI_ENABLED:-true}", compose_text)
        self.assertIn("CPA_QUOTA_THRESHOLD: ${CPA_QUOTA_THRESHOLD:-1}", compose_text)
        self.assertIn("AUTH_ENABLED: ${AUTH_ENABLED:-false}", compose_text)
        self.assertIn("LOGIN_PASSWORD: ${LOGIN_PASSWORD:-}", compose_text)
        self.assertIn("LOG_MAX_LINES: ${LOG_MAX_LINES:-500}", compose_text)
        self.assertIn('"${APP_PORT:-8765}:${APP_PORT:-8765}"', compose_text)
        self.assertIn("APP_PORT: ${APP_PORT:-8765}", compose_text)
        self.assertIn("./config.yml:/app/config.yml", compose_text)
        self.assertNotIn("./config.yml:/app/config.yml:ro", compose_text)
