from game import (
    GameState, COLUMNS, MOVE_RANGE, get_reachable_with_dist, get_valid_actions,
    apply_turn, is_game_over, is_los_clear, manhattan, chebyshev
)

DEPTH = 4
WIN_SCORE = 10000


def evaluate(state: GameState) -> int:
    """Heuristic evaluation from the AI's perspective (higher = better for AI)."""
    winner = is_game_over(state)
    if winner == "ai":
        return WIN_SCORE
    if winner == "player":
        return -WIN_SCORE

    score = (state.ai_hp - state.player_hp) * 100

    # Potion advantage: having potion is a resource edge
    if state.player_has_potion and not state.ai_has_potion:
        score -= 20
    elif state.ai_has_potion and not state.player_has_potion:
        score += 20

    # Cover: AI adjacent to a column is harder to Fire Bolt
    ai_r, ai_c = state.ai_pos
    ai_near_cover = any(
        (ai_r + dr, ai_c + dc) in COLUMNS
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
    )
    if ai_near_cover:
        score += 10

    # Exposure: AI in player's LOS is a Fire Bolt threat
    if is_los_clear(state.ai_pos, state.player_pos):
        score -= 10

    # Dagger range: being adjacent to player is good for AI (can Dagger)
    dist = chebyshev(state.ai_pos, state.player_pos)
    if dist == 1:
        score += 15
    elif dist == 2:
        score += 5

    return score


def generate_moves(state: GameState):
    """Yield all (pre_move_to, action, post_move_to, dash_to) tuples for current actor.

    Split movement: actor moves 0-MOVE_RANGE steps to pre_move_to, resolves action there,
    then moves the remaining budget to post_move_to (or dashes to dash_to).
    """
    actor = state.turn
    actor_pos = state.player_pos if actor == "player" else state.ai_pos
    opp_pos = state.ai_pos if actor == "player" else state.player_pos
    has_potion = state.player_has_potion if actor == "player" else state.ai_has_potion

    blocked = COLUMNS | {opp_pos}
    # All positions reachable for first movement segment, keyed by min distance used
    pre_dists = get_reachable_with_dist(actor_pos, MOVE_RANGE, blocked)

    for pre_move_to, pre_dist in pre_dists.items():
        remaining = MOVE_RANGE - pre_dist

        # Valid actions depend on position at the moment of acting (pre_move_to)
        actions = ["fire_bolt"]
        if chebyshev(pre_move_to, opp_pos) == 1:
            actions.append("dagger")
        if has_potion:
            actions.append("heal")
        actions.append("dash")

        for action in actions:
            if action == "dash":
                # Dash: MOVE_RANGE extra steps from pre_move_to (replaces second movement)
                dash_cells = get_reachable_with_dist(pre_move_to, MOVE_RANGE, blocked)
                for dash_to in dash_cells:
                    yield (pre_move_to, "dash", None, dash_to)
            else:
                # Second movement segment: up to `remaining` steps from pre_move_to
                post_cells = get_reachable_with_dist(pre_move_to, remaining, blocked)
                for post_move_to in post_cells:
                    yield (pre_move_to, action, post_move_to, None)


def minimax(state: GameState, depth: int, alpha: int, beta: int, maximizing: bool):
    """Returns (score, best_move) where best_move is (pre_move_to, action, post_move_to, dash_to)."""
    winner = is_game_over(state)
    if winner is not None or depth == 0:
        return evaluate(state), None

    best_move = None

    if maximizing:
        best_score = -WIN_SCORE * 2
        for move in generate_moves(state):
            pre_move_to, action, post_move_to, dash_to = move
            next_state = apply_turn(state, pre_move_to, action, post_move_to, dash_to)
            score, _ = minimax(next_state, depth - 1, alpha, beta, False)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_score, best_move
    else:
        best_score = WIN_SCORE * 2
        for move in generate_moves(state):
            pre_move_to, action, post_move_to, dash_to = move
            next_state = apply_turn(state, pre_move_to, action, post_move_to, dash_to)
            score, _ = minimax(next_state, depth - 1, alpha, beta, True)
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move


def get_ai_move(state: GameState):
    """Entry point: returns best (pre_move_to, action, post_move_to, dash_to) for AI."""
    _, best_move = minimax(state, DEPTH, -WIN_SCORE * 2, WIN_SCORE * 2, True)
    if best_move is None:
        return (state.ai_pos, "fire_bolt", state.ai_pos, None)
    return best_move
