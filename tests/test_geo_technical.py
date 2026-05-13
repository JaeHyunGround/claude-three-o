"""Tests for geo_technical.py — AI crawler technical accessibility."""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_technical import (
    check_ssr_rendering, check_response_performance,
    check_captcha_detection, check_robots_for_ai,
    analyze_technical_accessibility, AI_CRAWLERS,
)


class TestAICrawlers(unittest.TestCase):

    def test_count(self):
        self.assertEqual(len(AI_CRAWLERS), 5)

    def test_has_gptbot(self):
        self.assertIn("GPTBot", AI_CRAWLERS)

    def test_has_anthropic(self):
        self.assertIn("Anthropic-AI", AI_CRAWLERS)

    def test_has_google_extended(self):
        self.assertIn("Google-Extended", AI_CRAWLERS)

    def test_has_perplexity(self):
        self.assertIn("PerplexityBot", AI_CRAWLERS)

    def test_has_yeti(self):
        self.assertIn("Yeti", AI_CRAWLERS)

    def test_all_have_provider(self):
        for name, info in AI_CRAWLERS.items():
            self.assertIn("provider", info, f"{name} missing provider")
            self.assertIn("ua", info, f"{name} missing ua")


class TestCheckSSRRendering(unittest.TestCase):

    def _html(self, body_content, extra_head=""):
        return f"<html><head>{extra_head}</head><body>{body_content}</body></html>"

    def test_good_ssr(self):
        body = " ".join(["word"] * 100)
        result = check_ssr_rendering(self._html(body))
        self.assertTrue(result["has_ssr_content"])
        self.assertEqual(result["ssr_status"], "good")

    def test_poor_ssr_spa(self):
        html = '<html><head><script src="/_next/static/chunk.js"></script></head><body><div id="root"></div></body></html>'
        result = check_ssr_rendering(html)
        self.assertFalse(result["has_ssr_content"])
        self.assertTrue(result["likely_spa"])
        self.assertEqual(result["ssr_status"], "poor")

    def test_empty_body(self):
        result = check_ssr_rendering(self._html(""))
        self.assertFalse(result["has_ssr_content"])

    def test_detects_nextjs(self):
        html = self._html("content " * 60, '<script id="__NEXT_DATA__">{"props":{}}</script>')
        result = check_ssr_rendering(html)
        self.assertIn("Next.js", result["js_frameworks"])

    def test_detects_nuxtjs(self):
        html = self._html("content " * 60, '<script>window.__NUXT__={}</script>')
        result = check_ssr_rendering(html)
        self.assertIn("Nuxt.js", result["js_frameworks"])

    def test_detects_react(self):
        html = '<html><body><div data-reactroot>content ' + "word " * 60 + '</div></body></html>'
        result = check_ssr_rendering(html)
        self.assertIn("React", result["js_frameworks"])

    def test_detects_angular(self):
        html = '<html><body><div ng-app="myApp">content ' + "word " * 60 + '</div></body></html>'
        result = check_ssr_rendering(html)
        self.assertIn("Angular", result["js_frameworks"])

    def test_detects_vue(self):
        html = '<html><body><div data-v-abc123>content ' + "word " * 60 + '</div></body></html>'
        result = check_ssr_rendering(html)
        self.assertIn("Vue.js", result["js_frameworks"])

    def test_scripts_stripped_from_word_count(self):
        body = '<script>var x = "' + "word " * 200 + '";</script><p>short</p>'
        result = check_ssr_rendering(self._html(body))
        self.assertFalse(result["has_ssr_content"])

    def test_word_count(self):
        body = " ".join(["word"] * 75)
        result = check_ssr_rendering(self._html(body))
        self.assertGreaterEqual(result["word_count"], 75)

    def test_no_framework_detected(self):
        result = check_ssr_rendering(self._html("plain " * 60))
        self.assertEqual(result["js_frameworks"], [])

    def test_spa_empty_root_div(self):
        html = '<html><body><div id="app"></div></body></html>'
        result = check_ssr_rendering(html)
        self.assertTrue(result["likely_spa"])


class TestCheckResponsePerformance(unittest.TestCase):

    def test_fast(self):
        result = check_response_performance(0.2)
        self.assertEqual(result["status"], "fast")
        self.assertEqual(result["ttfb_ms"], 200)

    def test_acceptable(self):
        result = check_response_performance(1.0)
        self.assertEqual(result["status"], "acceptable")

    def test_slow(self):
        result = check_response_performance(2.0)
        self.assertEqual(result["status"], "slow")

    def test_very_slow(self):
        result = check_response_performance(5.0)
        self.assertEqual(result["status"], "very_slow")

    def test_boundary_500ms(self):
        result = check_response_performance(0.5)
        self.assertEqual(result["status"], "acceptable")

    def test_boundary_1500ms(self):
        result = check_response_performance(1.5)
        self.assertEqual(result["status"], "slow")

    def test_boundary_3000ms(self):
        result = check_response_performance(3.0)
        self.assertEqual(result["status"], "very_slow")

    def test_zero(self):
        result = check_response_performance(0)
        self.assertEqual(result["status"], "fast")
        self.assertEqual(result["ttfb_ms"], 0)


class TestCheckCaptchaDetection(unittest.TestCase):

    def test_no_captcha(self):
        result = check_captcha_detection("<html><body>Clean page</body></html>")
        self.assertFalse(result["has_captcha"])

    def test_recaptcha(self):
        html = '<html><body><div class="g-recaptcha"></div></body></html>'
        result = check_captcha_detection(html)
        self.assertTrue(result["has_captcha"])
        self.assertTrue(result["recaptcha"])

    def test_hcaptcha(self):
        html = '<html><body><div class="hcaptcha"></div></body></html>'
        result = check_captcha_detection(html)
        self.assertTrue(result["has_captcha"])

    def test_cloudflare(self):
        html = '<html><body><div class="challenge-platform"></div></body></html>'
        result = check_captcha_detection(html)
        self.assertTrue(result["has_captcha"])
        self.assertTrue(result["cloudflare_challenge"])

    def test_bot_detection(self):
        html = '<html><body><script src="bot-detection.js"></script></body></html>'
        result = check_captcha_detection(html)
        self.assertTrue(result["has_captcha"])
        self.assertTrue(result["bot_detection"])

    def test_multiple_signals(self):
        html = '<html><body><div class="recaptcha"></div><script src="anti-bot.js"></script></body></html>'
        result = check_captcha_detection(html)
        self.assertTrue(result["recaptcha"])
        self.assertTrue(result["bot_detection"])


class TestCheckRobotsForAI(unittest.TestCase):

    @patch("geo_technical.fetch_page")
    def test_no_robots(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "error": "404"}
        result = check_robots_for_ai("https://example.com")
        self.assertFalse(result["exists"])
        for crawler in AI_CRAWLERS:
            self.assertIn("allowed", result["crawler_status"][crawler])

    @patch("geo_technical.fetch_page")
    def test_all_allowed(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"}
        result = check_robots_for_ai("https://example.com")
        self.assertTrue(result["exists"])
        for crawler in AI_CRAWLERS:
            self.assertEqual(result["crawler_status"][crawler]["status"], "allowed")

    @patch("geo_technical.fetch_page")
    def test_specific_bot_blocked(self, mock_fetch):
        content = "User-agent: GPTBot\nDisallow: /"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": content}
        result = check_robots_for_ai("https://example.com")
        self.assertEqual(result["crawler_status"]["GPTBot"]["status"], "blocked")
        self.assertEqual(result["crawler_status"]["Anthropic-AI"]["status"], "allowed")

    @patch("geo_technical.fetch_page")
    def test_multiple_bots_blocked(self, mock_fetch):
        content = "User-agent: GPTBot\nDisallow: /\nUser-agent: Anthropic-AI\nDisallow: /"
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": content}
        result = check_robots_for_ai("https://example.com")
        self.assertEqual(result["crawler_status"]["GPTBot"]["status"], "blocked")
        self.assertEqual(result["crawler_status"]["Anthropic-AI"]["status"], "blocked")


class TestAnalyzeTechnicalAccessibility(unittest.TestCase):

    @patch("geo_technical.validate_url", return_value={"valid": False, "error": "bad"})
    def test_invalid_url(self, mock_val):
        result = analyze_technical_accessibility("bad")
        self.assertFalse(result["success"])

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_fetch_failure(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": False, "error": "timeout"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        self.assertFalse(result["success"])

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_good_page(self, mock_fetch, mock_val):
        body = "word " * 100
        html = f"<html><body>{body}</body></html>"
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "html": html, "elapsed_seconds": 0.3},
            {"success": True, "status_code": 200, "html": "# llms.txt content"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        self.assertTrue(result["success"])
        self.assertGreater(result["score"], 70)
        self.assertTrue(result["has_llms_txt"])

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_result_keys(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "html": "<html><body>" + "w " * 60 + "</body></html>", "elapsed_seconds": 0.5},
            {"success": False, "error": "404"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        for key in ["success", "url", "score", "robots", "ssr", "performance",
                     "captcha", "has_llms_txt", "issues"]:
            self.assertIn(key, result, f"Missing: {key}")

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_blocked_crawlers_lower_score(self, mock_fetch, mock_val):
        robots = "User-agent: GPTBot\nDisallow: /\nUser-agent: Anthropic-AI\nDisallow: /"
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": robots},
            {"success": True, "html": "<html><body>" + "w " * 60 + "</body></html>", "elapsed_seconds": 0.3},
            {"success": False, "error": "404"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        self.assertLess(result["score"], 70)
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("blocked" in m.lower() for m in msgs))

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_captcha_lowers_score(self, mock_fetch, mock_val):
        html = '<html><body><div class="g-recaptcha">' + "w " * 60 + '</div></body></html>'
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "html": html, "elapsed_seconds": 0.3},
            {"success": False, "error": "404"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("CAPTCHA" in m for m in msgs))

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_very_slow_issue(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "html": "<html><body>" + "w " * 60 + "</body></html>", "elapsed_seconds": 5.0},
            {"success": False, "error": "404"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("slow" in m.lower() for m in msgs))

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_score_clamped(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "html": "<html><body>" + "w " * 60 + "</body></html>", "elapsed_seconds": 0.2},
            {"success": True, "status_code": 200, "html": "# llms.txt"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    @patch("geo_technical.validate_url", return_value={"valid": True})
    @patch("geo_technical.fetch_page")
    def test_no_llms_txt_issue(self, mock_fetch, mock_val):
        mock_fetch.side_effect = [
            {"success": True, "status_code": 200, "html": "User-agent: *\nDisallow:"},
            {"success": True, "html": "<html><body>" + "w " * 60 + "</body></html>", "elapsed_seconds": 0.3},
            {"success": False, "error": "404"},
        ]
        result = analyze_technical_accessibility("https://x.com")
        self.assertFalse(result["has_llms_txt"])
        msgs = [i["message"] for i in result["issues"]]
        self.assertTrue(any("llms.txt" in m for m in msgs))


if __name__ == "__main__":
    unittest.main()
