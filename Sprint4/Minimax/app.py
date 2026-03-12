from flask import Flask, jsonify, request, render_template
from game import (
    GameState, new_game, apply_turn, is_game_over, state_to_dict,
    get_reachable_with_dist, MOVE_RANGE, chebyshev
)
from minimax import get_ai_move

app = Flask(__name__)

game_state: GameState = new_game()
move_log: list = []
turn_count: int = 0
game_mode: str = "pvc"   # "pvc" | "pvp"
move_log_pending: dict = {}   # stores P1 log entry while waiting for P2 in PvP


def _did_hit(action, state_before, state_after, actor):
    if actor == "player":
        if action in ("fire_bolt", "dagger"):
            return state_after.ai_hp < state_before.ai_hp
    else:
        if action in ("fire_bolt", "dagger"):
            return state_after.player_hp < state_before.player_hp
    return False


def _build_anim_event(actor, action, from_pos, target_pos, pre_heal, hit):
    return {
        "actor": actor,
        "action": action,
        "from_pos": list(from_pos),
        "to_pos": list(target_pos),
        "hit": hit,
        "pre_heal": pre_heal,
    }


def _describe_action(actor, action, pre_heal, actor_start, pre_move_to, post_move_to, dash_to,
                     state_before, state_after):
    label = "P1" if actor == "player" else ("P2" if game_mode == "pvp" else "BOT")
    final_pos = dash_to if (action == "dash" and dash_to) else post_move_to

    if final_pos == actor_start and pre_move_to == actor_start:
        move_desc = "stayed"
    elif pre_move_to != actor_start and pre_move_to != final_pos:
        move_desc = f"{actor_start}→{pre_move_to}→{final_pos}"
    elif final_pos != actor_start:
        move_desc = f"→{final_pos}"
    else:
        move_desc = f"→{pre_move_to}→{final_pos}"

    parts = []
    if pre_heal:
        if actor == "player":
            gained = state_after.player_hp - state_before.player_hp
        else:
            gained = state_after.ai_hp - state_before.ai_hp
        parts.append(f"Healed +{gained} HP (free)")

    if action == "fire_bolt":
        if _did_hit(action, state_before, state_after, actor):
            dmg = (state_before.ai_hp - state_after.ai_hp) if actor == "player" else (state_before.player_hp - state_after.player_hp)
            parts.append(f"Fire Bolt hit for {dmg} dmg")
        else:
            parts.append("Fire Bolt missed")
    elif action == "dagger":
        if _did_hit(action, state_before, state_after, actor):
            dmg = (state_before.ai_hp - state_after.ai_hp) if actor == "player" else (state_before.player_hp - state_after.player_hp)
            parts.append(f"Dagger hit for {dmg} dmg")
        else:
            parts.append("Dagger missed")
    elif action == "dash":
        parts.append("Dashed")

    effect = " + ".join(parts) if parts else "Acted"
    return f"[{label} {move_desc}] {effect}"


def _win_msg(winner):
    if game_mode == "pvp":
        return "Player 1 wins!" if winner == "player" else "Player 2 wins!"
    return "You win!" if winner == "player" else "Bot wins!"


def build_state_response(msg="", animation_data=None):
    d = state_to_dict(game_state, msg)
    d["move_log"] = move_log[-10:]
    d["game_mode"] = game_mode
    if animation_data is not None:
        d["animation_data"] = animation_data
    return d


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/state")
def get_state():
    return jsonify(build_state_response())


@app.route("/new_game", methods=["POST"])
def reset_game():
    global game_state, move_log, turn_count, game_mode, move_log_pending
    data = request.get_json(silent=True) or {}
    game_mode = data.get("mode", "pvc")
    game_state = new_game()
    move_log = []
    move_log_pending = {}
    turn_count = 0
    return jsonify(build_state_response("New game! Player 1's turn."))


@app.route("/move", methods=["POST"])
def player_move():
    global game_state, move_log, turn_count, move_log_pending

    if is_game_over(game_state):
        return jsonify({"error": "Game is already over"}), 400

    current_actor = game_state.turn   # "player" or "ai"

    # In PvC mode only "player" POSTs; AI runs automatically after
    if game_mode == "pvc" and current_actor != "player":
        return jsonify({"error": "Not your turn"}), 400

    data = request.get_json()
    pre_heal = bool(data.get("pre_heal", False))
    actor_pos = game_state.player_pos if current_actor == "player" else game_state.ai_pos
    opp_pos = game_state.ai_pos if current_actor == "player" else game_state.player_pos

    pre_move_to = tuple(data.get("pre_move_to", actor_pos))
    action = data.get("action", "fire_bolt")
    post_move_to_raw = data.get("post_move_to")
    post_move_to = tuple(post_move_to_raw) if post_move_to_raw else pre_move_to
    dash_to_raw = data.get("dash_to")
    dash_to = tuple(dash_to_raw) if dash_to_raw else None

    blocked = frozenset({opp_pos})

    # Validate pre_move_to reachability
    pre_dists = get_reachable_with_dist(actor_pos, MOVE_RANGE, blocked)
    if pre_move_to not in pre_dists:
        return jsonify({"error": f"Invalid pre-move to {pre_move_to}"}), 400

    pre_dist = pre_dists[pre_move_to]
    remaining = MOVE_RANGE - pre_dist

    # Validate action
    valid_actions = ["fire_bolt"]
    if chebyshev(pre_move_to, opp_pos) == 1:
        valid_actions.append("dagger")
    valid_actions.append("dash")

    if action not in valid_actions:
        return jsonify({"error": f"Action '{action}' not available from that position"}), 400

    if action == "dash":
        if dash_to is not None:
            dash_cells = get_reachable_with_dist(pre_move_to, MOVE_RANGE, blocked)
            if dash_to not in dash_cells:
                return jsonify({"error": f"Invalid dash destination {dash_to}"}), 400
    else:
        post_cells = get_reachable_with_dist(pre_move_to, remaining, blocked)
        if post_move_to not in post_cells:
            return jsonify({"error": f"Invalid post-move to {post_move_to}"}), 400

    # Validate pre_heal: only if actor has potion
    actor_has_potion = (game_state.player_has_potion if current_actor == "player"
                        else game_state.ai_has_potion)
    if pre_heal and not actor_has_potion:
        pre_heal = False

    # Apply current actor's turn
    state_before = game_state
    game_state = apply_turn(game_state, pre_heal, pre_move_to, action, post_move_to, dash_to)

    hit = _did_hit(action, state_before, game_state, current_actor)
    anim_events = [_build_anim_event(current_actor, action, pre_move_to, opp_pos, pre_heal, hit)]

    log_entry = _describe_action(current_actor, action, pre_heal,
                                  actor_pos, pre_move_to, post_move_to, dash_to,
                                  state_before, game_state)

    winner = is_game_over(game_state)
    if winner:
        turn_count += 1
        other_actor = "ai" if current_actor == "player" else "player"
        move_log.append({"turn": turn_count, current_actor: log_entry, other_actor: "—"})
        return jsonify(build_state_response(_win_msg(winner), anim_events))

    # PvP: return after human move, let frontend prompt P2
    if game_mode == "pvp":
        if current_actor == "ai":
            turn_count += 1
            move_log.append({"turn": turn_count, "player": move_log_pending.pop("player", "—"), "ai": log_entry})
        else:
            # Store P1 log, wait for P2
            move_log_pending["player"] = log_entry
        next_actor = "ai" if current_actor == "player" else "player"
        who = "Player 2" if next_actor == "ai" else "Player 1"
        return jsonify(build_state_response(f"{who}'s turn!", anim_events))

    # PvC: run AI automatically
    state_before_ai = game_state
    ai_pos_before = game_state.ai_pos
    ai_pre_heal, ai_pre_move, ai_action, ai_post_move, ai_dash = get_ai_move(game_state)
    game_state = apply_turn(game_state, ai_pre_heal, ai_pre_move, ai_action, ai_post_move, ai_dash)

    ai_opp_pos = state_before_ai.player_pos
    ai_hit = _did_hit(ai_action, state_before_ai, game_state, "ai")
    anim_events.append(_build_anim_event("ai", ai_action, ai_pre_move, ai_opp_pos, ai_pre_heal, ai_hit))

    ai_log = _describe_action("ai", ai_action, ai_pre_heal,
                               ai_pos_before, ai_pre_move, ai_post_move, ai_dash,
                               state_before_ai, game_state)
    turn_count += 1
    move_log.append({"turn": turn_count, "player": log_entry, "ai": ai_log})

    winner = is_game_over(game_state)
    msg = _win_msg(winner) if winner else "Your turn!"
    return jsonify(build_state_response(msg, anim_events))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
