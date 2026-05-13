"""Tests for seo_robots.py — robots.txt analysis."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from seo_robots import parse_robots_txt, check_bot_access, analyze_robots, AI_BOTS


class TestAIBotsConstant(unittest.TestCase):

    def test_has_gptbot(self):
        self.assertIn("GPTBot", AI_BOTS)

    def test_has_anthropic(self):
        self.assertIn("Anthropic-AI", AI_BOTS)

    def test_has_google_extended(self):
        self.assertIn("Google-Extended", AI_BOTS)

    def test_has_perplexity(self):
        self.assertIn("PerplexityBot", AI_BOTS)

    def test_has_googlebot(self):
        self.assertIn("Googlebot", AI_BOTS)

    def test_has_yeti(self):
        self.assertIn("Yeti", AI_BOTS)

    def test_count(self):
        self.assertEqual(len(AI_BOTS), 7)


class TestParseRobotsTxt(unittest.TestCase):

    def test_empty_content(self):
        self.assertEqual(parse_robots_txt(""), [])

    def test_comment_only(self):
        self.assertEqual(parse_robots_txt("# just a comment"), [])

    def test_single_disallow(self):
        content = "User-agent: *\nDisallow: /private"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["agent"], "*")
        self.assertEqual(rules[0]["directive"], "disallow")
        self.assertEqual(rules[0]["path"], "/private")

    def test_single_allow(self):
        content = "User-agent: Googlebot\nAllow: /public"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["agent"], "Googlebot")
        self.assertEqual(rules[0]["directive"], "allow")
        self.assertEqual(rules[0]["path"], "/public")

    def test_multiple_agents(self):
        content = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: Googlebot\nDisallow: /admin"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["agent"], "GPTBot")
        self.assertEqual(rules[1]["agent"], "Googlebot")

    def test_sitemap_directive(self):
        content = "User-agent: *\nDisallow:\nSitemap: https://example.com/sitemap.xml"
        rules = parse_robots_txt(content)
        sitemap_rules = [r for r in rules if r["directive"] == "sitemap"]
        self.assertEqual(len(sitemap_rules), 1)
        self.assertIn("sitemap.xml", sitemap_rules[0]["path"])
        self.assertIsNone(sitemap_rules[0]["agent"])

    def test_empty_disallow(self):
        content = "User-agent: *\nDisallow:"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["path"], "")

    def test_mixed_case(self):
        content = "USER-AGENT: Googlebot\nDISALLOW: /secret"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["agent"], "Googlebot")

    def test_comments_interspersed(self):
        content = "# Comment\nUser-agent: *\n# Another comment\nDisallow: /admin"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["path"], "/admin")

    def test_disallow_without_agent_ignored(self):
        content = "Disallow: /orphan"
        rules = parse_robots_txt(content)
        self.assertEqual(len(rules), 0)

    def test_multiple_sitemaps(self):
        content = "User-agent: *\nDisallow:\nSitemap: https://a.com/s1.xml\nSitemap: https://a.com/s2.xml"
        rules = parse_robots_txt(content)
        sitemap_rules = [r for r in rules if r["directive"] == "sitemap"]
        self.assertEqual(len(sitemap_rules), 2)

    def test_full_block_ai_bots(self):
        content = (
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: Anthropic-AI\nDisallow: /\n\n"
            "User-agent: PerplexityBot\nDisallow: /\n"
        )
        rules = parse_robots_txt(content)
        disallow_all = [r for r in rules if r["directive"] == "disallow" and r["path"] == "/"]
        self.assertEqual(len(disallow_all), 3)


class TestCheckBotAccess(unittest.TestCase):

    def test_blocked_specific(self):
        rules = [{"agent": "GPTBot", "directive": "disallow", "path": "/"}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "blocked")

    def test_allowed_no_rules(self):
        self.assertEqual(check_bot_access([], "GPTBot"), "allowed")

    def test_partial_block(self):
        rules = [{"agent": "GPTBot", "directive": "disallow", "path": "/api"}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "partial")

    def test_wildcard_block(self):
        rules = [{"agent": "*", "directive": "disallow", "path": "/"}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "blocked")

    def test_specific_overrides_wildcard(self):
        rules = [
            {"agent": "*", "directive": "disallow", "path": "/"},
            {"agent": "Googlebot", "directive": "allow", "path": "/"},
        ]
        self.assertEqual(check_bot_access(rules, "Googlebot"), "allowed")

    def test_case_insensitive_match(self):
        rules = [{"agent": "gptbot", "directive": "disallow", "path": "/"}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "blocked")

    def test_different_bot_not_affected(self):
        rules = [{"agent": "GPTBot", "directive": "disallow", "path": "/"}]
        self.assertEqual(check_bot_access(rules, "Googlebot"), "allowed")

    def test_wildcard_allowed_when_no_disallow(self):
        rules = [{"agent": "*", "directive": "allow", "path": "/"}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "allowed")

    def test_empty_path_disallow_not_block(self):
        rules = [{"agent": "GPTBot", "directive": "disallow", "path": ""}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "allowed")

    def test_sitemap_rules_ignored(self):
        rules = [{"agent": None, "directive": "sitemap", "path": "https://a.com/sitemap.xml"}]
        self.assertEqual(check_bot_access(rules, "GPTBot"), "allowed")


class TestAnalyzeRobots(unittest.TestCase):

    def _mock_fetch(self, content, status=200):
        return {"success": True, "html": content, "status_code": status}

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_no_robots_txt(self, mock_fetch, mock_validate):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = analyze_robots("https://example.com")
        self.assertTrue(result["success"])
        self.assertFalse(result["exists"])
        self.assertEqual(result["score"], 50)

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_basic_robots(self, mock_fetch, mock_validate):
        mock_fetch.return_value = self._mock_fetch("User-agent: *\nDisallow:")
        result = analyze_robots("https://example.com")
        self.assertTrue(result["success"])
        self.assertTrue(result["exists"])
        self.assertEqual(result["score"], 100)

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_ai_bot_blocked_score(self, mock_fetch, mock_validate):
        content = "User-agent: GPTBot\nDisallow: /\nUser-agent: Anthropic-AI\nDisallow: /"
        mock_fetch.return_value = self._mock_fetch(content)
        result = analyze_robots("https://example.com")
        self.assertEqual(result["score"], 80)

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_googlebot_blocked_critical(self, mock_fetch, mock_validate):
        content = "User-agent: Googlebot\nDisallow: /"
        mock_fetch.return_value = self._mock_fetch(content)
        result = analyze_robots("https://example.com")
        self.assertTrue(result["score"] <= 75)
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Googlebot" in i for i in issues))

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_no_sitemap_issue(self, mock_fetch, mock_validate):
        mock_fetch.return_value = self._mock_fetch("User-agent: *\nDisallow: /admin")
        result = analyze_robots("https://example.com")
        issues = [i["message"] for i in result["issues"]]
        self.assertTrue(any("Sitemap" in i for i in issues))

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_sitemap_extracted(self, mock_fetch, mock_validate):
        content = "User-agent: *\nDisallow:\nSitemap: https://example.com/sitemap.xml"
        mock_fetch.return_value = self._mock_fetch(content)
        result = analyze_robots("https://example.com")
        self.assertEqual(len(result["sitemaps"]), 1)
        self.assertIn("sitemap.xml", result["sitemaps"][0])

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_bot_access_dict(self, mock_fetch, mock_validate):
        mock_fetch.return_value = self._mock_fetch("User-agent: *\nDisallow:")
        result = analyze_robots("https://example.com")
        self.assertIn("bot_access", result)
        for bot in AI_BOTS:
            self.assertIn(bot, result["bot_access"])

    @patch("seo_robots.validate_url", return_value={"valid": False, "error": "bad url"})
    def test_invalid_url(self, mock_validate):
        result = analyze_robots("not-a-url")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_all_ai_blocked_score(self, mock_fetch, mock_validate):
        content = (
            "User-agent: GPTBot\nDisallow: /\n"
            "User-agent: Anthropic-AI\nDisallow: /\n"
            "User-agent: Google-Extended\nDisallow: /\n"
            "User-agent: PerplexityBot\nDisallow: /\n"
        )
        mock_fetch.return_value = self._mock_fetch(content)
        result = analyze_robots("https://example.com")
        self.assertEqual(result["score"], 60)

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_no_robots_bot_access_message(self, mock_fetch, mock_validate):
        mock_fetch.return_value = {"success": True, "html": "", "status_code": 404}
        result = analyze_robots("https://example.com")
        self.assertFalse(result["exists"])
        for bot in AI_BOTS:
            self.assertIn("no robots.txt", result["bot_access"][bot])

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_rules_count(self, mock_fetch, mock_validate):
        content = "User-agent: *\nDisallow: /a\nDisallow: /b\nDisallow: /c"
        mock_fetch.return_value = self._mock_fetch(content)
        result = analyze_robots("https://example.com")
        self.assertEqual(result["rules_count"], 3)

    @patch("seo_robots.validate_url", return_value={"valid": True})
    @patch("seo_robots.fetch_page")
    def test_blocked_ai_issue_lists_bots(self, mock_fetch, mock_validate):
        content = "User-agent: GPTBot\nDisallow: /\nUser-agent: PerplexityBot\nDisallow: /"
        mock_fetch.return_value = self._mock_fetch(content)
        result = analyze_robots("https://example.com")
        ai_issues = [i for i in result["issues"] if "AI bots" in i["message"]]
        self.assertEqual(len(ai_issues), 1)
        self.assertIn("GPTBot", ai_issues[0]["message"])
        self.assertIn("PerplexityBot", ai_issues[0]["message"])


if __name__ == "__main__":
    unittest.main()
