"""Tests for fetch_page.py — web page fetcher with bot comparison."""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import fetch_page, fetch_with_bot_comparison, clear_cache, USER_AGENTS, DEFAULT_TIMEOUT


class TestUserAgents(unittest.TestCase):

    def test_has_default(self):
        self.assertIn("default", USER_AGENTS)

    def test_has_googlebot(self):
        self.assertIn("googlebot", USER_AGENTS)

    def test_has_gptbot(self):
        self.assertIn("gptbot", USER_AGENTS)

    def test_has_anthropic(self):
        self.assertIn("anthropic", USER_AGENTS)

    def test_has_perplexity(self):
        self.assertIn("perplexity", USER_AGENTS)

    def test_default_timeout(self):
        self.assertEqual(DEFAULT_TIMEOUT, 15)


class TestFetchPage(unittest.TestCase):

    def setUp(self):
        clear_cache()

    @patch("fetch_page.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = fetch_page("bad-url")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_successful_fetch(self, mock_client_cls, mock_val):
        mock_response = MagicMock()
        mock_response.url = "https://x.com"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html>Hello</html>"
        mock_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertIn("html", result)
        self.assertIn("elapsed_seconds", result)

    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_timeout_error(self, mock_client_cls, mock_val):
        import httpx
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com")
        self.assertFalse(result["success"])
        self.assertIn("Timeout", result["error"])

    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_request_error(self, mock_client_cls, mock_val):
        import httpx
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.RequestError("connection failed")
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com")
        self.assertFalse(result["success"])

    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_result_keys(self, mock_client_cls, mock_val):
        mock_response = MagicMock()
        mock_response.url = "https://x.com"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html></html>"
        mock_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com")
        for key in ["success", "url", "status_code", "content_type", "content_length",
                     "elapsed_seconds", "headers", "html", "redirects"]:
            self.assertIn(key, result)

    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_redirects_tracked(self, mock_client_cls, mock_val):
        redirect = MagicMock()
        redirect.url = "https://old.com"
        mock_response = MagicMock()
        mock_response.url = "https://new.com"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.history = [redirect]

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://old.com")
        self.assertEqual(len(result["redirects"]), 1)


class TestRetryLogic(unittest.TestCase):

    def setUp(self):
        clear_cache()

    @patch("fetch_page._RETRY_DELAY", 0)
    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_retry_on_timeout_then_succeed(self, mock_client_cls, mock_val):
        import httpx
        mock_response = MagicMock()
        mock_response.url = "https://x.com"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "<html></html>"
        mock_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [httpx.TimeoutException("timeout"), mock_response]
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com", retries=1)
        self.assertTrue(result["success"])
        self.assertEqual(result["retries_used"], 1)

    @patch("fetch_page._RETRY_DELAY", 0)
    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_retry_exhausted(self, mock_client_cls, mock_val):
        import httpx
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com", retries=2)
        self.assertFalse(result["success"])
        self.assertEqual(result["retries_used"], 2)
        self.assertIn("Timeout", result["error"])

    @patch("fetch_page._RETRY_DELAY", 0)
    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_retry_on_500_then_succeed(self, mock_client_cls, mock_val):
        error_response = MagicMock()
        error_response.url = "https://x.com"
        error_response.status_code = 500
        error_response.headers = {}
        error_response.text = "error"
        error_response.history = []

        ok_response = MagicMock()
        ok_response.url = "https://x.com"
        ok_response.status_code = 200
        ok_response.headers = {}
        ok_response.text = "<html></html>"
        ok_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [error_response, ok_response]
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com", retries=1)
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)

    @patch("fetch_page._RETRY_DELAY", 0)
    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_no_retry_on_success(self, mock_client_cls, mock_val):
        mock_response = MagicMock()
        mock_response.url = "https://x.com"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "<html></html>"
        mock_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com", retries=2)
        self.assertTrue(result["success"])
        self.assertNotIn("retries_used", result)

    @patch("fetch_page._RETRY_DELAY", 0)
    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_no_retry_on_404(self, mock_client_cls, mock_val):
        mock_response = MagicMock()
        mock_response.url = "https://x.com"
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "not found"
        mock_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com", retries=2)
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 404)
        self.assertEqual(mock_client.get.call_count, 1)

    @patch("fetch_page._RETRY_DELAY", 0)
    @patch("fetch_page.validate_url", return_value={"valid": True})
    @patch("fetch_page.httpx.Client")
    def test_retry_on_connection_error(self, mock_client_cls, mock_val):
        import httpx
        mock_response = MagicMock()
        mock_response.url = "https://x.com"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "<html></html>"
        mock_response.history = []

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [httpx.RequestError("conn reset"), mock_response]
        mock_client_cls.return_value = mock_client

        result = fetch_page("https://x.com", retries=1)
        self.assertTrue(result["success"])


class TestFetchWithBotComparison(unittest.TestCase):

    @patch("fetch_page.fetch_page")
    def test_checks_all_bots(self, mock_fetch):
        mock_fetch.return_value = {"status_code": 200, "content_length": 1000}
        results = fetch_with_bot_comparison("https://x.com")
        for bot in ["default", "googlebot", "gptbot", "anthropic", "perplexity"]:
            self.assertIn(bot, results)

    @patch("fetch_page.fetch_page")
    def test_blocked_detection(self, mock_fetch):
        mock_fetch.return_value = {"status_code": 403, "content_length": 0}
        results = fetch_with_bot_comparison("https://x.com")
        self.assertTrue(results["default"]["blocked"])

    @patch("fetch_page.fetch_page")
    def test_not_blocked(self, mock_fetch):
        mock_fetch.return_value = {"status_code": 200, "content_length": 5000}
        results = fetch_with_bot_comparison("https://x.com")
        self.assertFalse(results["default"]["blocked"])


if __name__ == "__main__":
    unittest.main()
