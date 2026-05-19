"""Tests for config.py — configuration management."""

import sys
import os
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from config import (
    KEYS,
    SETUP_GUIDES,
    get_api_key,
    get_setup_guide,
    get_naver_credentials,
    list_configured_services,
    get_db_path,
    get_reports_dir,
)


class TestKeys(unittest.TestCase):

    def test_has_openai(self):
        self.assertIn("openai", KEYS)

    def test_has_perplexity(self):
        self.assertIn("perplexity", KEYS)

    def test_has_google(self):
        self.assertIn("google", KEYS)

    def test_has_anthropic(self):
        self.assertIn("anthropic", KEYS)

    def test_has_naver(self):
        self.assertIn("naver_client_id", KEYS)

    def test_has_dataforseo(self):
        self.assertIn("dataforseo", KEYS)

    def test_all_values_are_strings(self):
        for k, v in KEYS.items():
            self.assertIsInstance(v, str, f"{k} value is not string")


class TestSetupGuides(unittest.TestCase):

    def test_all_keys_have_guides(self):
        for service in KEYS:
            self.assertIn(service, SETUP_GUIDES)

    def test_guides_are_strings(self):
        for service, guide in SETUP_GUIDES.items():
            self.assertIsInstance(guide, str)

    def test_get_setup_guide_known(self):
        guide = get_setup_guide("openai")
        self.assertIn("openai", guide.lower())

    def test_get_setup_guide_unknown(self):
        guide = get_setup_guide("nonexistent")
        self.assertIn("three-o", guide)


class TestGetApiKey(unittest.TestCase):

    def test_missing_key_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_api_key("openai")
                self.assertIsNone(result)

    def test_existing_key_returns_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "openai_key.txt"
            key_file.write_text("sk-test123\n")
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_api_key("openai")
                self.assertEqual(result, "sk-test123")

    def test_naver_key_returns_client_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "naver_api.json"
            key_file.write_text(json.dumps({"client_id": "naver123", "client_secret": "secret"}))
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_api_key("naver_client_id")
                self.assertEqual(result, "naver123")

    def test_unknown_service(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_api_key("unknown_service")
                self.assertIsNone(result)

    def test_strips_whitespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "google_api_key.txt"
            key_file.write_text("  key-with-spaces  \n")
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_api_key("google")
                self.assertEqual(result, "key-with-spaces")


class TestGetNaverCredentials(unittest.TestCase):

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_naver_credentials()
                self.assertIsNone(result)

    def test_existing_returns_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            creds = {"client_id": "id", "client_secret": "secret"}
            (Path(tmpdir) / "naver_api.json").write_text(json.dumps(creds))
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = get_naver_credentials()
                self.assertEqual(result["client_id"], "id")
                self.assertEqual(result["client_secret"], "secret")


class TestListConfiguredServices(unittest.TestCase):

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = list_configured_services()
                self.assertEqual(result, [])

    def test_one_service(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "openai_key.txt").write_text("key")
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = list_configured_services()
                self.assertIn("openai", result)

    def test_multiple_services(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "openai_key.txt").write_text("key")
            (Path(tmpdir) / "google_api_key.txt").write_text("key")
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                result = list_configured_services()
                self.assertIn("openai", result)
                self.assertIn("google", result)


class TestGetDbPath(unittest.TestCase):

    def test_returns_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("config.CONFIG_DIR", Path(tmpdir)):
                path = get_db_path()
                self.assertTrue(str(path).endswith("three_o.db"))
                self.assertTrue(path.parent.exists())


class TestGetReportsDir(unittest.TestCase):

    def test_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("config.Path.cwd", return_value=Path(tmpdir)):
                reports = get_reports_dir()
                self.assertTrue(reports.exists())
                self.assertTrue(reports.is_dir())


if __name__ == "__main__":
    unittest.main()
