import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_INTERVAL_SECONDS = 1800
DEFAULT_QUOTA_THRESHOLD = 100
DEFAULT_EXPIRY_THRESHOLD_DAYS = 3
DEFAULT_USAGE_TIMEOUT_SECONDS = 15
DEFAULT_CPA_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 2
DEFAULT_WORKER_THREADS = 8
DEFAULT_ENABLE_REFRESH = True
DEFAULT_WEBUI_ENABLED = False
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 8080
DEFAULT_AUTH_ENABLED = False
DEFAULT_AUTH_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
PROJECT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class SettingsError(ValueError):
    pass


@dataclass(slots=True)
class Settings:
    cpa_endpoint: str
    cpa_token: str
    proxy: str | None = None
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    quota_threshold: int = DEFAULT_QUOTA_THRESHOLD
    expiry_threshold_days: int = DEFAULT_EXPIRY_THRESHOLD_DAYS
    usage_timeout_seconds: int = DEFAULT_USAGE_TIMEOUT_SECONDS
    cpa_timeout_seconds: int = DEFAULT_CPA_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    worker_threads: int = DEFAULT_WORKER_THREADS
    enable_refresh: bool = DEFAULT_ENABLE_REFRESH
    webui_enabled: bool = DEFAULT_WEBUI_ENABLED
    app_host: str = DEFAULT_APP_HOST
    app_port: int = DEFAULT_APP_PORT
    auth_enabled: bool = DEFAULT_AUTH_ENABLED
    login_password: str = ""
    auth_session_ttl_seconds: int = DEFAULT_AUTH_SESSION_TTL_SECONDS


def _read_project_env_file(env_file: Path | None = None) -> dict[str, str]:
    target = env_file or PROJECT_ENV_FILE
    if not target.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in target.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _get_config_value(name: str, env_values: dict[str, str]) -> str | None:
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    return env_values.get(name)


def _read_int(name: str, default: int, env_values: dict[str, str], *, minimum: int = 0, maximum: int | None = None) -> int:
    raw = _get_config_value(name, env_values)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer") from exc
    if value < minimum:
        raise SettingsError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise SettingsError(f"{name} must be <= {maximum}")
    return value


def _read_bool(name: str, default: bool, env_values: dict[str, str]) -> bool:
    raw = _get_config_value(name, env_values)
    if raw in (None, ""):
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"{name} must be a boolean")


def _read_duration_seconds(name: str, default: int, env_values: dict[str, str]) -> int:
    raw = _get_config_value(name, env_values)
    if raw in (None, ""):
        return default
    value = raw.strip().lower()
    unit_multipliers = {
        "s": 1,
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
    }
    try:
        if value[-1:] in unit_multipliers:
            seconds = int(value[:-1]) * unit_multipliers[value[-1]]
        else:
            seconds = int(value)
    except (ValueError, IndexError) as exc:
        raise SettingsError(f"{name} must be a duration such as 3600, 60m, 24h, or 7d") from exc
    if seconds <= 0:
        raise SettingsError(f"{name} must be positive")
    return seconds


def load_settings(env_file: Path | None = None) -> Settings:
    env_values = _read_project_env_file(env_file)
    endpoint = (_get_config_value("CPA_ENDPOINT", env_values) or "").strip().rstrip("/")
    token = (_get_config_value("CPA_TOKEN", env_values) or "").strip()
    proxy = (_get_config_value("CPA_PROXY", env_values) or "").strip() or None
    auth_enabled = _read_bool("AUTH_ENABLED", DEFAULT_AUTH_ENABLED, env_values)
    login_password = (_get_config_value("LOGIN_PASSWORD", env_values) or "").strip()

    if not endpoint:
        raise SettingsError("CPA_ENDPOINT is required")
    if not token:
        raise SettingsError("CPA_TOKEN is required")
    if not endpoint.startswith(("http://", "https://")):
        raise SettingsError("CPA_ENDPOINT must start with http:// or https://")
    if auth_enabled and not login_password:
        raise SettingsError("LOGIN_PASSWORD is required when AUTH_ENABLED is true")

    return Settings(
        cpa_endpoint=endpoint,
        cpa_token=token,
        proxy=proxy,
        interval_seconds=_read_int("CPA_INTERVAL", DEFAULT_INTERVAL_SECONDS, env_values, minimum=1),
        quota_threshold=_read_int("CPA_QUOTA_THRESHOLD", DEFAULT_QUOTA_THRESHOLD, env_values, minimum=0, maximum=100),
        expiry_threshold_days=_read_int("CPA_EXPIRY_THRESHOLD_DAYS", DEFAULT_EXPIRY_THRESHOLD_DAYS, env_values, minimum=0),
        usage_timeout_seconds=_read_int("CPA_USAGE_TIMEOUT", DEFAULT_USAGE_TIMEOUT_SECONDS, env_values, minimum=1),
        cpa_timeout_seconds=_read_int("CPA_HTTP_TIMEOUT", DEFAULT_CPA_TIMEOUT_SECONDS, env_values, minimum=1),
        max_retries=_read_int("CPA_MAX_RETRIES", DEFAULT_MAX_RETRIES, env_values, minimum=0, maximum=5),
        worker_threads=_read_int("CPA_WORKER_THREADS", DEFAULT_WORKER_THREADS, env_values, minimum=1),
        enable_refresh=_read_bool("CPA_ENABLE_REFRESH", DEFAULT_ENABLE_REFRESH, env_values),
        webui_enabled=_read_bool("WEBUI_ENABLED", DEFAULT_WEBUI_ENABLED, env_values),
        app_host=(_get_config_value("APP_HOST", env_values) or DEFAULT_APP_HOST).strip() or DEFAULT_APP_HOST,
        app_port=_read_int("APP_PORT", DEFAULT_APP_PORT, env_values, minimum=1, maximum=65535),
        auth_enabled=auth_enabled,
        login_password=login_password,
        auth_session_ttl_seconds=_read_duration_seconds("AUTH_SESSION_TTL", DEFAULT_AUTH_SESSION_TTL_SECONDS, env_values),
    )
