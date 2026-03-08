from game import (
    GameState, COLUMNS, get_reachable_cells, get_valid_actions,
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
    """Yield all (move_to, action, dash_to, action_first) tuples for current actor."""
    actor = state.turn
    actor_pos = state.player_pos if actor == "player" else state.ai_pos
    opp_pos = state.ai_pos if actor == "player" else state.player_pos

    blocked = COLUMNS | {opp_pos}
    reachable = get_reachable_cells(actor_pos, 2, blocked)
    reachable.add(actor_pos)  # staying in place is valid

    valid_actions = get_valid_actions(state, actor)

    for dest in reachable:
        for action in valid_actions:
            if action == "dash":
                blocked2 = COLUMNS | {opp_pos}
                secondary = get_reachable_cells(dest, 2, blocked2)
                secondary.add(dest)
                for dash_dest in secondary:
                    yield (dest, "dash", dash_dest, False)
            else:
                # Try both orderings; minimax will pick the best
                yield (dest, action, None, False)   # move first
                yield (dest, action, None, True)    # attack first


def minimax(state: GameState, depth: int, alpha: int, beta: int, maximizing: bool):
    """Returns (score, best_move) where best_move is (move_to, action, dash_to)."""
    winner = is_game_over(state)
    if winner is not None or depth == 0:
        return evaluate(state), None

    best_move = None

    if maximizing:
        best_score = -WIN_SCORE * 2
        for move in generate_moves(state):
            move_to, action, dash_to, action_first = move
            next_state = apply_turn(state, move_to, action, dash_to, action_first)
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
            move_to, action, dash_to, action_first = move
            next_state = apply_turn(state, move_to, action, dash_to, action_first)
            score, _ = minimax(next_state, depth - 1, alpha, beta, True)
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move


def get_ai_move(state: GameState):
    """Entry point: returns best (move_to, action, dash_to, action_first) for AI."""
    _, best_move = minimax(state, DEPTH, -WIN_SCORE * 2, WIN_SCORE * 2, True)
    if best_move is None:
        return (state.ai_pos, "fire_bolt", None, False)
    return best_move
