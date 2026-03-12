import math
import random
from game import GameState, get_legal_moves, apply_move, is_terminal

MCTS_ITERATIONS = 5000
C = math.sqrt(2)


class MCTSNode:
    def __init__(self, state: GameState, move=None, parent=None):
        self.state = state
        self.move = move          # (macro_idx, micro_idx) that led to this node
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0.0
        moves = get_legal_moves(state)
        random.shuffle(moves)
        self.untried_moves = moves

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def ucb1(self):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + C * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

    def best_child(self):
        return max(self.children, key=lambda c: c.ucb1())

    def best_move_child(self):
        """Select child with best win rate (used at root after search)."""
        return max(self.children, key=lambda c: c.wins / c.visits if c.visits > 0 else 0)


def rollout(state: GameState) -> int:
    """Random playout from state. Returns winner: 1=X, 2=O, 0=draw."""
    while True:
        terminal, winner = is_terminal(state)
        if terminal:
            return winner
        moves = get_legal_moves(state)
        move = random.choice(moves)
        state = apply_move(state, move[0], move[1])


def mcts_search(state: GameState, n_iterations: int = MCTS_ITERATIONS):
    """Run MCTS and return the best (macro_idx, micro_idx) move."""
    root = MCTSNode(state)
    ai_player = state.current  # the player we are finding a move for

    for _ in range(n_iterations):
        # --- Selection ---
        node = root
        while node.is_fully_expanded() and node.children:
            terminal, _ = is_terminal(node.state)
            if terminal:
                break
            node = node.best_child()

        # --- Expansion ---
        terminal, winner = is_terminal(node.state)
        if not terminal and node.untried_moves:
            move = node.untried_moves.pop()
            new_state = apply_move(node.state, move[0], move[1])
            child = MCTSNode(new_state, move=move, parent=node)
            node.children.append(child)
            node = child

        # --- Rollout ---
        terminal, winner = is_terminal(node.state)
        if terminal:
            result_winner = winner
        else:
            result_winner = rollout(node.state)

        # --- Backpropagation ---
        # Score from perspective of ai_player
        if result_winner == ai_player:
            score = 1.0
        elif result_winner == 0:
            score = 0.0
        else:
            score = -1.0

        n = node
        while n is not None:
            n.visits += 1
            # For each node, wins is from the perspective of ai_player
            n.wins += score
            n = n.parent

    if not root.children:
        # Fallback: no search possible, pick random
        moves = get_legal_moves(state)
        return random.choice(moves) if moves else None

    best = root.best_move_child()
    return best.move
