"""Tests for search.py — must all pass before proceeding to Step 4."""
import sys
sys.path.insert(0, ".")
from search import find_chain
from wiki_api import get_outgoing_links


def test_trivial():
    chain = find_chain("Cat", "Cat")
    assert chain == ["Cat"], f"Got: {chain}"
    print("PASS: trivial case")


def test_direct_link():
    # Verify Mammal is in Cat's outgoing links
    links = get_outgoing_links("Cat")
    assert "Mammal" in links, "'Mammal' not in Cat's links — test assumption broken"
    chain = find_chain("Cat", "Mammal")
    assert chain is not None, "Should find a chain"
    assert chain[0] == "Cat", f"Chain should start with Cat, got {chain[0]}"
    assert chain[-1] == "Mammal", f"Chain should end with Mammal, got {chain[-1]}"
    assert len(chain) == 2, f"Direct link should have 2 articles, got {len(chain)}"
    print(f"PASS: direct link — {' → '.join(chain)}")


def test_short_chain():
    chain = find_chain("Cat", "Dog")
    assert chain is not None, "Should find a chain"
    assert chain[0] == "Cat", f"Chain should start with Cat, got {chain[0]}"
    assert chain[-1] == "Dog", f"Chain should end with Dog, got {chain[-1]}"
    assert len(chain) <= 7, f"Chain too long: {len(chain)}"
    print(f"PASS: short chain ({len(chain)} articles) — {' → '.join(chain)}")


def test_chain_validity():
    """Verify each consecutive pair is actually linked."""
    chain = find_chain("Cat", "Dog")
    assert chain is not None
    for i in range(len(chain) - 1):
        links = get_outgoing_links(chain[i])
        assert chain[i + 1] in links, \
            f"Invalid link: '{chain[i]}' does not link to '{chain[i+1]}'"
    print("PASS: chain validity verified")


if __name__ == "__main__":
    test_trivial()
    test_direct_link()
    test_short_chain()
    test_chain_validity()
    print("\nAll search tests passed.")
