"""Tests for geo_llms_txt.py — llms.txt validation and generation."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from geo_llms_txt import (
    validate_llms_txt_content,
    generate_llms_txt_proposal,
    fetch_llms_txt,
    fetch_llms_full_txt,
    check_link_accessibility,
    analyze_llms_txt,
    LLMS_TXT_SPEC,
)


VALID_LLMS_TXT = """# Acme Corp

> Acme Corp is a leading technology company.

## Products

- [Product A](https://acme.com/product-a)
- [Product B](https://acme.com/product-b)
- [Product C](https://acme.com/product-c)

## About

- [About Us](https://acme.com/about)
- [Contact](https://acme.com/contact)

Contact: hello@acme.com
Updated: 2026-05-01
"""

MINIMAL_LLMS_TXT = """# Title

> Description

## Section

- [Link](https://example.com)
"""

EMPTY_LLMS_TXT = ""

SAMPLE_HTML = """
<html>
<head>
<title>Acme Corp - Best Tech Solutions</title>
<meta name="description" content="Acme provides innovative tech solutions.">
</head>
<body>
<nav>
<a href="/about">About Us</a>
<a href="/products">Products</a>
<a href="/contact">Contact</a>
<a href="/blog">Blog</a>
</nav>
</body>
</html>
"""


class TestLlmsTxtSpec(unittest.TestCase):

    def test_spec_has_required_fields(self):
        for field in ["title", "description", "sections", "links"]:
            self.assertIn(field, LLMS_TXT_SPEC)

    def test_all_fields_have_pattern(self):
        for field, spec in LLMS_TXT_SPEC.items():
            self.assertIn("pattern", spec)
            self.assertIn("required", spec)


class TestValidateLlmsTxtContent(unittest.TestCase):

    def test_valid_full_content(self):
        result = validate_llms_txt_content(VALID_LLMS_TXT)
        self.assertTrue(result["checks"]["title"]["present"])
        self.assertTrue(result["checks"]["description"]["present"])
        self.assertTrue(result["checks"]["sections"]["present"])
        self.assertTrue(result["checks"]["links"]["present"])
        self.assertTrue(result["checks"]["metadata"]["present"])
        self.assertGreater(result["compliance_score"], 80)

    def test_minimal_valid_content(self):
        result = validate_llms_txt_content(MINIMAL_LLMS_TXT)
        self.assertTrue(result["checks"]["title"]["present"])
        self.assertTrue(result["checks"]["description"]["present"])
        self.assertTrue(result["checks"]["sections"]["present"])
        self.assertTrue(result["checks"]["links"]["present"])
        self.assertGreater(result["compliance_score"], 50)

    def test_empty_content(self):
        result = validate_llms_txt_content(EMPTY_LLMS_TXT)
        self.assertFalse(result["checks"]["title"]["present"])
        self.assertFalse(result["checks"]["description"]["present"])
        self.assertFalse(result["checks"]["sections"]["present"])
        self.assertFalse(result["checks"]["links"]["present"])
        self.assertEqual(result["compliance_score"], 0)

    def test_missing_title(self):
        content = "> Description\n\n## Section\n\n- [Link](https://example.com)"
        result = validate_llms_txt_content(content)
        self.assertFalse(result["checks"]["title"]["present"])

    def test_missing_description(self):
        content = "# Title\n\n## Section\n\n- [Link](https://example.com)"
        result = validate_llms_txt_content(content)
        self.assertFalse(result["checks"]["description"]["present"])

    def test_missing_sections(self):
        content = "# Title\n\n> Description\n\n- [Link](https://example.com)"
        result = validate_llms_txt_content(content)
        self.assertFalse(result["checks"]["sections"]["present"])

    def test_missing_links(self):
        content = "# Title\n\n> Description\n\n## Section\n\nSome text here."
        result = validate_llms_txt_content(content)
        self.assertFalse(result["checks"]["links"]["present"])

    def test_section_count(self):
        content = "# T\n> D\n## S1\n## S2\n## S3\n- [L](http://x)"
        result = validate_llms_txt_content(content)
        self.assertEqual(result["checks"]["sections"]["count"], 3)

    def test_link_count(self):
        content = "# T\n> D\n## S\n- [A](http://a)\n- [B](http://b)\n- [C](http://c)"
        result = validate_llms_txt_content(content)
        self.assertEqual(result["checks"]["links"]["count"], 3)

    def test_links_extracted(self):
        result = validate_llms_txt_content(VALID_LLMS_TXT)
        self.assertGreater(len(result["links"]), 0)
        self.assertIn("text", result["links"][0])
        self.assertIn("url", result["links"][0])

    def test_line_count(self):
        content = "# T\n> D\n## S\n- [L](http://x)"
        result = validate_llms_txt_content(content)
        self.assertEqual(result["line_count"], 4)

    def test_metadata_bonus(self):
        without_meta = "# T\n> D\n## S\n- [L](http://x)"
        with_meta = "# T\n> D\n## S\n- [L](http://x)\nContact: a@b.com"
        score_without = validate_llms_txt_content(without_meta)["compliance_score"]
        score_with = validate_llms_txt_content(with_meta)["compliance_score"]
        self.assertGreater(score_with, score_without)

    def test_many_links_bonus(self):
        links = "\n".join(f"- [Link{i}](http://x/{i})" for i in range(6))
        content = f"# T\n> D\n## S\n{links}"
        result = validate_llms_txt_content(content)
        self.assertGreater(result["compliance_score"], 70)

    def test_many_sections_bonus(self):
        content = "# T\n> D\n## S1\n## S2\n## S3\n- [L](http://x)"
        result = validate_llms_txt_content(content)
        self.assertGreater(result["compliance_score"], 70)

    def test_score_capped_at_100(self):
        links = "\n".join(f"- [Link{i}](http://x/{i})" for i in range(10))
        content = f"# T\n> D\n## S1\n## S2\n## S3\n## S4\n{links}\nContact: a@b.com\nUpdated: 2026"
        result = validate_llms_txt_content(content)
        self.assertLessEqual(result["compliance_score"], 100)

    def test_metadata_types(self):
        for meta_type in ["Contact:", "Updated:", "Frequency:"]:
            content = f"# T\n> D\n## S\n- [L](http://x)\n{meta_type} value"
            result = validate_llms_txt_content(content)
            self.assertTrue(result["checks"]["metadata"]["present"])

    def test_links_max_20(self):
        links = "\n".join(f"- [L{i}](http://x/{i})" for i in range(30))
        content = f"# T\n> D\n## S\n{links}"
        result = validate_llms_txt_content(content)
        self.assertLessEqual(len(result["links"]), 20)


class TestGenerateLlmsTxtProposal(unittest.TestCase):

    def test_basic_generation(self):
        proposal = generate_llms_txt_proposal("https://acme.com", SAMPLE_HTML)
        self.assertIn("# Acme Corp", proposal)
        self.assertIn("> Acme provides innovative tech solutions.", proposal)
        self.assertIn("## Main Pages", proposal)

    def test_extracts_nav_links(self):
        proposal = generate_llms_txt_proposal("https://acme.com", SAMPLE_HTML)
        self.assertIn("[About Us]", proposal)
        self.assertIn("[Products]", proposal)
        self.assertIn("[Contact]", proposal)
        self.assertIn("https://acme.com/about", proposal)

    def test_no_title_uses_domain(self):
        html = "<html><head></head><body></body></html>"
        proposal = generate_llms_txt_proposal("https://acme.com", html)
        self.assertIn("# acme.com", proposal)

    def test_no_description_uses_default(self):
        html = "<html><head><title>Test</title></head><body></body></html>"
        proposal = generate_llms_txt_proposal("https://test.com", html)
        self.assertIn("> Official website of test.com", proposal)

    def test_no_links_adds_homepage(self):
        html = "<html><head><title>T</title></head><body></body></html>"
        proposal = generate_llms_txt_proposal("https://acme.com", html)
        self.assertIn("[Homepage](https://acme.com)", proposal)

    def test_links_limited_to_15(self):
        nav = "".join(f'<a href="/p{i}">Page {i}</a>' for i in range(30))
        html = f"<html><head><title>T</title></head><body>{nav}</body></html>"
        proposal = generate_llms_txt_proposal("https://acme.com", html)
        link_count = proposal.count("- [")
        self.assertLessEqual(link_count, 15)

    def test_long_link_text_skipped(self):
        html = '<html><head><title>T</title></head><body><a href="/x">' + "A" * 60 + '</a><a href="/y">Short</a></body></html>'
        proposal = generate_llms_txt_proposal("https://acme.com", html)
        self.assertNotIn("A" * 60, proposal)
        self.assertIn("[Short]", proposal)

    def test_reverse_meta_description_order(self):
        html = '<html><head><title>T</title><meta content="Reversed desc" name="description"></head><body></body></html>'
        proposal = generate_llms_txt_proposal("https://acme.com", html)
        self.assertIn("> Reversed desc", proposal)

    def test_duplicate_hrefs_deduplicated(self):
        html = '<html><head><title>T</title></head><body><a href="/about">About</a><a href="/about">About Us</a></body></html>'
        proposal = generate_llms_txt_proposal("https://acme.com", html)
        self.assertEqual(proposal.count("/about"), 1)


class TestFetchLlmsTxt(unittest.TestCase):

    @patch("geo_llms_txt.fetch_page")
    def test_found_at_root(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "# Title\n> Desc"}
        result = fetch_llms_txt("https://acme.com")
        self.assertTrue(result["found"])
        self.assertIn("llms.txt", result["location"])

    @patch("geo_llms_txt.fetch_page")
    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "status_code": 404}
        result = fetch_llms_txt("https://acme.com")
        self.assertFalse(result["found"])

    @patch("geo_llms_txt.fetch_page")
    def test_html_page_rejected(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "<html><body>Not llms.txt</body></html>"}
        result = fetch_llms_txt("https://acme.com")
        self.assertFalse(result["found"])

    @patch("geo_llms_txt.fetch_page")
    def test_empty_content_rejected(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "  "}
        result = fetch_llms_txt("https://acme.com")
        self.assertFalse(result["found"])

    @patch("geo_llms_txt.fetch_page")
    def test_well_known_fallback(self, mock_fetch):
        def side_effect(url):
            if ".well-known" in url:
                return {"success": True, "status_code": 200, "html": "# Title"}
            return {"success": False, "status_code": 404}
        mock_fetch.side_effect = side_effect
        result = fetch_llms_txt("https://acme.com")
        self.assertTrue(result["found"])
        self.assertIn(".well-known", result["location"])


class TestFetchLlmsFullTxt(unittest.TestCase):

    @patch("geo_llms_txt.fetch_page")
    def test_found(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "status_code": 200, "html": "Full content here..."}
        result = fetch_llms_full_txt("https://acme.com")
        self.assertTrue(result["found"])
        self.assertIn("size_bytes", result)

    @patch("geo_llms_txt.fetch_page")
    def test_not_found(self, mock_fetch):
        mock_fetch.return_value = {"success": False, "status_code": 404}
        result = fetch_llms_full_txt("https://acme.com")
        self.assertFalse(result["found"])


class TestCheckLinkAccessibility(unittest.TestCase):

    @patch("geo_llms_txt.fetch_page")
    def test_all_accessible(self, mock_fetch):
        mock_fetch.return_value = {"success": True}
        links = [
            {"url": "https://acme.com/a", "text": "A"},
            {"url": "https://acme.com/b", "text": "B"},
        ]
        result = check_link_accessibility(links)
        self.assertEqual(result["accessible"], 2)
        self.assertEqual(result["broken"], 0)

    @patch("geo_llms_txt.fetch_page")
    def test_mixed_accessibility(self, mock_fetch):
        def side_effect(url):
            return {"success": "/good" in url}
        mock_fetch.side_effect = side_effect
        links = [
            {"url": "https://acme.com/good", "text": "Good"},
            {"url": "https://acme.com/bad", "text": "Bad"},
        ]
        result = check_link_accessibility(links)
        self.assertEqual(result["accessible"], 1)
        self.assertEqual(result["broken"], 1)

    @patch("geo_llms_txt.fetch_page")
    def test_max_10_links_checked(self, mock_fetch):
        mock_fetch.return_value = {"success": True}
        links = [{"url": f"https://acme.com/{i}", "text": f"L{i}"} for i in range(20)]
        result = check_link_accessibility(links)
        self.assertLessEqual(result["total_checked"], 10)

    @patch("geo_llms_txt.fetch_page")
    def test_non_http_links_skipped(self, mock_fetch):
        mock_fetch.return_value = {"success": True}
        links = [
            {"url": "/relative", "text": "Rel"},
            {"url": "mailto:a@b.com", "text": "Mail"},
            {"url": "https://acme.com/a", "text": "HTTP"},
        ]
        result = check_link_accessibility(links)
        self.assertEqual(result["total_checked"], 1)


class TestAnalyzeLlmsTxt(unittest.TestCase):

    @patch("geo_llms_txt.fetch_llms_full_txt")
    @patch("geo_llms_txt.fetch_llms_txt")
    @patch("geo_llms_txt.validate_url")
    def test_present_valid(self, mock_validate, mock_fetch, mock_full):
        mock_validate.return_value = {"valid": True}
        mock_fetch.return_value = {"found": True, "location": "https://acme.com/llms.txt", "content": VALID_LLMS_TXT}
        mock_full.return_value = {"found": False}
        result = analyze_llms_txt("https://acme.com")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "present")
        self.assertGreater(result["score"], 0)

    @patch("geo_llms_txt.fetch_page")
    @patch("geo_llms_txt.fetch_llms_full_txt")
    @patch("geo_llms_txt.fetch_llms_txt")
    @patch("geo_llms_txt.validate_url")
    def test_missing_generates_proposal(self, mock_validate, mock_fetch, mock_full, mock_page):
        mock_validate.return_value = {"valid": True}
        mock_fetch.return_value = {"found": False}
        mock_full.return_value = {"found": False}
        mock_page.return_value = {"success": True, "html": SAMPLE_HTML}
        result = analyze_llms_txt("https://acme.com")
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["score"], 0)
        self.assertIn("proposal", result)
        self.assertGreater(len(result["proposal"]), 0)

    @patch("geo_llms_txt.validate_url")
    def test_invalid_url(self, mock_validate):
        mock_validate.return_value = {"valid": False, "error": "Invalid URL"}
        result = analyze_llms_txt("not-a-url")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch("geo_llms_txt.fetch_llms_full_txt")
    @patch("geo_llms_txt.fetch_llms_txt")
    @patch("geo_llms_txt.validate_url")
    def test_issues_for_missing_fields(self, mock_validate, mock_fetch, mock_full):
        mock_validate.return_value = {"valid": True}
        incomplete = "# Title\n\nSome text but no blockquote or links"
        mock_fetch.return_value = {"found": True, "location": "https://x/llms.txt", "content": incomplete}
        mock_full.return_value = {"found": False}
        result = analyze_llms_txt("https://x.com")
        self.assertGreater(len(result["issues"]), 0)
        messages = [i["message"] for i in result["issues"]]
        self.assertTrue(any("description" in m for m in messages))


if __name__ == "__main__":
    unittest.main()
