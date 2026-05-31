import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.openai_client import OpenAIClient


class FakeResponse:
    status_code = 200
    text = "{}"

    def json(self):
        return {}


class OpenAIClientTests(unittest.TestCase):
    @patch("src.openai_client.requests.request")
    def test_check_usage_uses_browser_like_headers(self, request_mock):
        request_mock.return_value = FakeResponse()
        client = OpenAIClient(proxy="http://127.0.0.1:7890", timeout=9, max_retries=0)

        client.check_usage("access-token", "account-id")

        _, _, kwargs = request_mock.mock_calls[0]
        headers = kwargs["headers"]
        self.assertEqual(kwargs["impersonate"], OpenAIClient.IMPERSONATE)
        self.assertEqual(kwargs["proxies"], {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"})
        self.assertEqual(kwargs["timeout"], 9)
        self.assertEqual(headers["Authorization"], "Bearer access-token")
        self.assertEqual(headers["Chatgpt-Account-Id"], "account-id")
        self.assertEqual(headers["Origin"], "https://chatgpt.com")
        self.assertEqual(headers["Referer"], "https://chatgpt.com/")
        self.assertIn("Chrome/", headers["User-Agent"])
        self.assertEqual(headers["sec-ch-ua-platform-version"], '"10.0.0"')
        self.assertEqual(headers["sec-ch-ua-arch"], '"x86_64"')
        self.assertTrue(headers["oai-device-id"])
        self.assertIn("traceparent", headers)
        self.assertIn("x-datadog-trace-id", headers)
        self.assertNotIn("Content-Type", headers)

    @patch("src.openai_client.requests.request")
    def test_refresh_token_uses_form_payload_and_browser_headers(self, request_mock):
        request_mock.return_value = FakeResponse()
        client = OpenAIClient(timeout=9, max_retries=0)

        client.refresh_token("refresh-token")

        method, url = request_mock.call_args.args[:2]
        kwargs = request_mock.call_args.kwargs
        headers = kwargs["headers"]
        self.assertEqual(method, "POST")
        self.assertEqual(url, OpenAIClient.REFRESH_URL)
        self.assertNotIn("json", kwargs)
        self.assertEqual(kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(kwargs["data"]["refresh_token"], "refresh-token")
        self.assertEqual(headers["Content-Type"], "application/x-www-form-urlencoded")
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(headers["Origin"], "http://localhost:1455")
        self.assertIn("Chrome/", headers["User-Agent"])
        self.assertEqual(kwargs["impersonate"], OpenAIClient.REFRESH_IMPERSONATE)
        self.assertEqual(headers["Sec-Fetch-Site"], "cross-site")
        self.assertTrue(headers["oai-device-id"])
        self.assertIn("traceparent", headers)

    @patch("src.openai_client.requests.request")
    def test_check_usage_accepts_extra_headers_without_sentinel(self, request_mock):
        request_mock.return_value = FakeResponse()
        client = OpenAIClient(
            sentinel_token="sentinel-token",
            extra_headers={"x-test-header": "test-value"},
            max_retries=0,
        )

        client.check_usage("access-token")

        headers = request_mock.call_args.kwargs["headers"]
        self.assertTrue(headers["oai-device-id"])
        self.assertNotIn("openai-sentinel-token", headers)
        self.assertEqual(headers["x-test-header"], "test-value")

    @patch("src.openai_client.requests.request")
    def test_check_usage_generates_device_id_when_not_configured(self, request_mock):
        request_mock.return_value = FakeResponse()
        client = OpenAIClient(max_retries=0)

        client.check_usage("access-token")
        first_device_id = request_mock.call_args.kwargs["headers"]["oai-device-id"]
        client.check_usage("access-token")
        second_device_id = request_mock.call_args.kwargs["headers"]["oai-device-id"]

        self.assertTrue(first_device_id)
        self.assertEqual(first_device_id, second_device_id)


if __name__ == "__main__":
    unittest.main()
