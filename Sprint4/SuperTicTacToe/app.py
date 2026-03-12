from flask import Flask, render_template, jsonify, request
from game import new_game, apply_move, get_legal_moves, is_terminal, state_to_dict
from mcts import mcts_search

app = Flask(__name__)

game_state = new_game()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/state')
def state():
    return jsonify(state_to_dict(game_state))


@app.route('/new_game', methods=['POST'])
def new_game_route():
    global game_state
    game_state = new_game()
    return jsonify(state_to_dict(game_state))


@app.route('/move', methods=['POST'])
def move():
    global game_state
    data = request.get_json()
    macro_idx = int(data['macro'])
    micro_idx = int(data['micro'])

    # Validate move
    legal = get_legal_moves(game_state)
    if (macro_idx, micro_idx) not in legal:
        return jsonify({'error': 'Illegal move'}), 400

    # Apply human move (X)
    game_state = apply_move(game_state, macro_idx, micro_idx)

    terminal, winner = is_terminal(game_state)
    if not terminal:
        # AI move (O)
        ai_move = mcts_search(game_state)
        if ai_move:
            game_state = apply_move(game_state, ai_move[0], ai_move[1])

    return jsonify(state_to_dict(game_state))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
