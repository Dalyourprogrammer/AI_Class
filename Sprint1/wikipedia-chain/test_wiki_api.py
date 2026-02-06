"""Tests for wiki_api.py — must all pass before proceeding to Step 3."""
import sys
sys.path.insert(0, ".")
from wiki_api import validate_article, get_outgoing_links, get_backlinks

NAMESPACE_PREFIXES = ("Talk:", "Wikipedia:", "File:", "User:", "Template:",
                      "Category:", "Help:", "Portal:", "Module:", "Draft:")


def test_validate_existing():
    result = validate_article("Python (programming language)")
    assert result == "Python (programming language)", f"Got: {result}"
    print("PASS: validate existing article")


def test_validate_redirect():
    result = validate_article("USA")
    assert result == "United States", f"Got: {result}"
    print("PASS: validate redirect")


def test_validate_nonexistent():
    result = validate_article("Xyzzyxyzzy12345")
    assert result is None, f"Got: {result}"
    print("PASS: validate nonexistent article")


def test_outgoing_links():
    links = get_outgoing_links("Cat")
    assert isinstance(links, list), "Should return a list"
    assert len(links) > 0, "Should have links"
    assert all(isinstance(l, str) for l in links), "All links should be strings"
    assert "Mammal" in links, f"'Mammal' not found in Cat's links"
    for l in links:
        assert not any(l.startswith(p) for p in NAMESPACE_PREFIXES), f"Non-article link: {l}"
    print(f"PASS: outgoing links ({len(links)} links)")


def test_backlinks():
    links = get_backlinks("Cat")
    assert isinstance(links, list), "Should return a list"
    assert len(links) > 0, "Should have backlinks"
    assert all(isinstance(l, str) for l in links), "All links should be strings"
    for l in links:
        assert not any(l.startswith(p) for p in NAMESPACE_PREFIXES), f"Non-article link: {l}"
    print(f"PASS: backlinks ({len(links)} links)")


def test_pagination():
    links = get_outgoing_links("United States")
    assert len(links) > 500, f"Expected >500 links, got {len(links)} (pagination may be broken)"
    print(f"PASS: pagination ({len(links)} links for 'United States')")


if __name__ == "__main__":
    test_validate_existing()
    test_validate_redirect()
    test_validate_nonexistent()
    test_outgoing_links()
    test_backlinks()
    test_pagination()
    print("\nAll wiki_api tests passed.")
