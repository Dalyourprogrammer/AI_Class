from game import (
    GameState, MOVE_RANGE, get_reachable_with_dist,
    apply_turn, is_game_over, is_los_clear, chebyshev
)

DEPTH = 3
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
    """Yield all (pre_heal, pre_move_to, action, post_move_to, dash_to) tuples for current actor."""
    actor = state.turn
    actor_pos = state.player_pos if actor == "player" else state.ai_pos
    opp_pos = state.ai_pos if actor == "player" else state.player_pos
    has_potion = state.player_has_potion if actor == "player" else state.ai_has_potion

    blocked = frozenset({opp_pos})
    pre_dists = get_reachable_with_dist(actor_pos, MOVE_RANGE, blocked)

    pre_heal_options = [False, True] if has_potion else [False]

    for pre_heal in pre_heal_options:
        for pre_move_to, pre_dist in pre_dists.items():
            remaining = MOVE_RANGE - pre_dist

            actions = ["fire_bolt"]
            if chebyshev(pre_move_to, opp_pos) == 1:
                actions.append("dagger")
            actions.append("dash")

            for action in actions:
                if action == "dash":
                    dash_cells = get_reachable_with_dist(pre_move_to, MOVE_RANGE, blocked)
                    for dash_to in dash_cells:
                        yield (pre_heal, pre_move_to, "dash", None, dash_to)
                else:
                    post_cells = get_reachable_with_dist(pre_move_to, remaining, blocked)
                    for post_move_to in post_cells:
                        yield (pre_heal, pre_move_to, action, post_move_to, None)


def minimax(state: GameState, depth: int, alpha: int, beta: int, maximizing: bool):
    """Returns (score, best_move) where best_move is (pre_heal, pre_move_to, action, post_move_to, dash_to)."""
    winner = is_game_over(state)
    if winner is not None or depth == 0:
        return evaluate(state), None

    best_move = None

    if maximizing:
        best_score = -WIN_SCORE * 2
        for move in generate_moves(state):
            pre_heal, pre_move_to, action, post_move_to, dash_to = move
            next_state = apply_turn(state, pre_heal, pre_move_to, action, post_move_to, dash_to)
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
            pre_heal, pre_move_to, action, post_move_to, dash_to = move
            next_state = apply_turn(state, pre_heal, pre_move_to, action, post_move_to, dash_to)
            score, _ = minimax(next_state, depth - 1, alpha, beta, True)
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move


def get_ai_move(state: GameState):
    """Entry point: returns best (pre_heal, pre_move_to, action, post_move_to, dash_to) for AI."""
    _, best_move = minimax(state, DEPTH, -WIN_SCORE * 2, WIN_SCORE * 2, True)
    if best_move is None:
        return (False, state.ai_pos, "fire_bolt", state.ai_pos, None)
    return best_move
