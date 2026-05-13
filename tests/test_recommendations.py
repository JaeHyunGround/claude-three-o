"""Tests for recommendation engine."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from recommendations import (
    generate_recommendations, format_recommendations_md,
    RECOMMENDATION_CATALOG, INDUSTRY_RECOMMENDATIONS,
    EFFORT_LEVELS, IMPACT_LEVELS,
)


class TestRecommendationGeneration(unittest.TestCase):

    def setUp(self):
        self.audit_data = {
            "seo": {
                "score": 55,
                "issues": [
                    {"severity": "high", "message": "Missing meta description"},
                    {"severity": "medium", "message": "Title length 12 chars"},
                ],
            },
            "geo": {
                "score": 45,
                "issues": [{"severity": "medium", "message": "Low factual density"}],
                "platforms": {"gemini": {"score": 40}},
            },
            "aao": {
                "score": 32,
                "industry_detected": "restaurant",
                "dimensions": {
                    "structured_data": {"score": 20},
                    "reviews_ratings": {"score": 10},
                    "info_completeness": {"score": 50},
                    "api_booking": {"score": 25},
                    "trust_signals": {"score": 35},
                    "freshness": {"score": 40},
                },
            },
        }

    def test_generates_recommendations(self):
        result = generate_recommendations(self.audit_data)
        self.assertTrue(result["success"])
        self.assertGreater(result["total"], 0)

    def test_has_quick_wins(self):
        result = generate_recommendations(self.audit_data)
        self.assertGreater(len(result["quick_wins"]), 0)

    def test_has_strategic(self):
        result = generate_recommendations(self.audit_data)
        self.assertGreater(len(result["strategic"]), 0)

    def test_industry_detected(self):
        result = generate_recommendations(self.audit_data)
        self.assertEqual(result["industry"], "restaurant")

    def test_industry_recommendations_included(self):
        result = generate_recommendations(self.audit_data)
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertGreater(len(industry_recs), 0)

    def test_sorted_by_impact(self):
        result = generate_recommendations(self.audit_data)
        impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        impacts = [impact_order.get(r["impact"], 9) for r in result["recommendations"]]
        self.assertEqual(impacts, sorted(impacts))

    def test_max_items_respected(self):
        result = generate_recommendations(self.audit_data, max_items=3)
        self.assertLessEqual(len(result["recommendations"]), 3)

    def test_effort_estimate_present(self):
        result = generate_recommendations(self.audit_data)
        for rec in result["recommendations"]:
            self.assertIn("effort_estimate", rec)
            self.assertIn("impact_estimate", rec)

    def test_no_data_still_works(self):
        result = generate_recommendations({})
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 0)

    def test_general_industry_no_specific_recs(self):
        data = {"aao": {"industry_detected": "general", "dimensions": {}}}
        result = generate_recommendations(data)
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 0)


class TestRecommendationFormatting(unittest.TestCase):

    def test_markdown_output(self):
        data = {
            "seo": {"score": 40, "issues": [{"severity": "high", "message": "Missing meta description"}]},
            "geo": {"score": 40, "issues": []},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {"structured_data": {"score": 10}}},
        }
        result = generate_recommendations(data)
        md = format_recommendations_md(result)
        self.assertIn("Recommendations", md)
        self.assertIn("Quick Wins", md)

    def test_empty_recommendations(self):
        result = {"quick_wins": [], "strategic": [], "maintenance": []}
        md = format_recommendations_md(result)
        self.assertIn("Recommendations", md)


class TestSEOConditions(unittest.TestCase):

    def _base(self, **seo_overrides):
        seo = {"score": 70, "issues": []}
        seo.update(seo_overrides)
        return {
            "seo": seo,
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }

    def _ids(self, data):
        return [r["id"] for r in generate_recommendations(data)["recommendations"]]

    def test_meta_description(self):
        data = self._base(issues=[{"severity": "high", "message": "Missing meta description"}])
        self.assertIn("seo_add_meta_description", self._ids(data))

    def test_title_length(self):
        data = self._base(issues=[{"severity": "medium", "message": "Title length 12 chars"}])
        self.assertIn("seo_fix_title_length", self._ids(data))

    def test_canonical(self):
        data = self._base(issues=[{"severity": "medium", "message": "Missing canonical tag"}])
        self.assertIn("seo_add_canonical", self._ids(data))

    def test_heading_h1(self):
        data = self._base(issues=[{"severity": "medium", "message": "Multiple H1 tags found"}])
        self.assertIn("seo_fix_heading_hierarchy", self._ids(data))

    def test_heading_keyword(self):
        data = self._base(issues=[{"severity": "low", "message": "Poor heading structure"}])
        self.assertIn("seo_fix_heading_hierarchy", self._ids(data))

    def test_hsts(self):
        data = self._base(issues=[{"severity": "medium", "message": "HSTS header not set"}])
        self.assertIn("seo_add_hsts", self._ids(data))

    def test_viewport(self):
        data = self._base(issues=[{"severity": "high", "message": "No viewport meta tag"}])
        self.assertIn("seo_add_viewport", self._ids(data))

    def test_images_alt(self):
        data = self._base(issues=[{"severity": "medium", "message": "5 images missing alt text"}])
        self.assertIn("seo_improve_images", self._ids(data))

    def test_no_issues_no_seo_recs(self):
        data = self._base()
        seo_recs = [r for r in self._ids(data) if r.startswith("seo_")]
        self.assertEqual(len(seo_recs), 0)

    def test_multiple_issues_multiple_recs(self):
        data = self._base(issues=[
            {"severity": "high", "message": "Missing meta description"},
            {"severity": "medium", "message": "Title length 10 chars"},
            {"severity": "medium", "message": "HSTS header missing"},
        ])
        ids = self._ids(data)
        self.assertIn("seo_add_meta_description", ids)
        self.assertIn("seo_fix_title_length", ids)
        self.assertIn("seo_add_hsts", ids)


class TestGEOConditions(unittest.TestCase):

    def _base(self, **geo_overrides):
        geo = {"score": 80, "issues": []}
        geo.update(geo_overrides)
        return {
            "seo": {"score": 80, "issues": []},
            "geo": geo,
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }

    def _ids(self, data):
        return [r["id"] for r in generate_recommendations(data)["recommendations"]]

    def test_definition_sentences_low_score(self):
        data = self._base(score=45)
        self.assertIn("geo_add_definition_sentences", self._ids(data))

    def test_definition_sentences_high_score_excluded(self):
        data = self._base(score=75)
        self.assertNotIn("geo_add_definition_sentences", self._ids(data))

    def test_data_density_from_issue(self):
        data = self._base(issues=[{"severity": "medium", "message": "Low factual density"}])
        self.assertIn("geo_improve_data_density", self._ids(data))

    def test_data_density_from_dimension(self):
        data = self._base(dimensions={"factual_density": {"score": 30}})
        self.assertIn("geo_improve_data_density", self._ids(data))

    def test_source_attribution_low_score(self):
        data = self._base(score=50)
        self.assertIn("geo_add_source_attribution", self._ids(data))

    def test_source_attribution_high_score_excluded(self):
        data = self._base(score=70)
        self.assertNotIn("geo_add_source_attribution", self._ids(data))

    def test_content_structure_from_issue(self):
        data = self._base(issues=[{"severity": "medium", "message": "Poor content structure"}])
        self.assertIn("geo_improve_content_structure", self._ids(data))

    def test_eeat_gemini_low(self):
        data = self._base(platforms={"gemini": {"score": 30}})
        self.assertIn("geo_add_eeat_signals", self._ids(data))

    def test_eeat_gemini_high_excluded(self):
        data = self._base(platforms={"gemini": {"score": 75}})
        self.assertNotIn("geo_add_eeat_signals", self._ids(data))

    def test_llms_txt_always_included(self):
        data = self._base(score=95)
        self.assertIn("geo_add_llms_txt", self._ids(data))

    def test_llms_txt_included_even_high_score(self):
        data = self._base(score=100, issues=[], platforms={})
        self.assertIn("geo_add_llms_txt", self._ids(data))


class TestAAOConditions(unittest.TestCase):

    def _base(self, **dims):
        return {
            "seo": {"score": 80, "issues": []},
            "geo": {"score": 80, "issues": []},
            "aao": {
                "score": 50,
                "industry_detected": "general",
                "dimensions": {k: {"score": v} for k, v in dims.items()},
            },
        }

    def _ids(self, data):
        return [r["id"] for r in generate_recommendations(data)["recommendations"]]

    def test_json_ld_low_structured_data(self):
        data = self._base(structured_data=20)
        self.assertIn("aao_add_json_ld", data and self._ids(data))

    def test_json_ld_high_score_excluded(self):
        data = self._base(structured_data=80)
        self.assertNotIn("aao_add_json_ld", self._ids(data))

    def test_schema_actions_low_api(self):
        data = self._base(api_booking=25)
        self.assertIn("aao_add_schema_actions", self._ids(data))

    def test_schema_actions_high_excluded(self):
        data = self._base(api_booking=60)
        self.assertNotIn("aao_add_schema_actions", self._ids(data))

    def test_collect_reviews(self):
        data = self._base(reviews_ratings=15)
        self.assertIn("aao_collect_reviews", self._ids(data))

    def test_collect_reviews_high_excluded(self):
        data = self._base(reviews_ratings=80)
        self.assertNotIn("aao_collect_reviews", self._ids(data))

    def test_complete_business_info(self):
        data = self._base(info_completeness=40)
        self.assertIn("aao_complete_business_info", self._ids(data))

    def test_add_trust_signals(self):
        data = self._base(trust_signals=30)
        self.assertIn("aao_add_trust_signals", self._ids(data))

    def test_improve_freshness(self):
        data = self._base(freshness=25)
        self.assertIn("aao_improve_freshness", self._ids(data))

    def test_no_dimensions_no_aao_recs(self):
        data = self._base()
        aao_recs = [r for r in self._ids(data) if r.startswith("aao_")]
        self.assertEqual(len(aao_recs), 0)


class TestIndustryRecommendations(unittest.TestCase):

    def _data_for_industry(self, industry):
        return {
            "seo": {"score": 70, "issues": []},
            "geo": {"score": 70, "issues": []},
            "aao": {"score": 50, "industry_detected": industry, "dimensions": {}},
        }

    def test_restaurant_count(self):
        result = generate_recommendations(self._data_for_industry("restaurant"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 3)

    def test_restaurant_titles(self):
        result = generate_recommendations(self._data_for_industry("restaurant"))
        titles = [r["title"] for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertTrue(any("Menu schema" in t for t in titles))
        self.assertTrue(any("reservation" in t.lower() for t in titles))

    def test_ecommerce_count(self):
        result = generate_recommendations(self._data_for_industry("ecommerce"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 3)

    def test_ecommerce_product_schema(self):
        result = generate_recommendations(self._data_for_industry("ecommerce"))
        titles = [r["title"] for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertTrue(any("Product schema" in t for t in titles))

    def test_clinic_count(self):
        result = generate_recommendations(self._data_for_industry("clinic"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 3)

    def test_hotel_count(self):
        result = generate_recommendations(self._data_for_industry("hotel"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 2)

    def test_education_count(self):
        result = generate_recommendations(self._data_for_industry("education"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 2)

    def test_saas_count(self):
        result = generate_recommendations(self._data_for_industry("saas"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 2)

    def test_unknown_industry_no_recs(self):
        result = generate_recommendations(self._data_for_industry("unknown_industry"))
        industry_recs = [r for r in result["recommendations"] if r["pillar"] == "INDUSTRY"]
        self.assertEqual(len(industry_recs), 0)

    def test_industry_title_prefix(self):
        result = generate_recommendations(self._data_for_industry("restaurant"))
        for r in result["recommendations"]:
            if r["pillar"] == "INDUSTRY":
                self.assertTrue(r["title"].startswith("[Restaurant]"))

    def test_industry_id_format(self):
        result = generate_recommendations(self._data_for_industry("clinic"))
        for r in result["recommendations"]:
            if r["pillar"] == "INDUSTRY":
                self.assertTrue(r["id"].startswith("industry_clinic_"))

    def test_all_industries_have_effort_impact(self):
        for industry in INDUSTRY_RECOMMENDATIONS:
            result = generate_recommendations(self._data_for_industry(industry))
            for r in result["recommendations"]:
                if r["pillar"] == "INDUSTRY":
                    self.assertIn("effort_estimate", r, f"Missing effort_estimate in {industry}")
                    self.assertIn("impact_estimate", r, f"Missing impact_estimate in {industry}")


class TestClassification(unittest.TestCase):

    def test_quick_win_low_effort_high_impact(self):
        data = {
            "seo": {"score": 50, "issues": [{"severity": "high", "message": "No viewport meta tag"}]},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        qw_ids = [r["id"] for r in result["quick_wins"]]
        self.assertIn("seo_add_viewport", qw_ids)

    def test_quick_win_medium_effort_critical_impact(self):
        data = {
            "seo": {"score": 80, "issues": []},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {"structured_data": {"score": 10}}},
        }
        result = generate_recommendations(data)
        qw_ids = [r["id"] for r in result["quick_wins"]]
        self.assertIn("aao_add_json_ld", qw_ids)

    def test_strategic_high_effort_high_impact(self):
        data = {
            "seo": {"score": 80, "issues": []},
            "geo": {"score": 40, "issues": [], "platforms": {"gemini": {"score": 20}}},
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        strat_ids = [r["id"] for r in result["strategic"]]
        self.assertIn("geo_add_eeat_signals", strat_ids)

    def test_strategic_major_effort_critical_impact(self):
        data = {
            "seo": {"score": 80, "issues": []},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 30, "industry_detected": "restaurant", "dimensions": {}},
        }
        result = generate_recommendations(data)
        strat_ids = [r["id"] for r in result["strategic"]]
        has_reservation = any("reservation" in r.lower() for r in strat_ids)
        self.assertTrue(has_reservation or len(strat_ids) > 0)

    def test_maintenance_low_effort_low_impact(self):
        data = {
            "seo": {"score": 50, "issues": [{"severity": "medium", "message": "Missing canonical tag"}]},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        maint_ids = [r["id"] for r in result["maintenance"]]
        self.assertIn("seo_add_canonical", maint_ids)

    def test_quick_wins_capped_at_5(self):
        data = {
            "seo": {"score": 30, "issues": [
                {"severity": "high", "message": "Missing meta description"},
                {"severity": "medium", "message": "Title length 5"},
                {"severity": "high", "message": "No viewport meta tag"},
            ]},
            "geo": {"score": 30, "issues": [{"severity": "medium", "message": "Low factual density"}]},
            "aao": {"score": 20, "industry_detected": "general", "dimensions": {"structured_data": {"score": 10}}},
        }
        result = generate_recommendations(data)
        self.assertLessEqual(len(result["quick_wins"]), 5)

    def test_strategic_capped_at_5(self):
        result = generate_recommendations({
            "seo": {"score": 30, "issues": []},
            "geo": {"score": 30, "issues": [], "platforms": {"gemini": {"score": 10}}},
            "aao": {"score": 20, "industry_detected": "restaurant", "dimensions": {
                "api_booking": {"score": 10}, "reviews_ratings": {"score": 5},
            }},
        })
        self.assertLessEqual(len(result["strategic"]), 5)

    def test_maintenance_capped_at_5(self):
        result = generate_recommendations({
            "seo": {"score": 30, "issues": [
                {"severity": "h", "message": "Missing canonical link"},
                {"severity": "m", "message": "5 images missing alt text"},
                {"severity": "m", "message": "HSTS not enabled"},
                {"severity": "m", "message": "heading hierarchy broken"},
            ]},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 60, "industry_detected": "general", "dimensions": {"freshness": {"score": 20}}},
        })
        self.assertLessEqual(len(result["maintenance"]), 5)


class TestSorting(unittest.TestCase):

    def test_critical_before_high(self):
        data = {
            "seo": {"score": 80, "issues": []},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 20, "industry_detected": "general", "dimensions": {
                "structured_data": {"score": 10},
                "api_booking": {"score": 20},
            }},
        }
        result = generate_recommendations(data)
        recs = result["recommendations"]
        impacts = [r["impact"] for r in recs]
        if "critical" in impacts and "high" in impacts:
            crit_idx = impacts.index("critical")
            high_idx = impacts.index("high")
            self.assertLess(crit_idx, high_idx)

    def test_same_impact_sorted_by_effort(self):
        data = {
            "seo": {"score": 40, "issues": [
                {"severity": "high", "message": "Missing meta description"},
                {"severity": "medium", "message": "Title length 10"},
            ]},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        medium_recs = [r for r in result["recommendations"] if r["impact"] == "medium"]
        effort_order = {"low": 0, "medium": 1, "high": 2, "major": 3}
        efforts = [effort_order[r["effort"]] for r in medium_recs]
        self.assertEqual(efforts, sorted(efforts))

    def test_full_sort_stability(self):
        result = generate_recommendations({
            "seo": {"score": 30, "issues": [
                {"severity": "h", "message": "Missing meta description"},
                {"severity": "m", "message": "Title length 5"},
                {"severity": "m", "message": "Missing canonical"},
                {"severity": "h", "message": "No viewport"},
            ]},
            "geo": {"score": 30, "issues": [{"severity": "m", "message": "Low factual density"}],
                    "platforms": {"gemini": {"score": 20}}},
            "aao": {"score": 20, "industry_detected": "general", "dimensions": {
                "structured_data": {"score": 10}, "api_booking": {"score": 15},
                "reviews_ratings": {"score": 10}, "trust_signals": {"score": 20},
                "freshness": {"score": 15},
            }},
        })
        impact_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        effort_order = {"low": 0, "medium": 1, "high": 2, "major": 3}
        keys = [(impact_order.get(r["impact"], 9), effort_order.get(r["effort"], 9))
                for r in result["recommendations"]]
        self.assertEqual(keys, sorted(keys))


class TestFormattingDetailed(unittest.TestCase):

    def _rec_data(self):
        return generate_recommendations({
            "seo": {"score": 40, "issues": [{"severity": "high", "message": "Missing meta description"}]},
            "geo": {"score": 40, "issues": [{"severity": "medium", "message": "Low factual density"}]},
            "aao": {"score": 30, "industry_detected": "restaurant", "dimensions": {"structured_data": {"score": 10}}},
        })

    def test_quick_wins_section(self):
        md = format_recommendations_md(self._rec_data())
        self.assertIn("### Quick Wins", md)

    def test_strategic_section(self):
        md = format_recommendations_md(self._rec_data())
        self.assertIn("### Strategic Investments", md)

    def test_maintenance_section(self):
        md = format_recommendations_md(self._rec_data())
        self.assertIn("### Maintenance", md)

    def test_effort_label_in_output(self):
        md = format_recommendations_md(self._rec_data())
        self.assertIn("Effort:", md)

    def test_impact_label_in_output(self):
        md = format_recommendations_md(self._rec_data())
        self.assertIn("Impact:", md)

    def test_numbered_items(self):
        md = format_recommendations_md(self._rec_data())
        self.assertIn("**1.", md)

    def test_no_sections_when_empty(self):
        md = format_recommendations_md({"quick_wins": [], "strategic": [], "maintenance": []})
        self.assertNotIn("Quick Wins", md)
        self.assertNotIn("Strategic", md)
        self.assertNotIn("Maintenance", md)

    def test_maintenance_shows_max_3(self):
        rec_data = self._rec_data()
        rec_data["maintenance"] = [
            {"title": f"Item {i}", "effort_estimate": "< 1 hour", "impact_estimate": "+2-5 pts"}
            for i in range(10)
        ]
        md = format_recommendations_md(rec_data)
        self.assertIn("Item 0", md)
        self.assertIn("Item 2", md)
        self.assertNotIn("Item 3", md)


class TestConstants(unittest.TestCase):

    def test_effort_levels_complete(self):
        self.assertEqual(set(EFFORT_LEVELS.keys()), {"low", "medium", "high", "major"})

    def test_impact_levels_complete(self):
        self.assertEqual(set(IMPACT_LEVELS.keys()), {"low", "medium", "high", "critical"})

    def test_catalog_pillars(self):
        self.assertEqual(set(RECOMMENDATION_CATALOG.keys()), {"seo", "geo", "aao"})

    def test_catalog_seo_count(self):
        self.assertEqual(len(RECOMMENDATION_CATALOG["seo"]), 7)

    def test_catalog_geo_count(self):
        self.assertEqual(len(RECOMMENDATION_CATALOG["geo"]), 6)

    def test_catalog_aao_count(self):
        self.assertEqual(len(RECOMMENDATION_CATALOG["aao"]), 6)

    def test_all_catalog_entries_have_required_fields(self):
        for pillar, entries in RECOMMENDATION_CATALOG.items():
            for key, rec in entries.items():
                self.assertIn("condition", rec, f"{pillar}.{key} missing condition")
                self.assertIn("title", rec, f"{pillar}.{key} missing title")
                self.assertIn("detail", rec, f"{pillar}.{key} missing detail")
                self.assertIn("effort", rec, f"{pillar}.{key} missing effort")
                self.assertIn("impact", rec, f"{pillar}.{key} missing impact")

    def test_all_catalog_efforts_valid(self):
        for pillar, entries in RECOMMENDATION_CATALOG.items():
            for key, rec in entries.items():
                self.assertIn(rec["effort"], EFFORT_LEVELS, f"{pillar}.{key} invalid effort: {rec['effort']}")

    def test_all_catalog_impacts_valid(self):
        for pillar, entries in RECOMMENDATION_CATALOG.items():
            for key, rec in entries.items():
                self.assertIn(rec["impact"], IMPACT_LEVELS, f"{pillar}.{key} invalid impact: {rec['impact']}")

    def test_all_industry_entries_have_required_fields(self):
        for industry, recs in INDUSTRY_RECOMMENDATIONS.items():
            for i, rec in enumerate(recs):
                self.assertIn("title", rec, f"{industry}[{i}] missing title")
                self.assertIn("detail", rec, f"{industry}[{i}] missing detail")
                self.assertIn("effort", rec, f"{industry}[{i}] missing effort")
                self.assertIn("impact", rec, f"{industry}[{i}] missing impact")

    def test_all_industry_efforts_valid(self):
        for industry, recs in INDUSTRY_RECOMMENDATIONS.items():
            for rec in recs:
                self.assertIn(rec["effort"], EFFORT_LEVELS, f"{industry}: {rec['title']} invalid effort")

    def test_all_industry_impacts_valid(self):
        for industry, recs in INDUSTRY_RECOMMENDATIONS.items():
            for rec in recs:
                self.assertIn(rec["impact"], IMPACT_LEVELS, f"{industry}: {rec['title']} invalid impact")

    def test_industry_count(self):
        self.assertEqual(len(INDUSTRY_RECOMMENDATIONS), 6)

    def test_catalog_conditions_are_callable(self):
        for pillar, entries in RECOMMENDATION_CATALOG.items():
            for key, rec in entries.items():
                self.assertTrue(callable(rec["condition"]), f"{pillar}.{key} condition not callable")


class TestEdgeCases(unittest.TestCase):

    def test_missing_seo_pillar(self):
        data = {
            "geo": {"score": 40, "issues": []},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        self.assertTrue(result["success"])
        seo_recs = [r for r in result["recommendations"] if r["pillar"] == "SEO"]
        self.assertEqual(len(seo_recs), 0)

    def test_missing_geo_pillar(self):
        data = {
            "seo": {"score": 40, "issues": [{"severity": "h", "message": "Missing meta description"}]},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        self.assertTrue(result["success"])
        geo_recs = [r for r in result["recommendations"] if r["pillar"] == "GEO"]
        self.assertEqual(len(geo_recs), 0)

    def test_missing_aao_pillar(self):
        data = {
            "seo": {"score": 40, "issues": []},
            "geo": {"score": 40, "issues": []},
        }
        result = generate_recommendations(data)
        self.assertTrue(result["success"])
        self.assertEqual(result["industry"], "general")

    def test_empty_dimensions_dict(self):
        data = {
            "seo": {"score": 80, "issues": []},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 50, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        self.assertTrue(result["success"])

    def test_high_scores_minimal_recs(self):
        data = {
            "seo": {"score": 95, "issues": []},
            "geo": {"score": 95, "issues": [], "platforms": {"gemini": {"score": 90}}},
            "aao": {"score": 90, "industry_detected": "general", "dimensions": {
                "structured_data": {"score": 90},
                "api_booking": {"score": 90},
                "reviews_ratings": {"score": 80},
                "info_completeness": {"score": 90},
                "trust_signals": {"score": 85},
                "freshness": {"score": 80},
            }},
        }
        result = generate_recommendations(data)
        non_geo_llms = [r for r in result["recommendations"] if r["id"] != "geo_add_llms_txt"]
        self.assertLessEqual(len(non_geo_llms), 2)

    def test_max_items_zero(self):
        result = generate_recommendations({"seo": {"score": 30, "issues": [
            {"severity": "h", "message": "Missing meta description"}
        ]}}, max_items=0)
        self.assertEqual(len(result["recommendations"]), 0)

    def test_max_items_one(self):
        data = {
            "seo": {"score": 30, "issues": [{"severity": "h", "message": "Missing meta description"}]},
            "geo": {"score": 30, "issues": []},
            "aao": {"score": 30, "industry_detected": "general", "dimensions": {"structured_data": {"score": 10}}},
        }
        result = generate_recommendations(data, max_items=1)
        self.assertEqual(len(result["recommendations"]), 1)

    def test_condition_exception_handled(self):
        original = RECOMMENDATION_CATALOG["seo"]["add_meta_description"]["condition"]
        RECOMMENDATION_CATALOG["seo"]["add_meta_description"]["condition"] = lambda d: d["nonexistent"]["key"]
        try:
            result = generate_recommendations({"seo": {"score": 50, "issues": []}})
            self.assertTrue(result["success"])
            self.assertNotIn("seo_add_meta_description",
                             [r["id"] for r in result["recommendations"]])
        finally:
            RECOMMENDATION_CATALOG["seo"]["add_meta_description"]["condition"] = original

    def test_rec_structure_fields(self):
        data = {
            "seo": {"score": 30, "issues": [{"severity": "h", "message": "Missing meta description"}]},
            "geo": {"score": 80, "issues": []},
            "aao": {"score": 70, "industry_detected": "general", "dimensions": {}},
        }
        result = generate_recommendations(data)
        for rec in result["recommendations"]:
            self.assertIn("id", rec)
            self.assertIn("pillar", rec)
            self.assertIn("title", rec)
            self.assertIn("detail", rec)
            self.assertIn("effort", rec)
            self.assertIn("impact", rec)
            self.assertIn("effort_estimate", rec)
            self.assertIn("impact_estimate", rec)

    def test_result_keys(self):
        result = generate_recommendations({})
        self.assertIn("success", result)
        self.assertIn("industry", result)
        self.assertIn("total", result)
        self.assertIn("recommendations", result)
        self.assertIn("quick_wins", result)
        self.assertIn("strategic", result)
        self.assertIn("maintenance", result)


if __name__ == "__main__":
    unittest.main()
