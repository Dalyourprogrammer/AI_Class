"""
Sokobot — A* Sokoban Solver

Push-optimal A* search with deadlock detection for small Sokoban puzzles.
See solver.md for the full algorithmic design.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field
from itertools import permutations
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Direction helpers
# ---------------------------------------------------------------------------

class Dir(NamedTuple):
    dr: int
    dc: int
    name: str

UP    = Dir(-1,  0, "U")
DOWN  = Dir( 1,  0, "D")
LEFT  = Dir( 0, -1, "L")
RIGHT = Dir( 0,  1, "R")
DIRS  = (UP, DOWN, LEFT, RIGHT)

OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


# ---------------------------------------------------------------------------
# Level representation
# ---------------------------------------------------------------------------

Pos = tuple[int, int]

@dataclass
class Level:
    """Static, immutable data about a Sokoban level."""
    walls: frozenset[Pos]
    goals: frozenset[Pos]
    floors: frozenset[Pos]          # every non-wall cell
    dead_cells: frozenset[Pos]      # simple-deadlock cells (precomputed)
    width: int
    height: int
    initial_player: Pos
    initial_boxes: frozenset[Pos]


def parse_level(text: str) -> Level:
    """Parse a standard Sokoban level string into a Level object."""
    lines = text.rstrip("\n").split("\n")
    height = len(lines)
    width = max(len(line) for line in lines)

    walls: set[Pos] = set()
    goals: set[Pos] = set()
    floors: set[Pos] = set()
    boxes: set[Pos] = set()
    player: Pos | None = None

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            if ch == "#":
                walls.add((r, c))
            else:
                if ch != " " or _is_interior(r, c, lines):
                    floors.add((r, c))
                if ch == "@":
                    player = (r, c)
                elif ch == "+":        # player on goal
                    player = (r, c)
                    goals.add((r, c))
                elif ch == "$":
                    boxes.add((r, c))
                elif ch == "*":        # box on goal
                    boxes.add((r, c))
                    goals.add((r, c))
                elif ch == ".":
                    goals.add((r, c))

    if player is None:
        raise ValueError("Level has no player (@)")
    if len(boxes) == 0:
        raise ValueError("Level has no boxes ($)")
    if len(boxes) != len(goals):
        raise ValueError(
            f"Box count ({len(boxes)}) != goal count ({len(goals)})"
        )

    frozen_walls = frozenset(walls)
    frozen_floors = frozenset(floors)
    frozen_goals = frozenset(goals)
    dead = _compute_dead_cells(frozen_walls, frozen_floors, frozen_goals)

    return Level(
        walls=frozen_walls,
        goals=frozen_goals,
        floors=frozen_floors,
        dead_cells=dead,
        width=width,
        height=height,
        initial_player=player,
        initial_boxes=frozenset(boxes),
    )


def _is_interior(r: int, c: int, lines: list[str]) -> bool:
    """Rough check: a space is interior if there's a wall somewhere in every
    cardinal direction along its row/column.  Used to distinguish playable
    floor from exterior padding."""
    line = lines[r]
    has_wall_left = any(
        line[cc] == "#" for cc in range(c) if cc < len(line)
    )
    has_wall_right = any(
        line[cc] == "#" for cc in range(c + 1, len(line))
    )
    has_wall_up = any(
        r2 < len(lines) and c < len(lines[r2]) and lines[r2][c] == "#"
        for r2 in range(r)
    )
    has_wall_down = any(
        r2 < len(lines) and c < len(lines[r2]) and lines[r2][c] == "#"
        for r2 in range(r + 1, len(lines))
    )
    return has_wall_left and has_wall_right and has_wall_up and has_wall_down


# ---------------------------------------------------------------------------
# Simple deadlock precomputation  (reverse-push flood fill from each goal)
# ---------------------------------------------------------------------------

def _compute_dead_cells(
    walls: frozenset[Pos],
    floors: frozenset[Pos],
    goals: frozenset[Pos],
) -> frozenset[Pos]:
    """Return the set of floor cells from which a box can never reach any goal.

    Uses reverse-push BFS from each goal: a box at position P could have been
    pushed there from position Q if the cell on the far side of Q (the pull
    position) is also free.  Any floor cell NOT reached by any goal's reverse
    BFS is a dead cell.
    """
    reachable: set[Pos] = set()

    for goal in goals:
        visited: set[Pos] = {goal}
        queue: deque[Pos] = deque([goal])
        while queue:
            pos = queue.popleft()
            r, c = pos
            for d in DIRS:
                # In the forward direction, a push in direction d means:
                #   player at B-d, box at B, box moves to B+d.
                # Here pos = B+d (the box's current/destination cell).
                # So the box came from B = pos-d, but we want to expand
                # OUTWARD: find cells the box could have been at before.
                #
                # The box's previous position is pos+d (one step away),
                # and the player needed to be at pos+2*d (behind it) to
                # push it toward pos.
                prev_box = (r + d.dr, c + d.dc)
                player_pos = (r + 2 * d.dr, c + 2 * d.dc)
                if prev_box in floors and prev_box not in walls and \
                   player_pos in floors and player_pos not in walls and \
                   prev_box not in visited:
                    visited.add(prev_box)
                    queue.append(prev_box)
        reachable |= visited

    return frozenset(floors - reachable - goals)


# ---------------------------------------------------------------------------
# State & search helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class State:
    player: Pos
    boxes: frozenset[Pos]

    def __lt__(self, other: State) -> bool:
        return False   # tie-break for heapq; we don't care about ordering


def _normalize_player(player: Pos, boxes: frozenset[Pos],
                       level: Level) -> Pos:
    """Return the top-left reachable cell from `player`, treating boxes and
    walls as impassable.  This normalizes equivalent player positions."""
    blocked = level.walls | boxes
    visited: set[Pos] = {player}
    queue: deque[Pos] = deque([player])
    best = player
    while queue:
        pos = queue.popleft()
        if pos < best:
            best = pos
        r, c = pos
        for d in DIRS:
            nb = (r + d.dr, c + d.dc)
            if nb not in blocked and nb in level.floors and nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return best


def _player_reachable(player: Pos, boxes: frozenset[Pos],
                      level: Level) -> tuple[set[Pos], dict[Pos, Pos]]:
    """BFS from player position. Returns (reachable_set, parent_map).
    parent_map[pos] = previous pos on the shortest path from player."""
    blocked = level.walls | boxes
    visited: set[Pos] = {player}
    parent: dict[Pos, Pos] = {}
    queue: deque[Pos] = deque([player])
    while queue:
        pos = queue.popleft()
        r, c = pos
        for d in DIRS:
            nb = (r + d.dr, c + d.dc)
            if nb not in blocked and nb in level.floors and nb not in visited:
                visited.add(nb)
                parent[nb] = pos
                queue.append(nb)
    return visited, parent


def _reconstruct_path(parent: dict[Pos, Pos], start: Pos, end: Pos) -> list[Pos]:
    """Trace the BFS parent chain from end back to start."""
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Heuristic: minimum-cost box→goal matching
# ---------------------------------------------------------------------------

def _heuristic(boxes: frozenset[Pos], goals: frozenset[Pos]) -> int:
    """Minimum total Manhattan distance over all box-to-goal assignments."""
    box_list = list(boxes)
    goal_list = list(goals)
    n = len(box_list)
    if n == 0:
        return 0

    # Precompute distance matrix
    dists = [
        [abs(box_list[i][0] - goal_list[j][0]) +
         abs(box_list[i][1] - goal_list[j][1])
         for j in range(n)]
        for i in range(n)
    ]

    best = float("inf")
    for perm in permutations(range(n)):
        cost = sum(dists[i][perm[i]] for i in range(n))
        if cost < best:
            best = cost
    return int(best)


# ---------------------------------------------------------------------------
# Freeze deadlock detection
# ---------------------------------------------------------------------------

def _has_freeze_deadlock(boxes: frozenset[Pos], level: Level) -> bool:
    """Check if any box is frozen (can't move on either axis) and not on a goal."""
    box_set = set(boxes)
    frozen: set[Pos] = set()

    changed = True
    while changed:
        changed = False
        for box in box_set:
            if box in frozen:
                continue
            r, c = box

            def blocked(pos: Pos) -> bool:
                return pos in level.walls or pos in frozen

            h_frozen = blocked((r, c - 1)) and blocked((r, c + 1))
            v_frozen = blocked((r - 1, c)) and blocked((r + 1, c))

            if h_frozen and v_frozen:
                frozen.add(box)
                changed = True

    # If any frozen box is not on a goal, it's a deadlock
    for box in frozen:
        if box not in level.goals:
            return True
    return False


# ---------------------------------------------------------------------------
# A* solver
# ---------------------------------------------------------------------------

@dataclass
class PushAction:
    """Records a single push for solution reconstruction."""
    box_from: Pos
    box_to: Pos
    direction: Dir
    player_path: list[Pos]   # player's walk to the push position


@dataclass
class Solution:
    pushes: list[PushAction]
    states_explored: int

    def to_moves(self) -> list[str]:
        """Expand pushes into a flat list of move direction names
        (player steps + push steps) for animation."""
        moves: list[str] = []
        for push in self.pushes:
            # Player walks to push position
            for i in range(len(push.player_path) - 1):
                r1, c1 = push.player_path[i]
                r2, c2 = push.player_path[i + 1]
                dr, dc = r2 - r1, c2 - c1
                for d in DIRS:
                    if d.dr == dr and d.dc == dc:
                        moves.append(d.name.lower())
                        break
            # The push step itself
            moves.append(push.direction.name.upper())
        return moves


def solve(level_text: str, max_states: int = 1_000_000) -> Solution | None:
    """Solve a Sokoban level using A* search.

    Returns a Solution with the push sequence, or None if no solution found
    within the state limit.
    """
    level = parse_level(level_text)
    return solve_level(level, max_states)


def solve_level(level: Level, max_states: int = 1_000_000,
                progress_callback=None) -> Solution | None:
    """Solve a parsed Level object."""
    initial_boxes = level.initial_boxes

    # Quick check: any box already on a dead cell?
    for box in initial_boxes:
        if box in level.dead_cells:
            return None

    norm_player = _normalize_player(level.initial_player, initial_boxes, level)
    initial_state = State(norm_player, initial_boxes)

    if initial_boxes <= level.goals:
        return Solution(pushes=[], states_explored=0)

    # Priority queue: (f, g, state)
    h0 = _heuristic(initial_boxes, level.goals)
    open_heap: list[tuple[int, int, State]] = [(h0, 0, initial_state)]
    came_from: dict[State, tuple[State, PushAction]] = {}
    g_score: dict[State, int] = {initial_state: 0}
    closed: set[State] = set()
    states_explored = 0

    while open_heap and states_explored < max_states:
        f, g, state = heapq.heappop(open_heap)

        if state in closed:
            continue
        closed.add(state)
        states_explored += 1

        if progress_callback and states_explored % 5000 == 0:
            progress_callback(states_explored)

        # Goal check
        if state.boxes <= level.goals:
            return _build_solution(state, came_from, states_explored, level)

        # Player reachability from current (un-normalized) position
        # We need to use the actual position that leads to valid pushes.
        # Since we normalized, we need to recompute reachability from norm pos.
        reachable, parent_map = _player_reachable(
            state.player, state.boxes, level
        )

        # Generate all possible pushes
        for box in state.boxes:
            r, c = box
            for d in DIRS:
                # Player must be at box - d to push in direction d
                push_pos = (r - d.dr, c - d.dc)
                target = (r + d.dr, c + d.dc)

                # Player can reach push position?
                if push_pos not in reachable:
                    continue
                # Target cell is free?
                if target in level.walls or target in state.boxes:
                    continue

                # Dead cell check
                if target in level.dead_cells:
                    continue

                # Build new state
                new_boxes = (state.boxes - {box}) | {target}
                new_player = _normalize_player(box, new_boxes, level)
                new_state = State(new_player, new_boxes)

                if new_state in closed:
                    continue

                # Freeze deadlock check
                if _has_freeze_deadlock(new_boxes, level):
                    continue

                new_g = g + 1
                if new_state in g_score and new_g >= g_score[new_state]:
                    continue

                g_score[new_state] = new_g
                h = _heuristic(new_boxes, level.goals)
                heapq.heappush(open_heap, (new_g + h, new_g, new_state))

                # Record path for reconstruction
                player_path = _reconstruct_path(
                    parent_map, state.player, push_pos
                )
                came_from[new_state] = (
                    state,
                    PushAction(box, target, d, player_path),
                )

    return None  # no solution within state limit


def _build_solution(
    goal_state: State,
    came_from: dict[State, tuple[State, PushAction]],
    states_explored: int,
    level: Level,
) -> Solution:
    """Trace back through came_from to build the solution."""
    pushes: list[PushAction] = []
    state = goal_state
    while state in came_from:
        prev_state, action = came_from[state]
        pushes.append(action)
        state = prev_state
    pushes.reverse()
    return Solution(pushes=pushes, states_explored=states_explored)


# ---------------------------------------------------------------------------
# Pretty-print a state (for debugging)
# ---------------------------------------------------------------------------

def render_state(level: Level, state: State) -> str:
    """Render a state as a Sokoban level string."""
    lines = []
    for r in range(level.height):
        row = []
        for c in range(level.width):
            pos = (r, c)
            if pos in level.walls:
                row.append("#")
            elif pos in state.boxes and pos in level.goals:
                row.append("*")
            elif pos in state.boxes:
                row.append("$")
            elif pos == state.player and pos in level.goals:
                row.append("+")
            elif pos == state.player:
                row.append("@")
            elif pos in level.goals:
                row.append(".")
            elif pos in level.floors:
                row.append(" ")
            else:
                row.append(" ")
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick smoke test with a trivial puzzle
    test_level = """\
######
#.   #
# $  #
#  @ #
######"""

    print("Solving:")
    print(test_level)
    print()

    level = parse_level(test_level)
    print(f"Dead cells: {level.dead_cells}")
    print(f"Goals: {level.goals}")
    print(f"Boxes: {level.initial_boxes}")
    print()

    result = solve(test_level)
    if result:
        print(f"Solved in {len(result.pushes)} pushes, "
              f"{result.states_explored} states explored.")
        print(f"Moves: {result.to_moves()}")
    else:
        print("No solution found.")
