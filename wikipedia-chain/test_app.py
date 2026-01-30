"""Tests for app.py — must all pass before proceeding to Step 5."""
import sys
sys.path.insert(0, ".")
from app import app


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_get_index():
    resp = client().get("/")
    assert resp.status_code == 200, f"GET / returned {resp.status_code}"
    print("PASS: GET / returns 200")


def test_successful_search():
    resp = client().post("/api/find-chain",
                         json={"start": "Cat", "end": "Mammal"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "found", f"Expected 'found', got {data['status']}"
    chain = data["chain"]
    assert chain[0]["title"] == "Cat"
    assert chain[-1]["title"] == "Mammal"
    for entry in chain:
        assert "title" in entry and "url" in entry
        assert entry["url"].startswith("https://en.wikipedia.org/wiki/")
    print(f"PASS: successful search — {len(chain)} articles")


def test_trivial_case():
    resp = client().post("/api/find-chain",
                         json={"start": "Cat", "end": "Cat"})
    data = resp.get_json()
    assert data["status"] == "found"
    assert len(data["chain"]) == 1
    assert data["chain"][0]["title"] == "Cat"
    print("PASS: trivial case")


def test_redirect_resolution():
    resp = client().post("/api/find-chain",
                         json={"start": "USA", "end": "USA"})
    data = resp.get_json()
    assert data["status"] == "found"
    assert data["chain"][0]["title"] == "United States"
    print("PASS: redirect resolution")


def test_invalid_article():
    resp = client().post("/api/find-chain",
                         json={"start": "Xyzzyxyzzy12345", "end": "Cat"})
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    print("PASS: invalid article error")


def test_missing_fields():
    for body in [{}, {"start": "Cat"}, {"end": "Cat"}]:
        resp = client().post("/api/find-chain", json=body)
        data = resp.get_json()
        assert data["status"] == "error", f"Expected error for {body}"
    print("PASS: missing fields error")


if __name__ == "__main__":
    test_get_index()
    test_successful_search()
    test_trivial_case()
    test_redirect_resolution()
    test_invalid_article()
    test_missing_fields()
    print("\nAll app tests passed.")
