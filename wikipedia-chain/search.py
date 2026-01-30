from wiki_api import get_outgoing_links, get_backlinks

MAX_DEPTH = 3


def find_chain(start, end):
    """Find a chain of Wikipedia articles from start to end using
    bidirectional iterative deepening search.

    Returns a list of article titles, or None if no chain is found
    within the depth limit."""
    if start == end:
        return [start]

    # visited maps title -> path from origin
    forward_visited = {start: [start]}
    backward_visited = {end: [end]}

    # Cache of link results to avoid redundant API calls
    forward_links_cache = {}
    backward_links_cache = {}

    for depth in range(1, MAX_DEPTH + 1):
        _dfs(start, depth, 0, [start], forward_visited,
             forward_links_cache, get_outgoing_links)
        _dfs(end, depth, 0, [end], backward_visited,
             backward_links_cache, get_backlinks)

        meeting = set(forward_visited.keys()) & set(backward_visited.keys())
        if meeting:
            best_chain = None
            for node in meeting:
                fwd_path = forward_visited[node]
                bwd_path = backward_visited[node]
                chain = fwd_path + list(reversed(bwd_path))[1:]
                if best_chain is None or len(chain) < len(best_chain):
                    best_chain = chain
            return best_chain

    return None


def _dfs(title, max_depth, current_depth, path, visited, links_cache, get_links_fn):
    """Depth-limited DFS. Expands nodes and records paths in visited dict."""
    if current_depth >= max_depth:
        return

    # Fetch links, using cache to avoid repeated API calls
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
