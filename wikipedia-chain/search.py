from collections.abc import Callable
from wiki_api import get_outgoing_links, get_backlinks

MAX_DEPTH = 3


def find_chain(
    start: str,
    end: str,
    on_progress: Callable[[str], None] | None = None,
) -> list[str] | None:
    """Find a chain of Wikipedia articles from start to end using
    bidirectional iterative deepening search.

    Returns a list of article titles, or None if no chain is found
    within the depth limit. Calls on_progress with status updates
    at each depth iteration.
    """
    if start == end:
        return [start]

    forward_visited: dict[str, list[str]] = {start: [start]}
    backward_visited: dict[str, list[str]] = {end: [end]}

    forward_links_cache: dict[str, list[str]] = {}
    backward_links_cache: dict[str, list[str]] = {}

    for depth in range(1, MAX_DEPTH + 1):
        if on_progress:
            on_progress(f"Searching depth {depth}...")

        _dfs(start, depth, 0, [start], forward_visited,
             forward_links_cache, get_outgoing_links)
        _dfs(end, depth, 0, [end], backward_visited,
             backward_links_cache, get_backlinks)

        meeting = set(forward_visited.keys()) & set(backward_visited.keys())
        if meeting:
            best_chain: list[str] | None = None
            for node in meeting:
                fwd_path = forward_visited[node]
                bwd_path = backward_visited[node]
                chain = fwd_path + list(reversed(bwd_path))[1:]
                if best_chain is None or len(chain) < len(best_chain):
                    best_chain = chain
            return best_chain

    return None


def _dfs(
    title: str,
    max_depth: int,
    current_depth: int,
    path: list[str],
    visited: dict[str, list[str]],
    links_cache: dict[str, list[str]],
    get_links_fn: Callable[[str], list[str]],
) -> None:
    """Depth-limited DFS. Expands nodes and records paths in visited dict."""
    if current_depth >= max_depth:
        return

    if title in links_cache:
        links = links_cache[title]
    else:
        links = get_links_fn(title)
        links_cache[title] = links

    for link in links:
        if link not in visited:
            new_path = path + [link]
            visited[link] = new_path
            _dfs(link, max_depth, current_depth + 1,
                 new_path, visited, links_cache, get_links_fn)
