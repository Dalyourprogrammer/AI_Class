"""Tests for cache.py and caching integration — must all pass before proceeding."""
import os
import sys
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, ".")

# Use a test database
import cache
TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_cache.db")
cache.DB_PATH = TEST_DB

from cache import get_cached_links, set_cached_links, clear_cache


def cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_cache_miss():
    cleanup()
    result = get_cached_links("Cat", "outgoing")
    assert result is None, f"Expected None, got {result}"
    print("PASS: cache miss")


def test_write_and_read():
    cleanup()
    set_cached_links("Cat", "outgoing", ["Dog", "Mammal"])
    result = get_cached_links("Cat", "outgoing")
    assert result == ["Dog", "Mammal"], f"Got: {result}"
    print("PASS: cache write and read")


def test_separate_link_types():
    cleanup()
    set_cached_links("Cat", "outgoing", ["Dog"])
    set_cached_links("Cat", "backlinks", ["Kitten"])
    assert get_cached_links("Cat", "outgoing") == ["Dog"]
    assert get_cached_links("Cat", "backlinks") == ["Kitten"]
    print("PASS: separate link types")


def test_expiration():
    cleanup()
    # Insert a row with an old timestamp directly
    conn = sqlite3.connect(TEST_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS link_cache (
            title TEXT NOT NULL,
            link_type TEXT NOT NULL,
            links TEXT NOT NULL,
            cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (title, link_type)
        )
    """)
    old_time = (datetime.now() - timedelta(days=2)).isoformat()
    conn.execute(
        "INSERT INTO link_cache (title, link_type, links, cached_at) VALUES (?, ?, ?, ?)",
        ("Cat", "outgoing", '["Dog"]', old_time)
    )
    conn.commit()
    conn.close()

    result = get_cached_links("Cat", "outgoing")
    assert result is None, f"Expected None for expired entry, got {result}"
    print("PASS: cache expiration")


def test_clear():
    cleanup()
    set_cached_links("Cat", "outgoing", ["Dog"])
    set_cached_links("Dog", "backlinks", ["Cat"])
    clear_cache()
    assert get_cached_links("Cat", "outgoing") is None
    assert get_cached_links("Dog", "backlinks") is None
    print("PASS: cache clear")


def test_integration_with_wiki_api():
    cleanup()
    # Reload wiki_api to pick up test DB path
    import wiki_api
    links1 = wiki_api.get_outgoing_links("Cat")
    assert isinstance(links1, list) and len(links1) > 0

    # Verify it's cached
    cached = get_cached_links("Cat", "outgoing")
    assert cached is not None, "Should be cached after first call"
    assert cached == links1

    # Second call should return same result (from cache)
    links2 = wiki_api.get_outgoing_links("Cat")
    assert links1 == links2
    print(f"PASS: integration with wiki_api ({len(links1)} links cached)")


def test_delete_endpoint():
    cleanup()
    set_cached_links("Cat", "outgoing", ["Dog"])
    from app import app
    app.config["TESTING"] = True
    client = app.test_client()
    resp = client.delete("/api/cache")
    data = resp.get_json()
    assert data["status"] == "ok"
    assert get_cached_links("Cat", "outgoing") is None
    print("PASS: DELETE /api/cache endpoint")


def test_search_still_works():
    cleanup()
    from search import find_chain
    chain = find_chain("Cat", "Mammal")
    assert chain is not None
    assert chain[0] == "Cat"
    assert chain[-1] == "Mammal"
    print(f"PASS: search still works — {' → '.join(chain)}")


if __name__ == "__main__":
    test_cache_miss()
    test_write_and_read()
    test_separate_link_types()
    test_expiration()
    test_clear()
    test_integration_with_wiki_api()
    test_delete_endpoint()
    test_search_still_works()
    cleanup()
    print("\nAll cache tests passed.")
