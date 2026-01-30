"""Tests for app.py — must all pass before proceeding."""
import sys
import time
sys.path.insert(0, ".")
from app import app


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_get_index():
    resp = client().get("/")
    assert resp.status_code == 200
    print("PASS: GET / returns 200")


def test_job_creation():
    c = client()
    resp = c.post("/api/search", json={"start": "Cat", "end": "Mammal"})
    data = resp.get_json()
    assert data["status"] == "ok", f"Expected 'ok', got {data}"
    assert "job_id" in data and len(data["job_id"]) > 0
    print(f"PASS: job creation (job_id={data['job_id'][:8]}...)")


def test_polling_found():
    c = client()
    resp = c.post("/api/search", json={"start": "Cat", "end": "Mammal"})
    data = resp.get_json()
    job_id = data["job_id"]

    # Poll until done
    for _ in range(60):
        resp = c.get(f"/api/search/{job_id}")
        data = resp.get_json()
        if data["status"] != "searching":
            break
        time.sleep(1)

    assert data["status"] == "found", f"Expected 'found', got {data}"
    chain = data["chain"]
    assert chain[0]["title"] == "Cat"
    assert chain[-1]["title"] == "Mammal"
    for entry in chain:
        assert "title" in entry and "url" in entry
        assert entry["url"].startswith("https://en.wikipedia.org/wiki/")
    print(f"PASS: polling found — {len(chain)} articles")


def test_trivial_case():
    resp = client().post("/api/search", json={"start": "Cat", "end": "Cat"})
    data = resp.get_json()
    assert data["status"] == "found"
    assert len(data["chain"]) == 1
    assert data["chain"][0]["title"] == "Cat"
    print("PASS: trivial case (immediate, no job)")


def test_redirect_resolution():
    resp = client().post("/api/search", json={"start": "USA", "end": "USA"})
    data = resp.get_json()
    assert data["status"] == "found"
    assert data["chain"][0]["title"] == "United States"
    print("PASS: redirect resolution")


def test_invalid_article():
    resp = client().post("/api/search", json={"start": "Xyzzyxyzzy12345", "end": "Cat"})
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    print("PASS: invalid article error")


def test_missing_fields():
    for body in [{}, {"start": "Cat"}, {"end": "Cat"}]:
        resp = client().post("/api/search", json=body)
        data = resp.get_json()
        assert data["status"] == "error", f"Expected error for {body}"
    print("PASS: missing fields error")


def test_invalid_job_id():
    resp = client().get("/api/search/nonexistent")
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    print("PASS: invalid job ID")


def test_delete_cache():
    resp = client().delete("/api/cache")
    data = resp.get_json()
    assert data["status"] == "ok"
    print("PASS: DELETE /api/cache")


if __name__ == "__main__":
    test_get_index()
    test_job_creation()
    test_polling_found()
    test_trivial_case()
    test_redirect_resolution()
    test_invalid_article()
    test_missing_fields()
    test_invalid_job_id()
    test_delete_cache()
    print("\nAll app tests passed.")
