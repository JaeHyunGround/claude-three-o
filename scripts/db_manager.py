"""SQLite database manager for Three-O baseline and drift storage."""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path.home() / ".config" / "three-o" / "data" / "three_o.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            url TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            score REAL,
            data_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS geo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            platform TEXT NOT NULL,
            query TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            mentioned INTEGER,
            position INTEGER,
            sentiment TEXT,
            data_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS aao_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            url TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            score REAL,
            data_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            pillar TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            score REAL,
            data_json TEXT,
            locked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_seo_brand ON seo_snapshots(brand, timestamp);
        CREATE INDEX IF NOT EXISTS idx_geo_brand ON geo_snapshots(brand, timestamp);
        CREATE INDEX IF NOT EXISTS idx_aao_brand ON aao_snapshots(brand, timestamp);
        CREATE INDEX IF NOT EXISTS idx_baselines_brand ON baselines(brand, pillar);
    """)
    conn.commit()
    conn.close()


def save_snapshot(pillar: str, brand: str, url: str, score: float, data: Dict[str, Any]) -> None:
    """Save an audit snapshot."""
    conn = get_connection()
    timestamp = datetime.now().isoformat()
    table = f"{pillar}_snapshots"
    conn.execute(
        f"INSERT INTO {table} (brand, url, timestamp, score, data_json) VALUES (?, ?, ?, ?, ?)",
        (brand, url, timestamp, score, json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def get_latest_baseline(brand: str, pillar: str) -> Optional[Dict[str, Any]]:
    """Get most recent baseline for a brand/pillar."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM baselines WHERE brand = ? AND pillar = ? ORDER BY timestamp DESC LIMIT 1",
        (brand, pillar),
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def save_baseline(brand: str, pillar: str, score: float, data: Dict[str, Any], locked: bool = False) -> None:
    """Save a new baseline."""
    conn = get_connection()
    timestamp = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO baselines (brand, pillar, timestamp, score, data_json, locked) VALUES (?, ?, ?, ?, ?, ?)",
        (brand, pillar, timestamp, score, json.dumps(data, ensure_ascii=False), int(locked)),
    )
    conn.commit()
    conn.close()


def get_baseline_history(brand: str, pillar: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent baselines for a brand/pillar ordered by timestamp desc."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM baselines WHERE brand = ? AND pillar = ? ORDER BY timestamp DESC LIMIT ?",
        (brand, pillar, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_pillar_baselines(brand: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """Get recent baselines for all pillars."""
    return {
        "seo": get_baseline_history(brand, "seo", limit),
        "geo": get_baseline_history(brand, "geo", limit),
        "aao": get_baseline_history(brand, "aao", limit),
    }


def list_brands() -> List[str]:
    """List all brands with stored data."""
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT brand FROM baselines ORDER BY brand").fetchall()
    conn.close()
    return [row["brand"] for row in rows]


def cleanup_old_data(days: int = 365) -> None:
    """Remove snapshots older than specified days."""
    conn = get_connection()
    datetime.now().isoformat()
    for table in ["seo_snapshots", "geo_snapshots", "aao_snapshots"]:
        conn.execute(
            f"DELETE FROM {table} WHERE julianday('now') - julianday(timestamp) > ?",
            (days,),
        )
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Three-O database manager")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize database tables")
    sub.add_parser("brands", help="List stored brands")
    sub.add_parser("path", help="Show database path")

    cleanup = sub.add_parser("cleanup", help="Remove old data")
    cleanup.add_argument("--days", type=int, default=365, help="Remove data older than N days")

    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print("Database initialized." if not args.json else json.dumps({"status": "initialized", "path": str(DB_PATH)}))

    elif args.command == "brands":
        init_db()
        brands = list_brands()
        if args.json:
            print(json.dumps({"brands": brands}))
        else:
            print(f"Stored brands ({len(brands)}):")
            for b in brands:
                print(f"  - {b}")

    elif args.command == "path":
        result = {"path": str(DB_PATH), "exists": DB_PATH.exists()}
        if args.json:
            print(json.dumps(result))
        else:
            print(f"DB path: {DB_PATH} ({'exists' if DB_PATH.exists() else 'not created'})")

    elif args.command == "cleanup":
        init_db()
        cleanup_old_data(args.days)
        print(f"Cleaned data older than {args.days} days.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
