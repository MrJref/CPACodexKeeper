import json
import secrets
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .logging_utils import ConsoleLogger
from .maintainer import CPACodexKeeper
from .settings import Settings
from .webui_assets import APP_CSS, APP_JS, INDEX_HTML


SESSION_COOKIE = "cpacodexkeeper_session"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_from_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


class HistoryLogger(ConsoleLogger):
    def __init__(self, max_lines: int = 500) -> None:
        super().__init__()
        self.max_lines = max_lines
        self._history: list[str] = []
        self._history_lock = threading.Lock()

    def _append_history(self, lines: list[str]) -> None:
        if not lines:
            return
        with self._history_lock:
            self._history.extend(lines)
            if len(self._history) > self.max_lines:
                del self._history[: len(self._history) - self.max_lines]

    def snapshot(self) -> list[str]:
        with self._history_lock:
            return list(self._history)

    def log(self, level: str, message: str, indent: int = 0) -> None:
        prefix = self.PREFIX_MAP.get(level, f"[{level}]")
        line = f"{'    ' * indent}{prefix} {message}"
        with self._lock:
            print(line)
        self._append_history([line])

    def token_header(self, idx: int, total: int, name: str) -> None:
        line = f"[{idx}/{total}] {name}"
        with self._lock:
            print(line)
        self._append_history([line])

    def divider(self) -> None:
        line = "=" * 60
        with self._lock:
            print(line)
        self._append_history([line])

    def blank_line(self) -> None:
        with self._lock:
            print()
        self._append_history([""])

    def emit_lines(self, lines: list[str]) -> None:
        if not lines:
            return
        with self._lock:
            for line in lines:
                print(line)
        self._append_history(lines)


class KeeperRuntime:
    def __init__(self, settings: Settings, *, dry_run: bool = False) -> None:
        self.settings = settings
        self.dry_run = dry_run
        self.logger = HistoryLogger()
        self.keeper = CPACodexKeeper(settings=settings, dry_run=dry_run, logger=self.logger)
        self._run_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._scheduler_thread: threading.Thread | None = None
        self.running = False
        self.round_no = 0
        self.last_started_at: float | None = None
        self.last_finished_at: float | None = None
        self.next_run_at: float | None = None
        self.last_error: str | None = None

    def start_scheduler(self) -> None:
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, name="cpacodexkeeper-scheduler", daemon=True)
        self._scheduler_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _scheduler_loop(self) -> None:
        self.logger.log("INFO", f"守护模式启动，执行间隔: {self.settings.interval_seconds} 秒")
        while not self._stop_event.is_set():
            with self._state_lock:
                self.round_no += 1
                round_no = self.round_no
                self.next_run_at = None
            self.logger.log("INFO", f"开始第 {round_no} 轮巡检")
            started = self._execute_round()
            if started:
                self.logger.log("INFO", f"第 {round_no} 轮巡检结束")
            with self._state_lock:
                self.next_run_at = time.time() + self.settings.interval_seconds
                wait_seconds = self.settings.interval_seconds
            self.logger.log("INFO", f"等待 {wait_seconds} 秒后开始下一轮")
            self._stop_event.wait(wait_seconds)

    def run_once_async(self) -> bool:
        thread = threading.Thread(target=self._execute_round, name="cpacodexkeeper-manual-run", daemon=True)
        thread.start()
        return True

    def _execute_round(self) -> bool:
        if not self._run_lock.acquire(blocking=False):
            self.logger.log("WARN", "已有巡检任务正在运行，本次触发已跳过")
            return False
        try:
            with self._state_lock:
                self.running = True
                self.last_started_at = time.time()
                self.last_error = None
            try:
                self.keeper.run()
            except Exception as exc:
                with self._state_lock:
                    self.last_error = str(exc)
                self.logger.log("ERROR", f"巡检异常: {exc}")
            finally:
                with self._state_lock:
                    self.running = False
                    self.last_finished_at = time.time()
            return True
        finally:
            self._run_lock.release()

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "running": self.running,
                "roundNo": self.round_no,
                "lastStartedAt": iso_from_timestamp(self.last_started_at),
                "lastFinishedAt": iso_from_timestamp(self.last_finished_at),
                "nextRunAt": iso_from_timestamp(self.next_run_at),
                "lastError": self.last_error,
                "dryRun": self.dry_run,
                "stats": self.keeper._stats_snapshot(),
                "logs": self.logger.snapshot(),
                "settings": {
                    "cpaEndpoint": self.settings.cpa_endpoint,
                    "intervalSeconds": self.settings.interval_seconds,
                    "quotaThreshold": self.settings.quota_threshold,
                    "expiryThresholdDays": self.settings.expiry_threshold_days,
                    "enableRefresh": self.settings.enable_refresh,
                    "workerThreads": self.settings.worker_threads,
                    "authEnabled": self.settings.auth_enabled,
                    "appPort": self.settings.app_port,
                },
                "timestamp": utc_now_iso(),
            }

    def token_summary(self) -> dict[str, Any]:
        tokens = self.keeper.get_token_list()
        sanitized = [
            {
                "name": token.get("name", ""),
                "type": token.get("type", ""),
                "email": token.get("email", ""),
                "disabled": bool(token.get("disabled", False)),
                "expired": token.get("expired", ""),
            }
            for token in tokens
        ]
        return {"total": len(sanitized), "tokens": sanitized, "timestamp": utc_now_iso()}


class WebUIService:
    def __init__(self, runtime: KeeperRuntime) -> None:
        self.runtime = runtime
        self.settings = runtime.settings
        self._sessions: dict[str, float] = {}
        self._sessions_lock = threading.Lock()

    def session_payload(self, handler: BaseHTTPRequestHandler) -> dict[str, bool]:
        return {
            "authEnabled": self.settings.auth_enabled,
            "authenticated": self.is_authenticated(handler),
        }

    def is_authenticated(self, handler: BaseHTTPRequestHandler) -> bool:
        if not self.settings.auth_enabled:
            return True
        token = self._read_session_cookie(handler)
        if not token:
            return False
        now = time.time()
        with self._sessions_lock:
            expires_at = self._sessions.get(token)
            if expires_at is None:
                return False
            if expires_at <= now:
                self._sessions.pop(token, None)
                return False
            return True

    def login(self, password: str) -> tuple[bool, str | None, int | None]:
        if not self.settings.auth_enabled:
            return True, None, None
        if not secrets.compare_digest(password, self.settings.login_password):
            return False, None, None
        token = secrets.token_urlsafe(32)
        max_age = self.settings.auth_session_ttl_seconds
        expires_at = time.time() + max_age
        with self._sessions_lock:
            self._sessions[token] = expires_at
        return True, token, max_age

    def logout(self, handler: BaseHTTPRequestHandler) -> None:
        token = self._read_session_cookie(handler)
        if not token:
            return
        with self._sessions_lock:
            self._sessions.pop(token, None)

    def _read_session_cookie(self, handler: BaseHTTPRequestHandler) -> str | None:
        raw_cookie = handler.headers.get("Cookie")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(raw_cookie)
        except Exception:
            return None
        morsel = cookie.get(SESSION_COOKIE)
        if not morsel:
            return None
        return morsel.value


class WebUIRequestHandler(BaseHTTPRequestHandler):
    server_version = "CPACodexKeeperWebUI/1.0"

    @property
    def service(self) -> WebUIService:
        return self.server.service  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        self.service.runtime.logger.log("INFO", f"WebUI {self.address_string()} {format % args}")

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_text(INDEX_HTML, "text/html; charset=utf-8")
            return
        if self.path == "/assets/app.css":
            self._send_text(APP_CSS, "text/css; charset=utf-8")
            return
        if self.path == "/assets/app.js":
            self._send_text(APP_JS, "application/javascript; charset=utf-8")
            return
        if self.path == "/api/health":
            self._send_json({"ok": True, "timestamp": utc_now_iso()})
            return
        if self.path == "/api/auth/session":
            self._send_json(self.service.session_payload(self))
            return
        if self.path == "/api/status":
            if not self._require_auth():
                return
            self._send_json(self.service.runtime.status())
            return
        if self.path == "/api/tokens":
            if not self._require_auth():
                return
            self._send_json(self.service.runtime.token_summary())
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/auth/login":
            payload = self._read_json()
            ok, token, max_age = self.service.login(str(payload.get("password", "")))
            if not ok:
                self._send_json({"error": "invalid password"}, status=HTTPStatus.UNAUTHORIZED)
                return
            headers = {}
            if token and max_age:
                headers["Set-Cookie"] = (
                    f"{SESSION_COOKIE}={token}; Max-Age={max_age}; Path=/; "
                    "HttpOnly; SameSite=Lax"
                )
            self._send_json({"authenticated": True, "authEnabled": self.service.settings.auth_enabled}, headers=headers)
            return
        if self.path == "/api/auth/logout":
            self.service.logout(self)
            self._send_json(
                {"authenticated": False},
                headers={"Set-Cookie": f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"},
            )
            return
        if self.path == "/api/run":
            if not self._require_auth():
                return
            if self.service.runtime.running:
                self._send_json({"error": "inspection already running"}, status=HTTPStatus.CONFLICT)
                return
            self.service.runtime.run_once_async()
            self._send_json({"accepted": True, "timestamp": utc_now_iso()}, status=HTTPStatus.ACCEPTED)
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def _require_auth(self) -> bool:
        if self.service.is_authenticated(self):
            return True
        self._send_json({"error": "auth required"}, status=HTTPStatus.UNAUTHORIZED)
        return False

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _send_text(self, text: str, content_type: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(
        self,
        payload: dict[str, Any],
        *,
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


class WebUIServer(ThreadingHTTPServer):
    service: WebUIService


def serve_webui(settings: Settings, *, dry_run: bool = False, start_scheduler: bool = True) -> None:
    runtime = KeeperRuntime(settings=settings, dry_run=dry_run)
    server = WebUIServer((settings.app_host, settings.app_port), WebUIRequestHandler)
    server.service = WebUIService(runtime)
    if start_scheduler:
        runtime.start_scheduler()
    runtime.logger.log("INFO", f"WebUI listening on http://{settings.app_host}:{settings.app_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        runtime.logger.log("INFO", "WebUI stopped")
    finally:
        runtime.stop()
        server.server_close()
