from flask import Flask, jsonify, request, render_template
from game import (
    GameState, new_game, apply_turn, is_game_over, state_to_dict,
    get_reachable_with_dist, COLUMNS, MOVE_RANGE, chebyshev
)
from minimax import get_ai_move

app = Flask(__name__)

game_state: GameState = new_game()
move_log: list = []
turn_count: int = 0


def describe_player_action(action, pre_move_to, post_move_to, dash_to, state_before, state_after):
    start = state_before.player_pos
    final_pos = dash_to if (action == "dash" and dash_to) else post_move_to

    if final_pos == start and pre_move_to == start:
        move_desc = "stayed"
    elif pre_move_to != start and pre_move_to != final_pos:
        move_desc = f"{start}→{pre_move_to}→{final_pos}"
    elif final_pos != start:
        move_desc = f"→{final_pos}"
    else:
        move_desc = f"→{pre_move_to}→{final_pos}"

    if action == "fire_bolt":
        if state_after.ai_hp < state_before.ai_hp:
            dmg = state_before.ai_hp - state_after.ai_hp
            effect = f"Fire Bolt hit for {dmg} dmg"
        else:
            effect = "Fire Bolt missed"
    elif action == "dagger":
        if state_after.ai_hp < state_before.ai_hp:
            dmg = state_before.ai_hp - state_after.ai_hp
            effect = f"Dagger hit for {dmg} dmg"
        else:
            effect = "Dagger missed"
    elif action == "heal":
        gained = state_after.player_hp - state_before.player_hp
        effect = f"Healed +{gained} HP"
    else:
        effect = "Dashed"

    return f"🧙 [{move_desc}] {effect}"


def describe_ai_action(action, pre_move, post_move, dash_to, state_before, state_after):
    start = state_before.ai_pos
    final_pos = dash_to if (action == "dash" and dash_to) else post_move
    msg_parts = []

    if final_pos == start and pre_move == start:
        msg_parts.append("AI stayed")
    elif pre_move != start and pre_move != final_pos:
        msg_parts.append(f"AI moved {start}→{pre_move}→{final_pos}")
    elif final_pos != start:
        msg_parts.append(f"AI moved to {final_pos}")
    else:
        msg_parts.append(f"AI moved to {pre_move} then back to {final_pos}")

    if action == "fire_bolt":
        if state_after.player_hp < state_before.player_hp:
            dmg = state_before.player_hp - state_after.player_hp
            msg_parts.append(f"Fire Bolt hit you for {dmg} damage!")
        else:
            msg_parts.append("Fire Bolt missed (blocked or not in line)")
    elif action == "dagger":
        if state_after.player_hp < state_before.player_hp:
            dmg = state_before.player_hp - state_after.player_hp
            msg_parts.append(f"Dagger struck you for {dmg} damage!")
        else:
            msg_parts.append("AI tried to Dagger but couldn't reach")
    elif action == "heal":
        msg_parts.append("AI used Heal Potion!")
    elif action == "dash":
        msg_parts.append(f"AI used Dash and moved to {dash_to}")

    return " | ".join(msg_parts)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/state")
def get_state():
    return jsonify(build_state_response())


def build_state_response(msg=""):
    d = state_to_dict(game_state, msg)
    d["move_log"] = move_log[-10:]  # last 10 entries
    return d


@app.route("/new_game", methods=["POST"])
def reset_game():
    global game_state, move_log, turn_count
    game_state = new_game()
    move_log = []
    turn_count = 0
    return jsonify(build_state_response("New game started! Your turn."))


@app.route("/move", methods=["POST"])
def player_move():
    global game_state, move_log, turn_count

    if game_state.turn != "player":
        return jsonify({"error": "Not your turn"}), 400

    if is_game_over(game_state):
        return jsonify({"error": "Game is already over"}), 400

    data = request.get_json()
    pre_move_to = tuple(data.get("pre_move_to", game_state.player_pos))
    action = data.get("action", "fire_bolt")
    post_move_to_raw = data.get("post_move_to")
    post_move_to = tuple(post_move_to_raw) if post_move_to_raw else pre_move_to
    dash_to_raw = data.get("dash_to")
    dash_to = tuple(dash_to_raw) if dash_to_raw else None

    opp_pos = game_state.ai_pos
    blocked = COLUMNS | {opp_pos}

    # Validate pre_move_to is reachable within MOVE_RANGE from player's current position
    pre_dists = get_reachable_with_dist(game_state.player_pos, MOVE_RANGE, blocked)
    if pre_move_to not in pre_dists:
        return jsonify({"error": f"Invalid pre-move to {pre_move_to}"}), 400

    pre_dist = pre_dists[pre_move_to]
    remaining = MOVE_RANGE - pre_dist

    # Validate action availability from pre_move_to
    valid_actions = ["fire_bolt"]
    if chebyshev(pre_move_to, opp_pos) == 1:
        valid_actions.append("dagger")
    if game_state.player_has_potion:
        valid_actions.append("heal")
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

    # Apply player turn
    state_before_player = game_state
    game_state = apply_turn(game_state, pre_move_to, action, post_move_to, dash_to)
    player_log = describe_player_action(action, pre_move_to, post_move_to, dash_to,
                                        state_before_player, game_state)

    winner = is_game_over(game_state)
    if winner:
        turn_count += 1
        move_log.append({"turn": turn_count, "player": player_log, "ai": "—"})
        result_msg = "You win! The AI has been defeated!" if winner == "player" else "AI wins! You were defeated!"
        return jsonify(build_state_response(result_msg))

    # AI move
    state_before_ai = game_state
    ai_pre_move, ai_action, ai_post_move, ai_dash_to = get_ai_move(game_state)
    game_state = apply_turn(game_state, ai_pre_move, ai_action, ai_post_move, ai_dash_to)
    ai_log = describe_ai_action(ai_action, ai_pre_move, ai_post_move, ai_dash_to,
                                state_before_ai, game_state)

    turn_count += 1
    move_log.append({"turn": turn_count, "player": player_log, "ai": f"🤖 {ai_log}"})

    winner = is_game_over(game_state)
    if winner:
        result_msg = "You win! The AI has been defeated!" if winner == "player" else "AI wins! You were defeated!"
        return jsonify(build_state_response(result_msg))

    return jsonify(build_state_response("Your turn!"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
