from dataclasses import dataclass, replace
from collections import deque

GRID_SIZE = 5
MAX_HP = 3
MOVE_RANGE = 2
COLUMNS = frozenset({(1, 1), (1, 3), (3, 1), (3, 3)})
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

ACTIONS = ["fire_bolt", "dagger", "heal", "dash"]


@dataclass(frozen=True)
class GameState:
    player_pos: tuple       # (row, col)
    ai_pos: tuple           # (row, col)
    player_hp: int
    ai_hp: int
    player_has_potion: bool
    ai_has_potion: bool
    turn: str               # "player" | "ai"


def new_game() -> GameState:
    return GameState(
        player_pos=(0, 0),
        ai_pos=(4, 4),
        player_hp=MAX_HP,
        ai_hp=MAX_HP,
        player_has_potion=True,
        ai_has_potion=True,
        turn="player",
    )


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE


def get_reachable_cells(from_pos: tuple, steps: int, blocked: frozenset) -> set:
    """BFS: all cells reachable within `steps` orthogonal moves, avoiding blocked cells."""
    visited = {from_pos}
    frontier = deque([(from_pos, 0)])
    reachable = set()

    while frontier:
        pos, dist = frontier.popleft()
        if dist > 0:
            reachable.add(pos)
        if dist == steps:
            continue
        r, c = pos
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            npos = (nr, nc)
            if in_bounds(nr, nc) and npos not in blocked and npos not in visited:
                visited.add(npos)
                frontier.append((npos, dist + 1))

    return reachable


def get_reachable_with_dist(from_pos: tuple, max_steps: int, blocked: frozenset) -> dict:
    """BFS: returns {pos: min_dist} for all cells reachable within max_steps, including from_pos (dist 0)."""
    dists = {from_pos: 0}
    frontier = deque([(from_pos, 0)])

    while frontier:
        pos, dist = frontier.popleft()
        if dist == max_steps:
            continue
        r, c = pos
        for dr, dc in DIRECTIONS:
            nr, nc = r + dr, c + dc
            npos = (nr, nc)
            if in_bounds(nr, nc) and npos not in blocked and npos not in dists:
                dists[npos] = dist + 1
                frontier.append((npos, dist + 1))

    return dists


def is_los_clear(pos_a: tuple, pos_b: tuple) -> bool:
    """Returns True if pos_a and pos_b are in the same row, column, or diagonal
    with no column blocking LOS."""
    r1, c1 = pos_a
    r2, c2 = pos_b

    dr = r2 - r1
    dc = c2 - c1

    # Must be same row, column, or diagonal
    if dr != 0 and dc != 0 and abs(dr) != abs(dc):
        return False

    # Step one cell at a time from pos_a toward pos_b, checking for blocking columns
    step_r = 0 if dr == 0 else (1 if dr > 0 else -1)
    step_c = 0 if dc == 0 else (1 if dc > 0 else -1)

    r, c = r1 + step_r, c1 + step_c
    while (r, c) != (r2, c2):
        if (r, c) in COLUMNS:
            return False
        r += step_r
        c += step_c

    return True


def manhattan(pos_a: tuple, pos_b: tuple) -> int:
    return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])


def chebyshev(pos_a: tuple, pos_b: tuple) -> int:
    """Max of row/col difference — includes diagonal adjacency."""
    return max(abs(pos_a[0] - pos_b[0]), abs(pos_a[1] - pos_b[1]))


def get_valid_actions(state: GameState, actor: str) -> list:
    """Return list of valid action names for actor in current state."""
    if actor == "player":
        actor_pos = state.player_pos
        opp_pos = state.ai_pos
        has_potion = state.player_has_potion
    else:
        actor_pos = state.ai_pos
        opp_pos = state.player_pos
        has_potion = state.ai_has_potion

    actions = []

    # Fire Bolt: always an option (may or may not deal damage)
    actions.append("fire_bolt")

    # Dagger: adjacent orthogonally or diagonally
    if chebyshev(actor_pos, opp_pos) == 1:
        actions.append("dagger")

    # Heal Potion: only if unused
    if has_potion:
        actions.append("heal")

    # Dash: always available
    actions.append("dash")

    return actions


def _resolve_action(actor: str, action: str, actor_pos: tuple, opp_pos: tuple,
                    player_hp: int, ai_hp: int,
                    player_has_potion: bool, ai_has_potion: bool):
    """Apply action effects and return updated (player_hp, ai_hp, player_has_potion, ai_has_potion)."""
    if action == "fire_bolt":
        if is_los_clear(actor_pos, opp_pos):
            if actor == "player":
                ai_hp = max(0, ai_hp - 1)
            else:
                player_hp = max(0, player_hp - 1)

    elif action == "dagger":
        if chebyshev(actor_pos, opp_pos) == 1:
            if actor == "player":
                ai_hp = max(0, ai_hp - 2)
            else:
                player_hp = max(0, player_hp - 2)

    elif action == "heal":
        if actor == "player" and player_has_potion:
            player_hp = min(MAX_HP, player_hp + 2)
            player_has_potion = False
        elif actor == "ai" and ai_has_potion:
            ai_hp = min(MAX_HP, ai_hp + 2)
            ai_has_potion = False

    return player_hp, ai_hp, player_has_potion, ai_has_potion


def apply_turn(state: GameState, pre_move_to: tuple, action: str,
               post_move_to: tuple = None, dash_to: tuple = None) -> GameState:
    """Apply a full turn with split movement: move to pre_move_to, resolve action there,
    then move to post_move_to (or dash_to for dash action). Returns new state with turn flipped.

    pre_move_to  — position where the actor is when they act (first movement segment)
    action       — the action resolved at pre_move_to
    post_move_to — final position after the action (second movement segment; non-dash actions)
    dash_to      — final position after dash extra movement (dash action only)
    """
    actor = state.turn
    opp_pos = state.ai_pos if actor == "player" else state.player_pos

    player_hp, ai_hp = state.player_hp, state.ai_hp
    player_has_potion, ai_has_potion = state.player_has_potion, state.ai_has_potion

    # Resolve action at pre_move_to
    player_hp, ai_hp, player_has_potion, ai_has_potion = _resolve_action(
        actor, action, pre_move_to, opp_pos,
        player_hp, ai_hp, player_has_potion, ai_has_potion
    )

    # Determine final resting position
    if action == "dash":
        final_pos = dash_to if dash_to is not None else pre_move_to
    else:
        final_pos = post_move_to if post_move_to is not None else pre_move_to

    if actor == "player":
        new_state = replace(state, player_pos=final_pos,
                            player_hp=player_hp, ai_hp=ai_hp,
                            player_has_potion=player_has_potion, ai_has_potion=ai_has_potion)
    else:
        new_state = replace(state, ai_pos=final_pos,
                            player_hp=player_hp, ai_hp=ai_hp,
                            player_has_potion=player_has_potion, ai_has_potion=ai_has_potion)

    return replace(new_state, turn="ai" if actor == "player" else "player")


def is_game_over(state: GameState):
    """Returns None if ongoing, 'player' or 'ai' for the winner."""
    if state.ai_hp <= 0:
        return "player"
    if state.player_hp <= 0:
        return "ai"
    return None


def state_to_dict(state: GameState, extra_message: str = "") -> dict:
    actor = state.turn
    actor_pos = state.player_pos if actor == "player" else state.ai_pos
    opp_pos = state.ai_pos if actor == "player" else state.player_pos

    blocked = COLUMNS | {opp_pos}
    valid_moves = list(get_reachable_cells(actor_pos, MOVE_RANGE, blocked))

    winner = is_game_over(state)

    return {
        "player_pos": list(state.player_pos),
        "ai_pos": list(state.ai_pos),
        "player_hp": state.player_hp,
        "ai_hp": state.ai_hp,
        "player_has_potion": state.player_has_potion,
        "ai_has_potion": state.ai_has_potion,
        "turn": state.turn,
        "game_over": winner is not None,
        "winner": winner,
        "message": extra_message or ("Your turn!" if state.turn == "player" else "AI is thinking..."),
        "valid_moves": [list(m) for m in valid_moves],
        "columns": [list(c) for c in COLUMNS],
        "max_hp": MAX_HP,
        "move_range": MOVE_RANGE,
    }
