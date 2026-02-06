"""Tests for search.py — must all pass before proceeding."""
import sys
sys.path.insert(0, ".")
from search import find_chain
from wiki_api import get_outgoing_links


def test_trivial():
    chain = find_chain("Cat", "Cat")
    assert chain == ["Cat"], f"Got: {chain}"
    print("PASS: trivial case")


def test_direct_link():
    links = get_outgoing_links("Cat")
    assert "Mammal" in links, "'Mammal' not in Cat's links"
    chain = find_chain("Cat", "Mammal")
    assert chain is not None
    assert chain[0] == "Cat" and chain[-1] == "Mammal"
    assert len(chain) == 2, f"Expected 2, got {len(chain)}"
    print(f"PASS: direct link — {' → '.join(chain)}")


def test_short_chain():
    chain = find_chain("Cat", "Dog")
    assert chain is not None
    assert chain[0] == "Cat" and chain[-1] == "Dog"
    assert len(chain) <= 7, f"Chain too long: {len(chain)}"
    print(f"PASS: short chain ({len(chain)} articles) — {' → '.join(chain)}")


def test_chain_validity():
    chain = find_chain("Cat", "Dog")
    assert chain is not None
    for i in range(len(chain) - 1):
        links = get_outgoing_links(chain[i])
        assert chain[i + 1] in links, \
            f"Invalid link: '{chain[i]}' does not link to '{chain[i+1]}'"
    print("PASS: chain validity verified")


def test_progress_callback():
    progress_messages = []
    chain = find_chain("Cat", "Dog", on_progress=lambda msg: progress_messages.append(msg))
    assert chain is not None
    assert len(progress_messages) > 0, "Progress callback was never called"
    assert any("depth" in msg.lower() for msg in progress_messages)
    print(f"PASS: progress callback ({len(progress_messages)} messages)")


if __name__ == "__main__":
    test_trivial()
    test_direct_link()
    test_short_chain()
    test_chain_validity()
    test_progress_callback()
    print("\nAll search tests passed.")
