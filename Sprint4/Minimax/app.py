from flask import Flask, jsonify, request, render_template
from game import (
    GameState, new_game, apply_turn, is_game_over, state_to_dict,
    get_reachable_cells, get_valid_actions, COLUMNS, manhattan
)
from minimax import get_ai_move

app = Flask(__name__)

game_state: GameState = new_game()
move_log: list = []
turn_count: int = 0


def describe_ai_action(action: str, move_to: tuple, dash_to: tuple, state_before: GameState, state_after: GameState) -> str:
    from game import is_los_clear
    msg_parts = []

    if move_to != state_before.ai_pos:
        msg_parts.append(f"AI moved to {move_to}")
    else:
        msg_parts.append("AI stayed")

    if action == "fire_bolt":
        if state_after.player_hp < state_before.player_hp:
            dmg = state_before.player_hp - state_after.player_hp
            msg_parts.append(f"Fire Bolt hit you for {dmg} damage!")
        else:
            msg_parts.append("Fire Bolt missed (blocked by column or not in line)")
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


def describe_player_action(action, move_to, dash_to, state_before, state_after, action_first):
    pos = state_before.player_pos
    action_label = action.replace("_", " ").title()
    order = "attacked then moved" if action_first else "moved then acted"

    dest = dash_to if action == "dash" and dash_to else move_to
    move_desc = f"→ {dest}" if dest != state_before.player_pos else "stayed"

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

    return f"🧙 [{order}] {move_desc} | {effect}"


@app.route("/move", methods=["POST"])
def player_move():
    global game_state, move_log, turn_count

    if game_state.turn != "player":
        return jsonify({"error": "Not your turn"}), 400

    if is_game_over(game_state):
        return jsonify({"error": "Game is already over"}), 400

    data = request.get_json()
    move_to = tuple(data.get("move_to", game_state.player_pos))
    action = data.get("action", "fire_bolt")
    action_first = bool(data.get("action_first", False))
    dash_to_raw = data.get("dash_to")
    dash_to = tuple(dash_to_raw) if dash_to_raw else None

    # Validate move_to is reachable
    opp_pos = game_state.ai_pos
    blocked = COLUMNS | {opp_pos}
    reachable = get_reachable_cells(game_state.player_pos, 2, blocked)
    reachable.add(game_state.player_pos)

    if move_to not in reachable:
        return jsonify({"error": f"Invalid move to {move_to}"}), 400

    valid_actions = get_valid_actions(game_state, "player")
    if action not in valid_actions:
        return jsonify({"error": f"Action '{action}' not available"}), 400

    if action == "dash" and dash_to is not None:
        blocked2 = COLUMNS | {opp_pos}
        secondary = get_reachable_cells(move_to, 2, blocked2)
        secondary.add(move_to)
        if dash_to not in secondary:
            return jsonify({"error": f"Invalid dash destination {dash_to}"}), 400

    # Apply player turn
    state_before_player = game_state
    game_state = apply_turn(game_state, move_to, action, dash_to, action_first)
    player_log = describe_player_action(action, move_to, dash_to, state_before_player, game_state, action_first)

    winner = is_game_over(game_state)
    if winner:
        turn_count += 1
        move_log.append({"turn": turn_count, "player": player_log, "ai": "—"})
        result_msg = "You win! The AI has been defeated!" if winner == "player" else "AI wins! You were defeated!"
        return jsonify(build_state_response(result_msg))

    # AI move
    state_before_ai = game_state
    ai_move_to, ai_action, ai_dash_to, ai_action_first = get_ai_move(game_state)
    game_state = apply_turn(game_state, ai_move_to, ai_action, ai_dash_to, ai_action_first)
    ai_log = describe_ai_action(ai_action, ai_move_to, ai_dash_to, state_before_ai, game_state)

    turn_count += 1
    move_log.append({"turn": turn_count, "player": player_log, "ai": f"🤖 {ai_log}"})

    winner = is_game_over(game_state)
    if winner:
        result_msg = "You win! The AI has been defeated!" if winner == "player" else "AI wins! You were defeated!"
        return jsonify(build_state_response(result_msg))

    return jsonify(build_state_response("Your turn!"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
