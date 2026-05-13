"""Tests for db_manager.py — SQLite baseline and snapshot storage."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import db_manager


class DBTestCase(unittest.TestCase):
    """Base class that redirects DB_PATH to a temp file per test."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = Path(self.tmp.name)
        self.patcher = patch.object(db_manager, "DB_PATH", self.db_path)
        self.patcher.start()
        db_manager.init_db()

    def tearDown(self):
        self.patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        wal = Path(str(self.db_path) + "-wal")
        shm = Path(str(self.db_path) + "-shm")
        if wal.exists():
            wal.unlink()
        if shm.exists():
            shm.unlink()


class TestInitDB(DBTestCase):

    def test_creates_database_file(self):
        self.assertTrue(self.db_path.exists())

    def test_tables_exist(self):
        conn = db_manager.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        table_names = [t["name"] for t in tables]
        self.assertIn("baselines", table_names)
        self.assertIn("seo_snapshots", table_names)
        self.assertIn("geo_snapshots", table_names)
        self.assertIn("aao_snapshots", table_names)

    def test_idempotent(self):
        db_manager.init_db()
        db_manager.init_db()
        conn = db_manager.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        self.assertGreater(len(tables), 0)

    def test_indexes_created(self):
        conn = db_manager.get_connection()
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        conn.close()
        idx_names = [i["name"] for i in indexes]
        self.assertIn("idx_baselines_brand", idx_names)
        self.assertIn("idx_seo_brand", idx_names)


class TestGetConnection(DBTestCase):

    def test_returns_connection(self):
        conn = db_manager.get_connection()
        self.assertIsNotNone(conn)
        conn.close()

    def test_row_factory_set(self):
        conn = db_manager.get_connection()
        row = conn.execute("SELECT 1 AS val").fetchone()
        self.assertEqual(row["val"], 1)
        conn.close()

    def test_wal_mode(self):
        conn = db_manager.get_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()
        self.assertEqual(mode[0], "wal")
        conn.close()


class TestSaveAndGetBaseline(DBTestCase):

    def test_save_and_retrieve(self):
        db_manager.save_baseline("TestBrand", "seo", 75.5, {"meta": 80})
        result = db_manager.get_latest_baseline("TestBrand", "seo")
        self.assertIsNotNone(result)
        self.assertEqual(result["brand"], "TestBrand")
        self.assertEqual(result["pillar"], "seo")
        self.assertAlmostEqual(result["score"], 75.5)
        data = json.loads(result["data_json"])
        self.assertEqual(data["meta"], 80)

    def test_get_latest_returns_most_recent(self):
        db_manager.save_baseline("B", "seo", 50, {"v": 1})
        db_manager.save_baseline("B", "seo", 60, {"v": 2})
        db_manager.save_baseline("B", "seo", 70, {"v": 3})
        result = db_manager.get_latest_baseline("B", "seo")
        self.assertAlmostEqual(result["score"], 70)
        data = json.loads(result["data_json"])
        self.assertEqual(data["v"], 3)

    def test_different_pillars_independent(self):
        db_manager.save_baseline("B", "seo", 80, {})
        db_manager.save_baseline("B", "geo", 60, {})
        seo = db_manager.get_latest_baseline("B", "seo")
        geo = db_manager.get_latest_baseline("B", "geo")
        self.assertAlmostEqual(seo["score"], 80)
        self.assertAlmostEqual(geo["score"], 60)

    def test_different_brands_independent(self):
        db_manager.save_baseline("A", "seo", 90, {})
        db_manager.save_baseline("B", "seo", 40, {})
        a = db_manager.get_latest_baseline("A", "seo")
        b = db_manager.get_latest_baseline("B", "seo")
        self.assertAlmostEqual(a["score"], 90)
        self.assertAlmostEqual(b["score"], 40)

    def test_nonexistent_brand_returns_none(self):
        result = db_manager.get_latest_baseline("NoSuchBrand", "seo")
        self.assertIsNone(result)

    def test_nonexistent_pillar_returns_none(self):
        db_manager.save_baseline("B", "seo", 70, {})
        result = db_manager.get_latest_baseline("B", "aao")
        self.assertIsNone(result)

    def test_locked_baseline(self):
        db_manager.save_baseline("B", "seo", 70, {}, locked=True)
        result = db_manager.get_latest_baseline("B", "seo")
        self.assertEqual(result["locked"], 1)

    def test_unlocked_baseline_default(self):
        db_manager.save_baseline("B", "seo", 70, {})
        result = db_manager.get_latest_baseline("B", "seo")
        self.assertEqual(result["locked"], 0)

    def test_timestamp_set(self):
        db_manager.save_baseline("B", "seo", 70, {})
        result = db_manager.get_latest_baseline("B", "seo")
        self.assertIsNotNone(result["timestamp"])
        self.assertGreater(len(result["timestamp"]), 10)

    def test_korean_brand_name(self):
        db_manager.save_baseline("스카이벤처스", "geo", 55, {"test": "한글"})
        result = db_manager.get_latest_baseline("스카이벤처스", "geo")
        self.assertEqual(result["brand"], "스카이벤처스")
        data = json.loads(result["data_json"])
        self.assertEqual(data["test"], "한글")


class TestBaselineHistory(DBTestCase):

    def test_history_order_desc(self):
        for i in range(5):
            db_manager.save_baseline("B", "seo", 50 + i * 5, {"i": i})
        history = db_manager.get_baseline_history("B", "seo")
        scores = [h["score"] for h in history]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_history_limit(self):
        for i in range(10):
            db_manager.save_baseline("B", "seo", 50 + i, {})
        history = db_manager.get_baseline_history("B", "seo", limit=3)
        self.assertEqual(len(history), 3)

    def test_history_default_limit(self):
        for i in range(15):
            db_manager.save_baseline("B", "seo", i, {})
        history = db_manager.get_baseline_history("B", "seo")
        self.assertEqual(len(history), 10)

    def test_empty_history(self):
        history = db_manager.get_baseline_history("NoSuchBrand", "seo")
        self.assertEqual(history, [])

    def test_history_returns_dicts(self):
        db_manager.save_baseline("B", "seo", 70, {"x": 1})
        history = db_manager.get_baseline_history("B", "seo")
        self.assertIsInstance(history, list)
        self.assertIsInstance(history[0], dict)
        self.assertIn("score", history[0])
        self.assertIn("data_json", history[0])


class TestGetAllPillarBaselines(DBTestCase):

    def test_returns_all_three_pillars(self):
        result = db_manager.get_all_pillar_baselines("B")
        self.assertIn("seo", result)
        self.assertIn("geo", result)
        self.assertIn("aao", result)

    def test_empty_for_unknown_brand(self):
        result = db_manager.get_all_pillar_baselines("Unknown")
        for pillar in ["seo", "geo", "aao"]:
            self.assertEqual(result[pillar], [])

    def test_mixed_data(self):
        db_manager.save_baseline("B", "seo", 80, {})
        db_manager.save_baseline("B", "geo", 60, {})
        result = db_manager.get_all_pillar_baselines("B")
        self.assertEqual(len(result["seo"]), 1)
        self.assertEqual(len(result["geo"]), 1)
        self.assertEqual(len(result["aao"]), 0)

    def test_respects_limit(self):
        for i in range(8):
            db_manager.save_baseline("B", "seo", i, {})
        result = db_manager.get_all_pillar_baselines("B", limit=3)
        self.assertEqual(len(result["seo"]), 3)


class TestSaveSnapshot(DBTestCase):

    def test_save_seo_snapshot(self):
        db_manager.save_snapshot("seo", "B", "https://example.com", 70, {"meta": 80})
        conn = db_manager.get_connection()
        row = conn.execute("SELECT * FROM seo_snapshots WHERE brand = ?", ("B",)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["brand"], "B")
        self.assertEqual(row["url"], "https://example.com")
        self.assertAlmostEqual(row["score"], 70)

    def test_save_aao_snapshot(self):
        db_manager.save_snapshot("aao", "B", "https://example.com", 55, {"sel": 60})
        conn = db_manager.get_connection()
        row = conn.execute("SELECT * FROM aao_snapshots WHERE brand = ?", ("B",)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row["score"], 55)

    def test_multiple_snapshots(self):
        for i in range(5):
            db_manager.save_snapshot("seo", "B", "https://example.com", 50 + i, {})
        conn = db_manager.get_connection()
        count = conn.execute("SELECT COUNT(*) as c FROM seo_snapshots WHERE brand = ?", ("B",)).fetchone()
        conn.close()
        self.assertEqual(count["c"], 5)

    def test_data_json_stored(self):
        db_manager.save_snapshot("seo", "B", "https://ex.com", 70, {"dims": {"meta": 80, "perf": 60}})
        conn = db_manager.get_connection()
        row = conn.execute("SELECT data_json FROM seo_snapshots WHERE brand = ?", ("B",)).fetchone()
        conn.close()
        data = json.loads(row["data_json"])
        self.assertEqual(data["dims"]["meta"], 80)


class TestListBrands(DBTestCase):

    def test_empty_db(self):
        brands = db_manager.list_brands()
        self.assertEqual(brands, [])

    def test_single_brand(self):
        db_manager.save_baseline("Acme", "seo", 70, {})
        brands = db_manager.list_brands()
        self.assertEqual(brands, ["Acme"])

    def test_multiple_brands_sorted(self):
        db_manager.save_baseline("Zebra", "seo", 50, {})
        db_manager.save_baseline("Alpha", "geo", 60, {})
        db_manager.save_baseline("Mango", "aao", 70, {})
        brands = db_manager.list_brands()
        self.assertEqual(brands, ["Alpha", "Mango", "Zebra"])

    def test_deduplicated(self):
        db_manager.save_baseline("B", "seo", 50, {})
        db_manager.save_baseline("B", "geo", 60, {})
        db_manager.save_baseline("B", "seo", 70, {})
        brands = db_manager.list_brands()
        self.assertEqual(brands.count("B"), 1)


class TestCleanupOldData(DBTestCase):

    def test_cleanup_doesnt_crash_on_empty(self):
        db_manager.cleanup_old_data(days=30)

    def test_recent_data_preserved(self):
        db_manager.save_snapshot("seo", "B", "https://ex.com", 70, {})
        db_manager.cleanup_old_data(days=1)
        conn = db_manager.get_connection()
        count = conn.execute("SELECT COUNT(*) as c FROM seo_snapshots").fetchone()
        conn.close()
        self.assertEqual(count["c"], 1)

    def test_old_data_removed(self):
        conn = db_manager.get_connection()
        conn.execute(
            "INSERT INTO seo_snapshots (brand, url, timestamp, score, data_json) VALUES (?, ?, ?, ?, ?)",
            ("B", "https://ex.com", "2020-01-01T00:00:00", 70, "{}"),
        )
        conn.execute(
            "INSERT INTO aao_snapshots (brand, url, timestamp, score, data_json) VALUES (?, ?, ?, ?, ?)",
            ("B", "https://ex.com", "2020-01-01T00:00:00", 60, "{}"),
        )
        conn.commit()
        conn.close()
        db_manager.cleanup_old_data(days=30)
        conn = db_manager.get_connection()
        seo_count = conn.execute("SELECT COUNT(*) as c FROM seo_snapshots").fetchone()["c"]
        aao_count = conn.execute("SELECT COUNT(*) as c FROM aao_snapshots").fetchone()["c"]
        conn.close()
        self.assertEqual(seo_count + aao_count, 0)


if __name__ == "__main__":
    unittest.main()
