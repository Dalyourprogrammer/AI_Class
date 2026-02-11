# Sokobot Solver — Algorithmic Design

## 1. Problem Formulation

Sokoban is a search problem where we must find a sequence of **pushes** that places every box on a goal.

**Standard level format:**
| Char | Meaning |
|------|---------|
| `#`  | Wall |
| ` `  | Floor |
| `.`  | Goal (storage location) |
| `$`  | Box |
| `@`  | Player |
| `*`  | Box on a goal |
| `+`  | Player on a goal |

---

## 2. State Representation

**Static data (computed once per level):**
- Set of wall cells
- Set of goal cells
- Set of floor cells (anything not a wall)
- Precomputed simple-deadlock map (see Section 5)

**Dynamic search state (what changes move-to-move):**
```
State = (player_position, frozenset(box_positions))
```
Both are `(row, col)` tuples. Using `frozenset` for boxes makes states hashable for the visited set.

**State normalization:** Two states with identical box positions are functionally equivalent if the player can reach the same set of cells. Instead of storing the raw player position, we normalize it to the **top-left cell of the player's reachable region** (flood fill from player position, blocked by walls and boxes). This collapses many equivalent states into one, dramatically shrinking the search space.

---

## 3. A* Search Algorithm

We use **push-optimal** A*, where each "move" is a single box push (not a player step). This is the standard approach for Sokoban solvers because it produces a smaller state space than step-optimal search.

```
OPEN  ← priority queue, ordered by f = g + h
CLOSED ← set of visited states

initial_state ← (normalize(player_pos, boxes), frozenset(boxes))
push initial_state onto OPEN with g=0, h=heuristic(boxes)

while OPEN is not empty:
    pop state with lowest f from OPEN

    if all boxes are on goals:
        return reconstruct_solution(state)

    if state in CLOSED:
        continue
    add state to CLOSED

    for each successor in generate_pushes(state):
        if successor not in CLOSED and not is_deadlock(successor):
            push successor onto OPEN with g+1, h=heuristic(successor.boxes)
```

**Step limit:** Cap at ~1,000,000 states explored to prevent runaway searches on hard instances. Return "no solution found" if exceeded.

### 3.1 Generating Successor States (Pushes)

For each box `B` at position `(r, c)`, consider all 4 push directions:

| Push direction | Player must be at | Box moves to |
|---------------|-------------------|-------------|
| Push Up       | `(r+1, c)` | `(r-1, c)` |
| Push Down     | `(r-1, c)` | `(r+1, c)` |
| Push Left     | `(r, c+1)` | `(r, c-1)` |
| Push Right    | `(r, c-1)` | `(r, c+1)` |

A push is valid if:
1. The player can **reach** the required position (BFS/flood fill from current player pos, avoiding walls and boxes)
2. The target cell for the box is **not a wall** and **not occupied by another box**

When a push is valid, the new state is:
- Player moves to the box's old position
- Box moves to the target cell
- Normalize the new player position

### 3.2 Player Reachability

Before generating pushes, compute the **player's reachable region** via BFS/flood fill from the current player position, treating walls and all box positions as impassable. This is computed once per state and reused for all push checks.

For solution playback, we also record the **player's path** to the push position (the BFS parent chain), so we can reconstruct full player movement for animation.

---

## 4. Heuristic Function

The heuristic must be **admissible** (never overestimates the true cost) for A* to find optimal solutions.

### 4.1 Minimum Matching Heuristic

We need to assign each box to a distinct goal to minimize total cost. This is the **assignment problem**.

**Cost matrix:** For each `(box_i, goal_j)` pair, compute the Manhattan distance `|box_r - goal_r| + |box_c - goal_c|`.

**Optimal assignment:** For ≤5 boxes, we can solve this by **enumerating all permutations** of goal assignments (5! = 120) and taking the minimum total cost. This is simpler than implementing the Hungarian algorithm and fast enough for our scale.

```python
from itertools import permutations

def heuristic(boxes, goals):
    boxes = list(boxes)
    goals = list(goals)
    min_cost = infinity
    for perm in permutations(range(len(goals))):
        cost = sum(manhattan(boxes[i], goals[perm[i]]) for i in range(len(boxes)))
        min_cost = min(min_cost, cost)
    return min_cost
```

**Why this is admissible:** Each box must be pushed to some goal, and Manhattan distance is a lower bound on pushes needed (you can't push a box in fewer moves than its Manhattan distance to the target). The optimal matching gives the tightest lower bound under this per-box relaxation.

### 4.2 Potential Enhancement: Actual Minimum Push Distance

Instead of Manhattan distance, precompute the true minimum pushes to move a box from any cell to each goal (using BFS on the single-box problem, ignoring other boxes). This accounts for walls that force detours. Still admissible, tighter bound, but requires precomputation. Worth implementing if performance demands it.

---

## 5. Deadlock Detection

Deadlock detection is **critical** for performance. Without it, A* wastes enormous effort exploring states that can never lead to a solution.

### 5.1 Simple Deadlocks (Static — Precomputed)

A cell is a **simple deadlock** if a box placed on it can never reach any goal, regardless of the player's actions and ignoring other boxes.

**Detection method — reverse reachability:**
For each goal position, perform a **reverse-push flood fill**: starting from the goal, find all cells a box could be pulled to (equivalently, all cells from which a box could be pushed to this goal).

Reverse-push from cell `(r, c)` in direction `d`:
- The box would move from `(r, c)` to the cell opposite to `d`
- The "pull position" (where the player would need to stand) is on the same side as `d`
- Valid if the target cell and pull position are both floor (not wall)

A cell is a simple deadlock if it is **not reachable from any goal's** reverse flood fill. Precompute this as a boolean grid at level load time.

**What this catches:**
- Corner squares (box against two walls) not on goals
- Dead-end corridors with no goals
- Cells blocked by wall geometry

```
Example:  # # # # #
          # . $ # #    ← the box can reach the goal
          #   $ # #    ← this box is in a corner deadlock (against right wall + bottom wall)
          # # # # #
```

### 5.2 Freeze Deadlocks (Dynamic — Per State)

A box is **frozen** if it cannot move along either axis. If a frozen box is not on a goal, the state is a deadlock.

**Frozen along horizontal axis:** The box cannot be pushed left or right. True if:
- Wall on both left and right, OR
- Wall on one side and a frozen box on the other, OR
- Frozen boxes on both sides

**Frozen along vertical axis:** Same logic for up and down.

**A box is fully frozen** if it is frozen on both axes simultaneously.

**Detection algorithm (iterative):**
Because freezing is mutually recursive (box A frozen because of box B, and vice versa), we use iterative marking:

```
repeat:
    changed = false
    for each box B:
        h_blocked = (wall_or_frozen_box on left of B) AND (wall_or_frozen_box on right of B)
        v_blocked = (wall_or_frozen_box above B) AND (wall_or_frozen_box below B)
        if h_blocked and v_blocked and B not already marked frozen:
            mark B as frozen
            changed = true
until not changed

if any frozen box is not on a goal:
    state is a deadlock
```

**What this catches:**
- Two boxes side-by-side against a wall (neither can move)
- Box clusters that mutually block each other
- A box pushed into a wall where the perpendicular direction is also blocked

```
Example:  # # # # #
          #   $ $ #    ← both boxes frozen against right wall
          #       #       (horizontal: wall right, box left for right box)
          # # # # #       (vertical: wall above for both)
```

### 5.3 What We Skip (Too Complex for Our Scope)

- **Corral deadlocks:** Regions enclosed by boxes/walls where the player can't enter. Complex to detect, diminishing returns for small puzzles.
- **Bipartite deadlocks:** Checking if the remaining boxes-to-goals assignment is even feasible given wall geometry. Requires per-state matching.
- **PI-corral deadlocks:** Even more advanced. Used in championship-level solvers.

For puzzles ≤8x8 with ≤5 boxes, simple + freeze deadlocks prune the vast majority of hopeless states.

---

## 6. Solution Reconstruction

A* stores a `came_from` map: `state → (parent_state, push_action)`. Once a goal state is found, trace back through this map to reconstruct the sequence of pushes.

Each push action records:
- Which box was pushed
- The direction of the push
- The player's path to the push position (from the BFS during successor generation)

For the web UI playback, we expand each push into the full sequence of player moves:
1. Player walks from current position to the push position (BFS path)
2. Player pushes the box (one step in the push direction)

This gives a step-by-step animation sequence: `[U, U, R, R, PUSH_DOWN, L, L, PUSH_LEFT, ...]`

---

## 7. Complexity and Practical Limits

**State space size** (worst case): For an 8x8 board with ~40 open cells and 5 boxes:
- Box arrangements: C(40, 5) ≈ 658,000
- Player positions: ~35 reachable cells per arrangement
- Total: ~23 million states (upper bound, most are pruned)

With normalization and deadlock pruning, the effective search space is typically 10-100x smaller. A* with a good heuristic explores a fraction of even that. Most 5-box puzzles on an 8x8 board solve in under 100,000 states.

**Time per state:** BFS for reachability (~40 cells), heuristic computation (120 permutations × 5 additions), deadlock check. Roughly ~1-5 microseconds. 1M states ≈ 1-5 seconds.

---

## 8. Summary

| Component | Approach |
|-----------|----------|
| Search | A* (push-optimal) |
| State | `(normalized_player_pos, frozenset(boxes))` |
| Heuristic | Min-cost box→goal matching via permutation enumeration |
| Static deadlocks | Reverse-push reachability from goals |
| Dynamic deadlocks | Iterative freeze detection |
| State limit | ~1M states explored |
| Target puzzles | ≤8x8 board, ≤5 boxes |
