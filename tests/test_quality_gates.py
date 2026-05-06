"""Tests for hooks quality gate validators."""

import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from validate_quality import validate_file
from check_cwv import check_cwv_terminology
from check_schema import check_schema_recommendations


class TestCWVCheck(unittest.TestCase):

    def _write_temp(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_catches_fid_reference(self):
        path = self._write_temp('metric = "FID"\n')
        violations = check_cwv_terminology(path)
        self.assertTrue(len(violations) > 0)
        os.unlink(path)

    def test_allows_inp_reference(self):
        path = self._write_temp('metric = "INP"\n')
        violations = check_cwv_terminology(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)

    def test_skips_comments(self):
        path = self._write_temp('# Uses INP never FID\ninp_value = 200\n')
        violations = check_cwv_terminology(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)

    def test_allows_deprecation_context(self):
        path = self._write_temp('note = "FID deprecated in favor of INP"\n')
        violations = check_cwv_terminology(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)

    def test_fid_in_variable_name_ok(self):
        path = self._write_temp('FID_LEGACY = None\n')
        violations = check_cwv_terminology(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)


class TestSchemaCheck(unittest.TestCase):

    def _write_temp(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_catches_howto_schema(self):
        path = self._write_temp('schema_type = "HowTo"\n')
        violations = check_schema_recommendations(path)
        self.assertTrue(any(v["schema"] == "HowTo" for v in violations))
        os.unlink(path)

    def test_catches_faqpage_unrestricted(self):
        path = self._write_temp('schema_type = "FAQPage"\n')
        violations = check_schema_recommendations(path)
        self.assertTrue(any(v["schema"] == "FAQPage" for v in violations))
        os.unlink(path)

    def test_allows_faqpage_with_restriction_context(self):
        path = self._write_temp('# FAQPage restricted to government and healthcare only\n')
        violations = check_schema_recommendations(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)

    def test_allows_howto_with_deprecated_context(self):
        path = self._write_temp('# HowTo schema deprecated\n')
        violations = check_schema_recommendations(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)

    def test_no_false_positives(self):
        path = self._write_temp('schema_type = "Organization"\nschema2 = "LocalBusiness"\n')
        violations = check_schema_recommendations(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)


class TestQualityValidator(unittest.TestCase):

    def _write_temp(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_clean_file_passes(self):
        path = self._write_temp('score = compute_three_o_score(75, 60, 80)\nprint(score)\n')
        violations = validate_file(path)
        self.assertEqual(len(violations), 0)
        os.unlink(path)

    def test_catches_api_key_pattern(self):
        path = self._write_temp('key = "sk-abcdefghijklmnopqrstuvwxyz123"\n')
        violations = validate_file(path)
        self.assertTrue(any(v["rule_id"] == "no-api-keys-in-code" for v in violations))
        os.unlink(path)

    def test_nonexistent_file(self):
        violations = validate_file("/nonexistent/path/file.py")
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
