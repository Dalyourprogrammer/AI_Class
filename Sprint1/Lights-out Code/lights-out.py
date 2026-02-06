import time
from collections import deque
import matplotlib.pyplot as plt


def build_toggle_masks(N: int):
    """Precompute XOR masks for pressing each cell (self + 4-neighbors)."""
    masks = []
    for r in range(N):
        for c in range(N):
            m = 0
            for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
                rr, cc = r + dr, c + dc
                if 0 <= rr < N and 0 <= cc < N:
                    idx = rr * N + cc
                    m ^= (1 << idx)
            masks.append(m)
    return masks


def bfs_lights_out(N: int):
    """
    BFS over board states.
    Returns: (solution_moves, nodes_processed)
    where each move is an integer in [0, N*N-1] indicating which cell to press.
    """
    masks = build_toggle_masks(N)
    start = (1 << (N * N)) - 1  # all ON
    goal = 0

    q = deque([start])
    parent = {start: (None, None)}  # state -> (prev_state, move_index)
    nodes_processed = 0

    while q:
        s = q.popleft()
        nodes_processed += 1

        if s == goal:
            moves = []
            cur = s
            while parent[cur][0] is not None:
                prev, mv = parent[cur]
                moves.append(mv)
                cur = prev
            moves.reverse()
            return moves, nodes_processed

        for a, mask in enumerate(masks):
            ns = s ^ mask
            if ns not in parent:  # visited check
                parent[ns] = (s, a)
                q.append(ns)

    return None, nodes_processed


def dls(N: int, limit: int, masks, start: int, goal: int):
    """
    Depth-limited DFS with simple pruning:
    if we've already reached a state at a shallower depth, don't revisit it deeper.
    Returns: (solution_moves_or_None, nodes_processed_in_this_dls)
    """
    nodes = 0
    best_depth = {start: 0}
    path = []

    def rec(state: int, depth: int):
        nonlocal nodes
        nodes += 1

        if state == goal:
            return True
        if depth == limit:
            return False

        for a, mask in enumerate(masks):
            ns = state ^ mask
            nd = depth + 1

            bd = best_depth.get(ns)
            if bd is not None and bd <= nd:
                continue  # already found ns at same/shallower depth

            best_depth[ns] = nd
            path.append(a)
            if rec(ns, nd):
                return True
            path.pop()

        return False

    found = rec(start, 0)
    return (path.copy() if found else None), nodes


def iterative_deepening(N: int, max_limit=None):
    """
    Iterative deepening: run DLS with depth limit = 0,1,2,... until solution is found.
    Returns: (solution_moves, total_nodes_processed, depth_found)
    """
    masks = build_toggle_masks(N)
    start = (1 << (N * N)) - 1
    goal = 0

    if max_limit is None:
        max_limit = N * N  # practical cap for demo; you can increase if needed

    total_nodes = 0
    for limit in range(max_limit + 1):
        sol, nodes = dls(N, limit, masks, start, goal)
        total_nodes += nodes
        if sol is not None:
            return sol, total_nodes, limit

    return None, total_nodes, max_limit


def run_benchmark(N_values):
    results = []
    for N in N_values:
        # BFS
        t0 = time.perf_counter()
        sol_bfs, nodes_bfs = bfs_lights_out(N)
        t1 = time.perf_counter()

        # Iterative Deepening
        sol_id, nodes_id, depth = iterative_deepening(N)
        t2 = time.perf_counter()

        results.append({
            "N": N,
            "BFS_nodes": nodes_bfs,
            "BFS_time_s": t1 - t0,
            "ID_nodes": nodes_id,
            "ID_time_s": t2 - t1,
            "ID_found_depth": depth,
            "BFS_solution_len": (len(sol_bfs) if sol_bfs is not None else None),
        })
    return results


def main():
    # Keep N modest; BFS blows up fast as 2^(N^2).
    N_values = [2, 3, 4]

    results = run_benchmark(N_values)

    print("Results:")
    for row in results:
        print(row)

    Ns = [r["N"] for r in results]
    bfs_nodes = [r["BFS_nodes"] for r in results]
    id_nodes = [r["ID_nodes"] for r in results]
    bfs_time = [r["BFS_time_s"] for r in results]
    id_time = [r["ID_time_s"] for r in results]

    # Graph 1: nodes processed
    plt.figure()
    plt.plot(Ns, bfs_nodes, marker="o", label="BFS")
    plt.plot(Ns, id_nodes, marker="o", label="Iterative deepening")
    plt.xlabel("Grid size N")
    plt.ylabel("Nodes processed")
    plt.title("Lights Out: Nodes processed vs N")
    plt.legend()
    plt.tight_layout()
    plt.savefig("nodes_processed_vs_N.png")
    plt.close()

    # Graph 2: runtime
    plt.figure()
    plt.plot(Ns, bfs_time, marker="o", label="BFS")
    plt.plot(Ns, id_time, marker="o", label="Iterative deepening")
    plt.xlabel("Grid size N")
    plt.ylabel("Time (seconds)")
    plt.title("Lights Out: Runtime vs N")
    plt.legend()
    plt.tight_layout()
    plt.savefig("runtime_vs_N.png")
    plt.close()



if __name__ == "__main__":
    main()
