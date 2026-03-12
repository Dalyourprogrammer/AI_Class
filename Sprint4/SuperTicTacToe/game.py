from dataclasses import dataclass


@dataclass(frozen=True)
class GameState:
    boards: tuple   # 9 tuples of 9 ints: 0=empty, 1=X, 2=O
    macro: tuple    # 9 ints: 0=active, 1=X won, 2=O won, -1=draw
    current: int    # 1=X, 2=O
    active: int     # -1=any, 0-8=forced board index


def new_game():
    empty_board = tuple(0 for _ in range(9))
    return GameState(
        boards=tuple(empty_board for _ in range(9)),
        macro=tuple(0 for _ in range(9)),
        current=1,
        active=-1,
    )


def check_line(a, b, c):
    return a != 0 and a == b == c


LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),             # diagonals
]


def check_winner(board):
    for a, b, c in LINES:
        if check_line(board[a], board[b], board[c]):
            return board[a]
    return 0


def board_status(board):
    """0=ongoing, 1=X won, 2=O won, -1=draw"""
    w = check_winner(board)
    if w:
        return w
    if all(v != 0 for v in board):
        return -1
    return 0


def apply_move(state: GameState, macro_idx: int, micro_idx: int) -> GameState:
    # Place mark
    new_boards = list(list(b) for b in state.boards)
    new_boards[macro_idx][micro_idx] = state.current
    new_boards = tuple(tuple(b) for b in new_boards)

    # Update macro status for the affected board
    new_macro = list(state.macro)
    status = board_status(new_boards[macro_idx])
    if status != 0:
        new_macro[macro_idx] = status
    new_macro = tuple(new_macro)

    # Next player
    next_player = 2 if state.current == 1 else 1

    # Determine next active board
    if new_macro[micro_idx] != 0:
        # Directed to a completed board — free choice
        next_active = -1
    else:
        next_active = micro_idx

    return GameState(
        boards=new_boards,
        macro=new_macro,
        current=next_player,
        active=next_active,
    )


def get_legal_moves(state: GameState):
    moves = []
    if state.active == -1:
        for macro_idx in range(9):
            if state.macro[macro_idx] == 0:
                for micro_idx in range(9):
                    if state.boards[macro_idx][micro_idx] == 0:
                        moves.append((macro_idx, micro_idx))
    else:
        macro_idx = state.active
        for micro_idx in range(9):
            if state.boards[macro_idx][micro_idx] == 0:
                moves.append((macro_idx, micro_idx))
    return moves


def is_terminal(state: GameState):
    """Returns (is_terminal, winner): winner 0=draw, 1=X, 2=O"""
    w = check_winner(state.macro)
    if w:
        return True, w
    # Draw: no legal moves or all macro cells resolved
    if not get_legal_moves(state):
        return True, 0
    # Check if macro draw is forced (all cells won or drawn, no winner)
    if all(v != 0 for v in state.macro):
        return True, 0
    return False, 0


def state_to_dict(state: GameState):
    terminal, winner = is_terminal(state)
    legal = get_legal_moves(state)
    return {
        "boards": [list(b) for b in state.boards],
        "macro": list(state.macro),
        "current": state.current,
        "active": state.active,
        "legal_moves": [list(m) for m in legal],
        "terminal": terminal,
        "winner": winner,
    }
