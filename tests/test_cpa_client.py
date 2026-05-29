import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.cpa_client import CPAClient


class CPAClientTests(unittest.TestCase):
    @patch("src.cpa_client.requests.request")
    def test_requests_do_not_use_proxy(self, request_mock):
        request_mock.return_value = Mock(status_code=200, text="{}", json=Mock(return_value={}))
        client = CPAClient("https://example.com", "secret", max_retries=0)

        client.list_auth_files()

        kwargs = request_mock.call_args.kwargs
        self.assertNotIn("proxies", kwargs)

    def test_upload_auth_file_passes_name_via_params(self):
        client = CPAClient("https://example.com", "secret")
        client._request = Mock(return_value=Mock(status_code=200))

        token_data = {
            "email": "jamessnyder20000630+89730080@outlook.com",
            "access_token": "token",
        }

        ok = client.upload_auth_file("jamessnyder20000630+89730080@outlook.com.json", token_data)

        self.assertTrue(ok)
        client._request.assert_called_once_with(
            "POST",
            "/v0/management/auth-files",
            params={"name": "jamessnyder20000630+89730080@outlook.com.json"},
            data='{"email": "jamessnyder20000630+89730080@outlook.com", "access_token": "token"}',
        )


if __name__ == "__main__":
    unittest.main()
