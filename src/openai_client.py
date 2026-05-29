import threading
import time

from curl_cffi import requests

from .models import RequestResult, TokenQuota, UsageInfo
from .utils import brief_response_text


class OpenAIClient:
    USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
    REFRESH_URL = "https://auth.openai.com/oauth/token"
    CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
    REDIRECT_URI = "http://localhost:1455/auth/callback"
    IMPERSONATE = "chrome"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    )
    COMMON_BROWSER_HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    def __init__(
        self,
        *,
        proxy: str | None = None,
        timeout: int = 15,
        max_retries: int = 2,
        stop_event: threading.Event | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.stop_event = stop_event
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    def _request(self, method: str, url: str, **kwargs) -> RequestResult:
        last_error = None
        for attempt in range(self.max_retries + 1):
            if self.stop_event and self.stop_event.is_set():
                return RequestResult(status_code=None, error="stop requested")
            try:
                response = requests.request(
                    method,
                    url,
                    proxies=self.proxies,
                    impersonate=self.IMPERSONATE,
                    timeout=self.timeout,
                    **kwargs,
                )
                json_data = None
                try:
                    json_data = response.json()
                except (ValueError, TypeError):
                    pass
                if response.status_code >= 500 and attempt < self.max_retries:
                    if self.stop_event and self.stop_event.wait(1):
                        return RequestResult(status_code=None, error="stop requested")
                    if not self.stop_event:
                        time.sleep(1)
                    continue
                return RequestResult(
                    status_code=response.status_code,
                    body=response.text,
                    brief=brief_response_text(response),
                    json_data=json_data,
                )
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    if self.stop_event and self.stop_event.wait(1):
                        return RequestResult(status_code=None, error="stop requested")
                    if not self.stop_event:
                        time.sleep(1)
                    continue
        return RequestResult(status_code=None, error=last_error or "request failed")

    def check_usage(self, access_token: str, account_id: str | None = None) -> RequestResult:
        headers = {
            **self.COMMON_BROWSER_HEADERS,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=1, i",
        }
        if account_id:
            headers["Chatgpt-Account-Id"] = account_id
        return self._request("GET", self.USAGE_URL, headers=headers)

    def refresh_token(self, refresh_token: str) -> RequestResult:
        payload = {
            "redirect_uri": self.REDIRECT_URI,
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "refresh_token": refresh_token,
        }
        headers = {
            **self.COMMON_BROWSER_HEADERS,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://localhost:1455",
            "Referer": "http://localhost:1455/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Priority": "u=1, i",
        }
        return self._request("POST", self.REFRESH_URL, headers=headers, data=payload)


def parse_usage_info(result: RequestResult | dict | None) -> UsageInfo:
    if isinstance(result, RequestResult):
        body = result.json_data
    elif isinstance(result, dict):
        body = result.get("json") or result
    else:
        body = None

    if not isinstance(body, dict):
        return UsageInfo()

    rate_limit = body.get("rate_limit") or {}
    primary = rate_limit.get("primary_window") or {}
    secondary = rate_limit.get("secondary_window")
    credits = body.get("credits") or {}

    primary_window = TokenQuota(
        used_percent=_parse_used_percent(primary.get("used_percent")),
        limit_window_seconds=primary.get("limit_window_seconds"),
        reset_after_seconds=primary.get("reset_after_seconds"),
        reset_at=primary.get("reset_at"),
    )
    secondary_window = None
    if isinstance(secondary, dict):
        secondary_window = TokenQuota(
            used_percent=_parse_used_percent(secondary.get("used_percent")),
            limit_window_seconds=secondary.get("limit_window_seconds"),
            reset_after_seconds=secondary.get("reset_after_seconds"),
            reset_at=secondary.get("reset_at"),
        )

    return UsageInfo(
        plan_type=body.get("plan_type", "unknown"),
        primary_window=primary_window,
        secondary_window=secondary_window,
        has_credits=bool(credits.get("has_credits", False)),
        credits_balance=credits.get("balance"),
    )


def _parse_used_percent(value) -> float:
    if value in (None, ""):
        return 0
    if isinstance(value, str):
        value = value.strip().removesuffix("%")
    try:
        percent = float(value)
    except (TypeError, ValueError):
        return 0
    return min(100, max(0, percent))
