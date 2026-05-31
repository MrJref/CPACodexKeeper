import random
import threading
import time
import uuid
from collections.abc import Mapping

from curl_cffi import requests

from .models import RequestResult, TokenQuota, UsageInfo
from .utils import brief_response_text


class OpenAIClient:
    USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
    REFRESH_URL = "https://auth.openai.com/oauth/token"
    CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
    REDIRECT_URI = "http://localhost:1455/auth/callback"
    IMPERSONATE = "chrome"
    REFRESH_IMPERSONATE = "chrome110"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    )
    SEC_CH_UA = '"Google Chrome";v="145", "Not?A_Brand";v="8", "Chromium";v="145"'
    SEC_CH_UA_FULL = '"Chromium";v="145.0.0.0", "Not:A-Brand";v="99.0.0.0", "Google Chrome";v="145.0.0.0"'

    def __init__(
        self,
        *,
        proxy: str | None = None,
        timeout: int = 15,
        max_retries: int = 2,
        stop_event: threading.Event | None = None,
        sentinel_token: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.stop_event = stop_event
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.device_id = str(uuid.uuid4())
        self.sentinel_token = (sentinel_token or "").strip()
        self.extra_headers = dict(extra_headers or {})

    @classmethod
    def _trace_headers(cls) -> dict[str, str]:
        trace_id = str(random.getrandbits(64))
        parent_id = str(random.getrandbits(64))
        return {
            "traceparent": f"00-{uuid.uuid4().hex}-{format(int(parent_id), '016x')}-01",
            "tracestate": "dd=s:1;o:rum",
            "x-datadog-origin": "rum",
            "x-datadog-parent-id": parent_id,
            "x-datadog-sampling-priority": "1",
            "x-datadog-trace-id": trace_id,
        }

    def _browser_headers(
        self,
        *,
        accept: str = "application/json",
        content_type: str | None = None,
        origin: str | None = None,
        referer: str | None = None,
        fetch_site: str = "same-origin",
        fetch_dest: str = "empty",
        fetch_mode: str = "cors",
        include_sentinel: bool = False,
    ) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Priority": "u=1, i",
            "User-Agent": self.USER_AGENT,
            "sec-ch-ua": self.SEC_CH_UA,
            "sec-ch-ua-arch": '"x86_64"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version-list": self.SEC_CH_UA_FULL,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"10.0.0"',
            "Sec-Fetch-Dest": fetch_dest,
            "Sec-Fetch-Mode": fetch_mode,
            "Sec-Fetch-Site": fetch_site,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if origin:
            headers["Origin"] = origin
        if referer:
            headers["Referer"] = referer
        if self.device_id:
            headers["oai-device-id"] = self.device_id
        if include_sentinel and self.sentinel_token:
            headers["openai-sentinel-token"] = self.sentinel_token
        headers.update(self._trace_headers())
        headers.update(self.extra_headers)
        return headers

    def _request(self, method: str, url: str, *, impersonate: str | None = None, **kwargs) -> RequestResult:
        last_error = None
        for attempt in range(self.max_retries + 1):
            if self.stop_event and self.stop_event.is_set():
                return RequestResult(status_code=None, error="stop requested")
            try:
                response = requests.request(
                    method,
                    url,
                    proxies=self.proxies,
                    impersonate=impersonate or self.IMPERSONATE,
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
        headers = self._browser_headers(
            origin="https://chatgpt.com",
            referer="https://chatgpt.com/",
            include_sentinel=False,
        )
        headers["Authorization"] = f"Bearer {access_token}"
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
        headers = self._browser_headers(
            content_type="application/x-www-form-urlencoded",
            origin="http://localhost:1455",
            referer="http://localhost:1455/",
            fetch_site="cross-site",
            include_sentinel=False,
        )
        return self._request("POST", self.REFRESH_URL, impersonate=self.REFRESH_IMPERSONATE, headers=headers, data=payload)


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
