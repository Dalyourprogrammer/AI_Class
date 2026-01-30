import json
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.db")
TTL = timedelta(days=1)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS link_cache (
            title TEXT NOT NULL,
            link_type TEXT NOT NULL,
            links TEXT NOT NULL,
            cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (title, link_type)
        )
    """)
    return conn


def get_cached_links(title, link_type):
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT links, cached_at FROM link_cache WHERE title = ? AND link_type = ?",
            (title, link_type)
        ).fetchone()
        if row is None:
            return None
        cached_at = datetime.fromisoformat(row[1])
        if datetime.now() - cached_at > TTL:
            conn.execute(
                "DELETE FROM link_cache WHERE title = ? AND link_type = ?",
                (title, link_type)
            )
            conn.commit()
            return None
        return json.loads(row[0])
    finally:
        conn.close()


def set_cached_links(title, link_type, links):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO link_cache (title, link_type, links, cached_at) VALUES (?, ?, ?, ?)",
            (title, link_type, json.dumps(links), datetime.now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def clear_cache():
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM link_cache")
        conn.commit()
    finally:
        conn.close()
