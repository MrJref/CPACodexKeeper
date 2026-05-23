import json
import secrets
import threading
import time
import tomllib
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from curl_cffi import requests

from .inspection_schedule import next_inspection_timestamp, schedule_description
from .logging_utils import ConsoleLogger, current_log_time
from .maintainer import CPACodexKeeper
from .settings import PROJECT_CONFIG_FILE, Settings, SettingsError, load_settings, update_config_file
from .webui_assets import APP_CSS, APP_JS, INDEX_HTML


SESSION_COOKIE = "cpacodexkeeper_session"
SCHEDULER_STOP_JOIN_TIMEOUT_SECONDS = 2


def _load_app_version() -> str:
    try:
        return package_version("cpacodexkeeper")
    except PackageNotFoundError:
        pass

    pyproject_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
    try:
        pyproject = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
        version = pyproject["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "unknown"
    return str(version)


APP_VERSION = _load_app_version()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_from_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def proxy_label(proxy: str | None) -> str | None:
    if not proxy:
        return None
    parsed = urlsplit(proxy)
    if not parsed.scheme or not parsed.netloc:
        return proxy
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, netloc, "", "", ""))


def _payload_int(payload: dict[str, Any], name: str, *, minimum: int = 0, maximum: int | None = None) -> int | None:
    if name not in payload:
        return None
    raw = payload.get(name)
    if raw in (None, ""):
        raise ValueError(f"{name} is required")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def _payload_optional_int(payload: dict[str, Any], name: str, *, minimum: int = 0, maximum: int | None = None) -> int | str | None:
    if name not in payload:
        return None
    raw = payload.get(name)
    if raw in (None, ""):
        return ""
    return _payload_int(payload, name, minimum=minimum, maximum=maximum)


def _payload_bool(payload: dict[str, Any], name: str) -> bool | None:
    if name not in payload:
        return None
    raw = payload.get(name)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{name} must be a boolean")


def _payload_string(payload: dict[str, Any], name: str, *, allow_empty: bool = True) -> str | None:
    if name not in payload:
        return None
    value = str(payload.get(name) or "").strip()
    if not allow_empty and not value:
        raise ValueError(f"{name} is required")
    return value


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = value


def _config_updates_from_payload(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cpa: dict[str, Any] = {}
    webui: dict[str, Any] = {}
    auth: dict[str, Any] = {}

    _set_if_present(cpa, "endpoint", _payload_string(payload, "cpaEndpoint", allow_empty=False))
    token = _payload_string(payload, "cpaToken", allow_empty=True)
    if token:
        cpa["token"] = token
    _set_if_present(cpa, "proxy", _payload_string(payload, "proxy", allow_empty=True))
    _set_if_present(cpa, "cron", _payload_string(payload, "cronExpression", allow_empty=False))
    _set_if_present(cpa, "interval_min", _payload_optional_int(payload, "intervalMinSeconds", minimum=1))
    _set_if_present(cpa, "interval_max", _payload_optional_int(payload, "intervalMaxSeconds", minimum=1))
    _set_if_present(cpa, "quota_threshold", _payload_int(payload, "quotaThreshold", minimum=0, maximum=100))
    _set_if_present(cpa, "expiry_threshold_days", _payload_int(payload, "expiryThresholdDays", minimum=0))
    _set_if_present(cpa, "enable_refresh", _payload_bool(payload, "enableRefresh"))
    _set_if_present(cpa, "enable_auto_delete", _payload_bool(payload, "enableAutoDelete"))
    _set_if_present(cpa, "http_timeout", _payload_int(payload, "cpaTimeoutSeconds", minimum=1))
    _set_if_present(cpa, "usage_timeout", _payload_int(payload, "usageTimeoutSeconds", minimum=1))
    _set_if_present(cpa, "max_retries", _payload_int(payload, "maxRetries", minimum=0, maximum=5))
    _set_if_present(cpa, "worker_threads", _payload_int(payload, "workerThreads", minimum=1))

    _set_if_present(webui, "enabled", _payload_bool(payload, "webuiEnabled"))
    _set_if_present(auth, "enabled", _payload_bool(payload, "authEnabled"))
    password = _payload_string(payload, "loginPassword", allow_empty=True)
    if password:
        auth["login_password"] = password
    _set_if_present(auth, "session_ttl", _payload_int(payload, "authSessionTtlSeconds", minimum=1))

    return {"cpa": cpa, "webui": webui, "auth": auth}


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

    def clear(self) -> None:
        with self._history_lock:
            self._history.clear()

    def set_max_lines(self, max_lines: int) -> None:
        self.max_lines = max_lines
        with self._history_lock:
            if len(self._history) > self.max_lines:
                del self._history[: len(self._history) - self.max_lines]

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
        self.logger = HistoryLogger(max_lines=settings.log_max_lines)
        self._run_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._proxy_test_lock = threading.Lock()
        self._stop_event = threading.Event()
        self.keeper = CPACodexKeeper(settings=settings, dry_run=dry_run, logger=self.logger, stop_event=self._stop_event)
        self._scheduler_thread: threading.Thread | None = None
        self.running = False
        self.round_no = 0
        self.last_started_at: float | None = None
        self.last_finished_at: float | None = None
        self.next_run_at: float | None = None
        self.last_error: str | None = None
        self.last_proxy_test: dict[str, Any] | None = None

    def apply_settings(self, settings: Settings) -> None:
        with self._state_lock:
            self.settings = settings
            self.logger.set_max_lines(settings.log_max_lines)
            self.keeper = CPACodexKeeper(settings=settings, dry_run=self.dry_run, logger=self.logger, stop_event=self._stop_event)
            scheduler_active = bool(self._scheduler_thread and self._scheduler_thread.is_alive() and not self._stop_event.is_set())
            self.next_run_at = next_inspection_timestamp(settings) if scheduler_active else self.next_run_at

    def config_payload(self) -> dict[str, Any]:
        return {
            "configPath": str(PROJECT_CONFIG_FILE),
            "values": {
                "cpaEndpoint": self.settings.cpa_endpoint,
                "cpaTokenConfigured": bool(self.settings.cpa_token),
                "proxy": self.settings.proxy or "",
                "cronExpression": self.settings.cron_expression,
                "intervalMinSeconds": self.settings.interval_min_seconds,
                "intervalMaxSeconds": self.settings.interval_max_seconds,
                "quotaThreshold": self.settings.quota_threshold,
                "expiryThresholdDays": self.settings.expiry_threshold_days,
                "enableRefresh": self.settings.enable_refresh,
                "enableAutoDelete": self.settings.enable_auto_delete,
                "usageTimeoutSeconds": self.settings.usage_timeout_seconds,
                "cpaTimeoutSeconds": self.settings.cpa_timeout_seconds,
                "maxRetries": self.settings.max_retries,
                "workerThreads": self.settings.worker_threads,
                "webuiEnabled": self.settings.webui_enabled,
                "logMaxLines": self.settings.log_max_lines,
                "authEnabled": self.settings.auth_enabled,
                "loginPasswordConfigured": bool(self.settings.login_password),
                "authSessionTtlSeconds": self.settings.auth_session_ttl_seconds,
            },
        }

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        updates = _config_updates_from_payload(payload)
        old_text = PROJECT_CONFIG_FILE.read_text(encoding="utf-8") if PROJECT_CONFIG_FILE.exists() else None
        try:
            update_config_file(updates)
            settings = load_settings()
        except Exception:
            if old_text is None:
                PROJECT_CONFIG_FILE.unlink(missing_ok=True)
            else:
                PROJECT_CONFIG_FILE.write_text(old_text, encoding="utf-8")
            raise
        self.apply_settings(settings)
        self.logger.log("INFO", "WebUI 配置已保存并热更新生效")
        return self.config_payload()

    def update_log_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        log_max_lines = _payload_int(payload, "logMaxLines", minimum=1)
        if log_max_lines is None:
            raise ValueError("logMaxLines is required")
        old_text = PROJECT_CONFIG_FILE.read_text(encoding="utf-8") if PROJECT_CONFIG_FILE.exists() else None
        try:
            update_config_file({"webui": {"log_max_lines": log_max_lines}})
            settings = load_settings()
        except Exception:
            if old_text is None:
                PROJECT_CONFIG_FILE.unlink(missing_ok=True)
            else:
                PROJECT_CONFIG_FILE.write_text(old_text, encoding="utf-8")
            raise
        self.apply_settings(settings)
        self.logger.log("INFO", f"WebUI 日志保留行数已更新为 {log_max_lines}")
        return self.config_payload()

    def scheduler_active(self) -> bool:
        return bool(self._scheduler_thread and self._scheduler_thread.is_alive() and not self._stop_event.is_set())

    def start_scheduler(self) -> bool:
        with self._state_lock:
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                return False
            self._stop_event.clear()
            self.keeper.clear_stop()
            self.next_run_at = None
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                name="cpacodexkeeper-scheduler",
                daemon=True,
            )
            thread = self._scheduler_thread
        thread.start()
        return True

    def stop_scheduler(self) -> bool:
        with self._state_lock:
            if not self._scheduler_thread or not self._scheduler_thread.is_alive() or self._stop_event.is_set():
                self.next_run_at = None
                return False
            self._stop_event.set()
            self.keeper.request_stop()
            self.next_run_at = None
            thread = self._scheduler_thread
        self.logger.log("INFO", "守护模式停止中")
        if thread is not threading.current_thread():
            thread.join(timeout=SCHEDULER_STOP_JOIN_TIMEOUT_SECONDS)
        return True

    def stop(self) -> None:
        self._stop_event.set()
        self.keeper.request_stop()
        thread = self._scheduler_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=SCHEDULER_STOP_JOIN_TIMEOUT_SECONDS)

    def _scheduler_loop(self) -> None:
        self.logger.log("INFO", f"守护模式启动，{schedule_description(self.settings)}")
        try:
            while not self._stop_event.is_set():
                with self._state_lock:
                    settings = self.settings
                    self.next_run_at = next_inspection_timestamp(settings)
                    next_run_at = self.next_run_at
                self.logger.log("INFO", f"下次自动巡检: {datetime.fromtimestamp(next_run_at).strftime('%Y-%m-%d %H:%M:%S')}")
                if self._stop_event.wait(max(0, next_run_at - time.time())):
                    break
                with self._state_lock:
                    self.round_no += 1
                    round_no = self.round_no
                    self.next_run_at = None
                self.logger.log("INFO", f"开始第 {round_no} 轮巡检")
                started = self._execute_round()
                if started:
                    self.logger.log("INFO", f"第 {round_no} 轮巡检结束，完成时间: {current_log_time()}")
        finally:
            with self._state_lock:
                self.next_run_at = None
            self.logger.log("INFO", "守护模式已停止")

    def run_once_async(self) -> bool:
        if not self.scheduler_active():
            self._stop_event.clear()
            self.keeper.clear_stop()
        thread = threading.Thread(target=self._execute_round, name="cpacodexkeeper-manual-run", daemon=True)
        thread.start()
        return True

    def clear_logs(self) -> None:
        self.logger.clear()

    def test_proxy_latency(self, proxy: str | None = None) -> dict[str, Any]:
        proxy = (proxy or self.settings.proxy or "").strip()
        if not proxy:
            result = {
                "ok": False,
                "configured": False,
                "proxy": None,
                "latencyMs": None,
                "error": "CPA_PROXY is not configured",
                "timestamp": utc_now_iso(),
            }
            with self._state_lock:
                self.last_proxy_test = result
            return result

        if not self._proxy_test_lock.acquire(blocking=False):
            result = {
                "ok": False,
                "configured": True,
                "proxy": proxy_label(proxy),
                "latencyMs": None,
                "error": "proxy test already running",
                "timestamp": utc_now_iso(),
            }
            with self._state_lock:
                self.last_proxy_test = result
            return result

        started = time.perf_counter()
        try:
            response = requests.get(
                "https://chatgpt.com/",
                proxies={"http": proxy, "https": proxy},
                impersonate="chrome",
                timeout=min(self.settings.usage_timeout_seconds, 10),
            )
            latency_ms = round((time.perf_counter() - started) * 1000)
            result = {
                "ok": response.status_code < 500,
                "configured": True,
                "proxy": proxy_label(proxy),
                "latencyMs": latency_ms,
                "statusCode": response.status_code,
                "error": None if response.status_code < 500 else f"HTTP {response.status_code}",
                "timestamp": utc_now_iso(),
            }
        except Exception as exc:
            result = {
                "ok": False,
                "configured": True,
                "proxy": proxy_label(proxy),
                "latencyMs": None,
                "error": str(exc),
                "timestamp": utc_now_iso(),
            }
        finally:
            self._proxy_test_lock.release()

        with self._state_lock:
            self.last_proxy_test = result
        return result

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
                "appVersion": APP_VERSION,
                "serviceRunning": self.scheduler_active(),
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
                    "cronExpression": self.settings.cron_expression,
                    "intervalMinSeconds": self.settings.interval_min_seconds,
                    "intervalMaxSeconds": self.settings.interval_max_seconds,
                    "scheduleDescription": schedule_description(self.settings),
                    "quotaThreshold": self.settings.quota_threshold,
                    "expiryThresholdDays": self.settings.expiry_threshold_days,
                    "enableRefresh": self.settings.enable_refresh,
                    "enableAutoDelete": self.settings.enable_auto_delete,
                    "usageTimeoutSeconds": self.settings.usage_timeout_seconds,
                    "cpaTimeoutSeconds": self.settings.cpa_timeout_seconds,
                    "maxRetries": self.settings.max_retries,
                    "workerThreads": self.settings.worker_threads,
                    "logMaxLines": self.settings.log_max_lines,
                    "proxyConfigured": bool(self.settings.proxy),
                    "proxy": proxy_label(self.settings.proxy),
                    "authEnabled": self.settings.auth_enabled,
                    "appPort": self.settings.app_port,
                },
                "proxyTest": self.last_proxy_test,
                "timestamp": utc_now_iso(),
            }

class WebUIService:
    def __init__(self, runtime: KeeperRuntime) -> None:
        self.runtime = runtime
        self._sessions: dict[str, float] = {}
        self._sessions_lock = threading.Lock()

    @property
    def settings(self) -> Settings:
        return self.runtime.settings

    def session_payload(self, handler: BaseHTTPRequestHandler) -> dict[str, Any]:
        return {
            "appVersion": APP_VERSION,
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
        return

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
        if self.path == "/api/config":
            if not self._require_auth():
                return
            self._send_json(self.service.runtime.config_payload())
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
            self._send_json(
                {"appVersion": APP_VERSION, "authenticated": True, "authEnabled": self.service.settings.auth_enabled},
                headers=headers,
            )
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
        if self.path == "/api/service/start":
            if not self._require_auth():
                return
            started = self.service.runtime.start_scheduler()
            self._send_json({"started": started, "serviceRunning": self.service.runtime.scheduler_active(), "timestamp": utc_now_iso()})
            return
        if self.path == "/api/service/stop":
            if not self._require_auth():
                return
            stopped = self.service.runtime.stop_scheduler()
            self._send_json({"stopped": stopped, "serviceRunning": self.service.runtime.scheduler_active(), "timestamp": utc_now_iso()})
            return
        if self.path == "/api/logs/clear":
            if not self._require_auth():
                return
            self.service.runtime.clear_logs()
            self._send_json({"cleared": True, "timestamp": utc_now_iso()})
            return
        if self.path == "/api/proxy/test":
            if not self._require_auth():
                return
            payload = self._read_json()
            self._send_json(self.service.runtime.test_proxy_latency(_payload_string(payload, "proxy", allow_empty=True)))
            return
        if self.path == "/api/config":
            if not self._require_auth():
                return
            try:
                config = self.service.runtime.update_config(self._read_json())
            except (SettingsError, ValueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except OSError as exc:
                self._send_json({"error": f"failed to write config.yml: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({"saved": True, "config": config, "timestamp": utc_now_iso()})
            return
        if self.path == "/api/log-settings":
            if not self._require_auth():
                return
            try:
                config = self.service.runtime.update_log_settings(self._read_json())
            except (SettingsError, ValueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except OSError as exc:
                self._send_json({"error": f"failed to write config.yml: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({"saved": True, "config": config, "timestamp": utc_now_iso()})
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
