"""Tests for three_o_plan.py — strategic optimization plan generator."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from three_o_plan import (
    INDUSTRY_PRIORITIES,
    TIMELINE_TEMPLATE,
    generate_plan_from_audit,
    generate_plan_from_scores,
)


class TestIndustryPriorities(unittest.TestCase):

    def test_has_restaurant(self):
        self.assertIn("restaurant", INDUSTRY_PRIORITIES)

    def test_has_ecommerce(self):
        self.assertIn("ecommerce", INDUSTRY_PRIORITIES)

    def test_has_franchise(self):
        self.assertIn("franchise", INDUSTRY_PRIORITIES)

    def test_has_academy(self):
        self.assertIn("academy", INDUSTRY_PRIORITIES)

    def test_has_clinic(self):
        self.assertIn("clinic", INDUSTRY_PRIORITIES)

    def test_has_service(self):
        self.assertIn("service", INDUSTRY_PRIORITIES)

    def test_weights_sum_to_one(self):
        for industry, config in INDUSTRY_PRIORITIES.items():
            total = config["seo_weight"] + config["geo_weight"] + config["aao_weight"]
            self.assertAlmostEqual(total, 1.0, places=2, msg=f"{industry} weights don't sum to 1")

    def test_each_has_focus(self):
        for industry, config in INDUSTRY_PRIORITIES.items():
            self.assertIn("focus", config)
            self.assertGreater(len(config["focus"]), 0)

    def test_ecommerce_aao_weight_highest(self):
        self.assertGreater(INDUSTRY_PRIORITIES["ecommerce"]["aao_weight"],
                           INDUSTRY_PRIORITIES["ecommerce"]["seo_weight"])

    def test_restaurant_seo_weight_highest(self):
        self.assertGreater(INDUSTRY_PRIORITIES["restaurant"]["seo_weight"],
                           INDUSTRY_PRIORITIES["restaurant"]["geo_weight"])


class TestTimelineTemplate(unittest.TestCase):

    def test_has_week_1_2(self):
        self.assertIn("week_1_2", TIMELINE_TEMPLATE)

    def test_has_ongoing(self):
        self.assertIn("ongoing", TIMELINE_TEMPLATE)

    def test_each_phase_has_tasks(self):
        for key, phase in TIMELINE_TEMPLATE.items():
            self.assertIn("phase", phase)
            self.assertIn("tasks", phase)
            self.assertIsInstance(phase["tasks"], list)

    def test_five_phases(self):
        self.assertEqual(len(TIMELINE_TEMPLATE), 5)


class TestGeneratePlanFromAudit(unittest.TestCase):

    def _audit(self, seo=70, geo=60, aao=50, seo_issues=None, geo_issues=None, aao_issues=None):
        return {
            "seo": {"score": seo, "issues": seo_issues or []},
            "geo": {"score": geo, "issues": geo_issues or []},
            "aao": {"score": aao, "issues": aao_issues or []},
        }

    def test_success(self):
        result = generate_plan_from_audit(self._audit())
        self.assertTrue(result["success"])

    def test_default_industry_service(self):
        result = generate_plan_from_audit(self._audit())
        self.assertEqual(result["industry"], "service")

    def test_custom_industry(self):
        result = generate_plan_from_audit(self._audit(), industry="restaurant")
        self.assertEqual(result["industry"], "restaurant")

    def test_unknown_industry_defaults_service(self):
        result = generate_plan_from_audit(self._audit(), industry="unknown_xyz")
        self.assertEqual(result["industry"], "unknown_xyz")
        self.assertIn("Service schema", result["industry_focus"][0])

    def test_current_scores(self):
        result = generate_plan_from_audit(self._audit(seo=80, geo=60, aao=40))
        self.assertEqual(result["current_scores"]["seo"], 80)
        self.assertEqual(result["current_scores"]["geo"], 60)
        self.assertEqual(result["current_scores"]["aao"], 40)

    def test_weakest_pillar(self):
        result = generate_plan_from_audit(self._audit(seo=80, geo=70, aao=40))
        self.assertEqual(result["weakest_pillar"], "AAO")

    def test_goals_for_low_scores(self):
        result = generate_plan_from_audit(self._audit(seo=40, geo=50, aao=30))
        pillars = [g["pillar"] for g in result["goals"]]
        self.assertIn("SEO", pillars)
        self.assertIn("GEO", pillars)
        self.assertIn("AAO", pillars)

    def test_no_goals_for_high_scores(self):
        result = generate_plan_from_audit(self._audit(seo=80, geo=75, aao=70))
        self.assertEqual(len(result["goals"]), 0)

    def test_goal_target_capped_at_80(self):
        result = generate_plan_from_audit(self._audit(seo=40, geo=70, aao=70))
        seo_goal = [g for g in result["goals"] if g["pillar"] == "SEO"][0]
        self.assertEqual(seo_goal["target"], 60)

    def test_goal_target_does_not_exceed_80(self):
        result = generate_plan_from_audit(self._audit(seo=55, geo=70, aao=70))
        seo_goal = [g for g in result["goals"] if g["pillar"] == "SEO"][0]
        self.assertEqual(seo_goal["target"], 75)

    def test_total_issues_counted(self):
        issues = [{"severity": "high", "message": "Fix it"}] * 3
        result = generate_plan_from_audit(self._audit(seo_issues=issues))
        self.assertEqual(result["total_issues"], 3)

    def test_critical_issues_counted(self):
        issues = [
            {"severity": "critical", "message": "C1"},
            {"severity": "high", "message": "H1"},
            {"severity": "low", "message": "L1"},
        ]
        result = generate_plan_from_audit(self._audit(seo_issues=issues))
        self.assertEqual(result["critical_issues"], 2)

    def test_timeline_has_phases(self):
        result = generate_plan_from_audit(self._audit())
        for phase_key in ["week_1_2", "week_3_4", "month_2", "month_3", "ongoing"]:
            self.assertIn(phase_key, result["timeline"])

    def test_critical_issues_in_early_phase(self):
        issues = [{"severity": "critical", "message": "Broken indexing"}]
        result = generate_plan_from_audit(self._audit(seo_issues=issues))
        week1_tasks = result["timeline"]["week_1_2"]["tasks"]
        self.assertTrue(any("Broken indexing" in t for t in week1_tasks))

    def test_medium_geo_in_month_2(self):
        issues = [{"severity": "medium", "message": "Improve citability"}]
        result = generate_plan_from_audit(self._audit(geo_issues=issues))
        month2_tasks = result["timeline"]["month_2"]["tasks"]
        self.assertTrue(any("citability" in t for t in month2_tasks))

    def test_medium_aao_in_month_3(self):
        issues = [{"severity": "medium", "message": "Add product feed"}]
        result = generate_plan_from_audit(self._audit(aao_issues=issues))
        month3_tasks = result["timeline"]["month_3"]["tasks"]
        self.assertTrue(any("product feed" in t for t in month3_tasks))

    def test_ongoing_always_has_tasks(self):
        result = generate_plan_from_audit(self._audit())
        self.assertGreater(len(result["timeline"]["ongoing"]["tasks"]), 0)

    def test_tasks_capped_at_8(self):
        issues = [{"severity": "critical", "message": f"Issue {i}"} for i in range(15)]
        result = generate_plan_from_audit(self._audit(seo_issues=issues))
        for phase in result["timeline"].values():
            self.assertLessEqual(len(phase["tasks"]), 8)

    def test_result_keys(self):
        result = generate_plan_from_audit(self._audit())
        for key in ["success", "industry", "industry_focus", "current_scores",
                     "weakest_pillar", "goals", "timeline", "total_issues", "critical_issues"]:
            self.assertIn(key, result)


class TestGeneratePlanFromScores(unittest.TestCase):

    def test_basic_plan(self):
        result = generate_plan_from_scores(70, 60, 50)
        self.assertTrue(result["success"])

    def test_low_seo_adds_issues(self):
        result = generate_plan_from_scores(30, 70, 70)
        self.assertGreater(result["total_issues"], 0)

    def test_low_geo_adds_issues(self):
        result = generate_plan_from_scores(70, 30, 70)
        self.assertGreater(result["total_issues"], 0)

    def test_low_aao_adds_issues(self):
        result = generate_plan_from_scores(70, 70, 30)
        self.assertGreater(result["total_issues"], 0)

    def test_all_high_no_auto_issues(self):
        result = generate_plan_from_scores(80, 80, 80)
        self.assertEqual(result["total_issues"], 0)

    def test_with_industry(self):
        result = generate_plan_from_scores(50, 50, 50, industry="franchise")
        self.assertEqual(result["industry"], "franchise")

    def test_scores_passed_through(self):
        result = generate_plan_from_scores(45, 55, 65)
        self.assertEqual(result["current_scores"]["seo"], 45)
        self.assertEqual(result["current_scores"]["geo"], 55)
        self.assertEqual(result["current_scores"]["aao"], 65)

    def test_all_low_multiple_issues(self):
        result = generate_plan_from_scores(30, 30, 30)
        self.assertGreaterEqual(result["total_issues"], 6)


if __name__ == "__main__":
    unittest.main()
