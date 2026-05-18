import os
from dataclasses import dataclass
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFAULT_INTERVAL_SECONDS = 1800
DEFAULT_QUOTA_THRESHOLD = 1
DEFAULT_EXPIRY_THRESHOLD_DAYS = 3
DEFAULT_USAGE_TIMEOUT_SECONDS = 15
DEFAULT_CPA_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 2
DEFAULT_WORKER_THREADS = 8
DEFAULT_ENABLE_REFRESH = True
DEFAULT_ENABLE_AUTO_DELETE = True
DEFAULT_WEBUI_ENABLED = False
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 8080
DEFAULT_AUTH_ENABLED = False
DEFAULT_AUTH_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_LOG_MAX_LINES = 500
PROJECT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
PROJECT_CONFIG_FILE = Path(__file__).resolve().parents[1] / "config.yml"

CONFIG_KEY_ALIASES = {
    "cpa.endpoint": "CPA_ENDPOINT",
    "cpa.token": "CPA_TOKEN",
    "cpa.proxy": "CPA_PROXY",
    "cpa.interval": "CPA_INTERVAL",
    "cpa.quota_threshold": "CPA_QUOTA_THRESHOLD",
    "cpa.expiry_threshold_days": "CPA_EXPIRY_THRESHOLD_DAYS",
    "cpa.enable_refresh": "CPA_ENABLE_REFRESH",
    "cpa.enable_auto_delete": "CPA_ENABLE_AUTO_DELETE",
    "cpa.http_timeout": "CPA_HTTP_TIMEOUT",
    "cpa.usage_timeout": "CPA_USAGE_TIMEOUT",
    "cpa.max_retries": "CPA_MAX_RETRIES",
    "cpa.worker_threads": "CPA_WORKER_THREADS",
    "webui.enabled": "WEBUI_ENABLED",
    "webui.host": "APP_HOST",
    "webui.port": "APP_PORT",
    "webui.log_max_lines": "LOG_MAX_LINES",
    "auth.enabled": "AUTH_ENABLED",
    "auth.login_password": "LOGIN_PASSWORD",
    "auth.session_ttl": "AUTH_SESSION_TTL",
}


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
    enable_auto_delete: bool = DEFAULT_ENABLE_AUTO_DELETE
    webui_enabled: bool = DEFAULT_WEBUI_ENABLED
    app_host: str = DEFAULT_APP_HOST
    app_port: int = DEFAULT_APP_PORT
    auth_enabled: bool = DEFAULT_AUTH_ENABLED
    login_password: str = ""
    auth_session_ttl_seconds: int = DEFAULT_AUTH_SESSION_TTL_SECONDS
    log_max_lines: int = DEFAULT_LOG_MAX_LINES


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


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for idx, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == "#" and quote is None and (idx == 0 or value[idx - 1].isspace()):
            return value[:idx].rstrip()
    return value.strip()


def _normalize_yaml_value(value: str) -> str:
    value = _strip_yaml_comment(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _read_project_config_file(config_file: Path | None = None) -> dict[str, str]:
    target = config_file or PROJECT_CONFIG_FILE
    if not target.exists():
        return {}

    values: dict[str, str] = {}
    current_section: str | None = None
    for line_no, raw_line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if ":" not in stripped:
            raise SettingsError(f"{target.name}:{line_no} must use key: value syntax")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if not key:
            raise SettingsError(f"{target.name}:{line_no} has an empty key")

        value = _normalize_yaml_value(raw_value.strip())
        if indent == 0 and value == "":
            current_section = key.lower()
            continue
        if value == "":
            continue

        normalized_key = key.upper() if indent == 0 else CONFIG_KEY_ALIASES.get(f"{current_section}.{key.lower()}")
        if normalized_key is None:
            normalized_key = f"{current_section}.{key.lower()}"
        normalized_key = CONFIG_KEY_ALIASES.get(normalized_key.lower(), normalized_key)
        values[normalized_key] = value
    return values


def _get_config_value(name: str, env_values: dict[str, str], config_values: dict[str, str]) -> str | None:
    config_value = config_values.get(name)
    if config_value not in (None, ""):
        return config_value
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    return env_values.get(name)


def _read_int(
    name: str,
    default: int,
    env_values: dict[str, str],
    config_values: dict[str, str],
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    raw = _get_config_value(name, env_values, config_values)
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


def _read_bool(name: str, default: bool, env_values: dict[str, str], config_values: dict[str, str]) -> bool:
    raw = _get_config_value(name, env_values, config_values)
    if raw in (None, ""):
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"{name} must be a boolean")


def _read_duration_seconds(name: str, default: int, env_values: dict[str, str], config_values: dict[str, str]) -> int:
    raw = _get_config_value(name, env_values, config_values)
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


def _read_string(name: str, default: str, env_values: dict[str, str], config_values: dict[str, str]) -> str:
    return (_get_config_value(name, env_values, config_values) or default).strip()


def _format_yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    text = str(value)
    if text == "":
        return ""
    if any(char in text for char in ["#", ":", "\n", '"', "'"]) or text != text.strip():
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _find_active_section(lines: list[str], section: str) -> tuple[int, int] | None:
    section_name = section.lower()
    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, raw_value = stripped.split(":", 1)
        if indent == 0 and key.strip().lower() == section_name and _normalize_yaml_value(raw_value.strip()) == "":
            end = len(lines)
            for next_idx in range(idx + 1, len(lines)):
                next_line = lines[next_idx]
                next_stripped = next_line.strip()
                if not next_stripped or next_stripped.startswith("#"):
                    continue
                next_indent = len(next_line) - len(next_line.lstrip(" "))
                if next_indent == 0:
                    end = next_idx
                    break
            return idx, end
    return None


def update_config_file(
    updates: Mapping[str, Mapping[str, Any]],
    config_file: Path | None = None,
) -> None:
    target = config_file or PROJECT_CONFIG_FILE
    lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []

    for section, values in updates.items():
        if not values:
            continue
        normalized_values = {key.lower(): _format_yaml_scalar(value) for key, value in values.items()}
        section_range = _find_active_section(lines, section)
        if section_range is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"{section}:")
            for key, value in normalized_values.items():
                lines.append(f"  {key}: {value}")
            continue

        start, end = section_range
        present_keys: set[str] = set()
        for idx in range(start + 1, end):
            raw_line = lines[idx]
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if indent == 0:
                continue
            key = stripped.split(":", 1)[0].strip().lower()
            if key in normalized_values:
                lines[idx] = f"  {key}: {normalized_values[key]}"
                present_keys.add(key)

        insert_at = end
        for key, value in normalized_values.items():
            if key not in present_keys:
                lines.insert(insert_at, f"  {key}: {value}")
                insert_at += 1

    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def load_settings(env_file: Path | None = None, config_file: Path | None = None) -> Settings:
    env_values = _read_project_env_file(env_file)
    config_values = _read_project_config_file(config_file)
    endpoint = (_get_config_value("CPA_ENDPOINT", env_values, config_values) or "").strip().rstrip("/")
    token = (_get_config_value("CPA_TOKEN", env_values, config_values) or "").strip()
    proxy = (_get_config_value("CPA_PROXY", env_values, config_values) or "").strip() or None
    auth_enabled = _read_bool("AUTH_ENABLED", DEFAULT_AUTH_ENABLED, env_values, config_values)
    login_password = (_get_config_value("LOGIN_PASSWORD", env_values, config_values) or "").strip()

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
        interval_seconds=_read_int("CPA_INTERVAL", DEFAULT_INTERVAL_SECONDS, env_values, config_values, minimum=1),
        quota_threshold=_read_int(
            "CPA_QUOTA_THRESHOLD",
            DEFAULT_QUOTA_THRESHOLD,
            env_values,
            config_values,
            minimum=0,
            maximum=100,
        ),
        expiry_threshold_days=_read_int(
            "CPA_EXPIRY_THRESHOLD_DAYS",
            DEFAULT_EXPIRY_THRESHOLD_DAYS,
            env_values,
            config_values,
            minimum=0,
        ),
        usage_timeout_seconds=_read_int(
            "CPA_USAGE_TIMEOUT",
            DEFAULT_USAGE_TIMEOUT_SECONDS,
            env_values,
            config_values,
            minimum=1,
        ),
        cpa_timeout_seconds=_read_int(
            "CPA_HTTP_TIMEOUT",
            DEFAULT_CPA_TIMEOUT_SECONDS,
            env_values,
            config_values,
            minimum=1,
        ),
        max_retries=_read_int("CPA_MAX_RETRIES", DEFAULT_MAX_RETRIES, env_values, config_values, minimum=0, maximum=5),
        worker_threads=_read_int("CPA_WORKER_THREADS", DEFAULT_WORKER_THREADS, env_values, config_values, minimum=1),
        enable_refresh=_read_bool("CPA_ENABLE_REFRESH", DEFAULT_ENABLE_REFRESH, env_values, config_values),
        enable_auto_delete=_read_bool("CPA_ENABLE_AUTO_DELETE", DEFAULT_ENABLE_AUTO_DELETE, env_values, config_values),
        webui_enabled=_read_bool("WEBUI_ENABLED", DEFAULT_WEBUI_ENABLED, env_values, config_values),
        app_host=_read_string("APP_HOST", DEFAULT_APP_HOST, env_values, config_values) or DEFAULT_APP_HOST,
        app_port=_read_int("APP_PORT", DEFAULT_APP_PORT, env_values, config_values, minimum=1, maximum=65535),
        auth_enabled=auth_enabled,
        login_password=login_password,
        auth_session_ttl_seconds=_read_duration_seconds(
            "AUTH_SESSION_TTL",
            DEFAULT_AUTH_SESSION_TTL_SECONDS,
            env_values,
            config_values,
        ),
        log_max_lines=_read_int("LOG_MAX_LINES", DEFAULT_LOG_MAX_LINES, env_values, config_values, minimum=1),
    )
