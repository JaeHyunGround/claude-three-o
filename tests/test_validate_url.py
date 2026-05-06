"""Tests for validate_url.py — URL validation and SSRF protection."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validate_url import validate_url


class TestValidateUrl(unittest.TestCase):

    def test_valid_http(self):
        result = validate_url("http://example.com")
        self.assertTrue(result["valid"])

    def test_valid_https(self):
        result = validate_url("https://example.com")
        self.assertTrue(result["valid"])

    def test_valid_with_path(self):
        result = validate_url("https://example.com/page/test")
        self.assertTrue(result["valid"])

    def test_valid_korean_domain(self):
        result = validate_url("https://naver.com")
        self.assertTrue(result["valid"])

    def test_invalid_no_scheme(self):
        result = validate_url("example.com")
        self.assertFalse(result["valid"])

    def test_invalid_empty(self):
        result = validate_url("")
        self.assertFalse(result["valid"])

    def test_invalid_ftp(self):
        result = validate_url("ftp://example.com")
        self.assertFalse(result["valid"])

    def test_ssrf_localhost(self):
        result = validate_url("http://localhost/admin")
        self.assertFalse(result["valid"])

    def test_ssrf_127(self):
        result = validate_url("http://127.0.0.1/secret")
        self.assertFalse(result["valid"])

    def test_ssrf_private_10(self):
        result = validate_url("http://10.0.0.1/internal")
        self.assertFalse(result["valid"])

    def test_ssrf_private_192(self):
        result = validate_url("http://192.168.1.1/admin")
        self.assertFalse(result["valid"])

    def test_ssrf_private_172(self):
        result = validate_url("http://172.16.0.1/internal")
        self.assertFalse(result["valid"])

    def test_ssrf_metadata(self):
        result = validate_url("http://169.254.169.254/metadata")
        self.assertFalse(result["valid"])

    def test_returns_normalized_url(self):
        result = validate_url("https://example.com")
        self.assertIn("url", result)

    def test_returns_error_on_invalid(self):
        result = validate_url("")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
