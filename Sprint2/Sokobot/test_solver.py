"""Tests for the Sokobot A* solver."""

import time
import unittest

from solver import (
    Level,
    State,
    parse_level,
    solve,
    solve_level,
    render_state,
    _has_freeze_deadlock,
    _normalize_player,
)
from puzzles import PUZZLES, get_puzzle_names


class TestParsing(unittest.TestCase):
    """Test level parsing."""

    def test_simple_level(self):
        level = parse_level("""\
######
#.   #
# $  #
#  @ #
######""")
        self.assertEqual(level.initial_player, (3, 3))
        self.assertEqual(level.initial_boxes, frozenset({(2, 2)}))
        self.assertEqual(level.goals, frozenset({(1, 1)}))
        self.assertEqual(level.height, 5)
        self.assertEqual(level.width, 6)

    def test_box_on_goal(self):
        level = parse_level("""\
####
#.*#
# @#
####""")
        self.assertIn((1, 1), level.goals)
        self.assertIn((1, 2), level.boxes if hasattr(level, 'boxes') else level.initial_boxes)

    def test_player_on_goal(self):
        level = parse_level("""\
#####
#  $#
# + #
#####""")
        self.assertEqual(level.initial_player, (2, 2))
        self.assertIn((2, 2), level.goals)

    def test_no_player_raises(self):
        with self.assertRaises(ValueError):
            parse_level("""\
####
#.$#
####""")

    def test_box_goal_mismatch_raises(self):
        with self.assertRaises(ValueError):
            parse_level("""\
#####
#.$.#
# @ #
#####""")

    def test_all_puzzles_parse(self):
        """Every built-in puzzle should parse without error."""
        for name in get_puzzle_names():
            with self.subTest(puzzle=name):
                level = parse_level(PUZZLES[name])
                self.assertGreater(len(level.goals), 0)
                self.assertEqual(len(level.initial_boxes), len(level.goals))


class TestDeadlocks(unittest.TestCase):
    """Test deadlock detection."""

    def test_corner_dead_cell(self):
        level = parse_level("""\
#####
#  .#
# $ #
#@  #
#####""")
        # Corners not reachable from goal should be dead
        self.assertIn((3, 1), level.dead_cells)  # bottom-left
        self.assertIn((1, 1), level.dead_cells)  # top-left
        self.assertIn((3, 3), level.dead_cells)  # bottom-right
        # Goal cell should NOT be dead
        self.assertNotIn((1, 3), level.dead_cells)

    def test_freeze_deadlock_two_boxes_wall(self):
        level = parse_level("""\
######
#. . #
# $$ #
#  @ #
######""")
        # Two boxes in top-right corner area — both frozen:
        # box at (1,3) against top wall and blocked by (1,4)
        # box at (1,4) against top wall and right wall
        boxes = frozenset({(1, 3), (1, 4)})
        self.assertTrue(_has_freeze_deadlock(boxes, level))

    def test_no_freeze_deadlock_on_goals(self):
        level = parse_level("""\
######
#    #
#  **#
#    #
#  @ #
######""")
        # Two boxes on goals against wall — frozen but ON goals = OK
        boxes = frozenset({(2, 3), (2, 4)})
        # Need goals at those positions
        self.assertFalse(_has_freeze_deadlock(boxes, level))


class TestNormalization(unittest.TestCase):
    """Test player position normalization."""

    def test_same_reachable_area(self):
        level = parse_level("""\
######
#    #
# $. #
# @  #
######""")
        boxes = frozenset({(2, 2)})
        # Player at (1,1) and (1,3) are in different reachable regions
        # (box divides the space)... actually for this level they might
        # be connected around the box.
        # Let's just check normalization produces a consistent result
        n1 = _normalize_player((1, 1), boxes, level)
        n2 = _normalize_player((1, 3), boxes, level)
        # Both are in the same connected region (can go around the box)
        self.assertEqual(n1, n2)


class TestSolving(unittest.TestCase):
    """Test the A* solver on various puzzles."""

    def test_trivial_one_push(self):
        result = solve("""\
####
#. #
#$ #
#@ #
####""")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pushes), 1)

    def test_simple_push(self):
        result = solve("""\
######
#.   #
# $  #
#  @ #
######""")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pushes), 2)

    def test_already_solved(self):
        result = solve("""\
####
#* #
#@ #
####""")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pushes), 0)

    def test_unsolvable_corner(self):
        """Box in corner with no goal there — unsolvable."""
        result = solve("""\
####
#$ #
# .#
# @#
####""")
        self.assertIsNone(result)

    def test_moves_output(self):
        result = solve("""\
####
#. #
#$ #
#@ #
####""")
        self.assertIsNotNone(result)
        moves = result.to_moves()
        self.assertIsInstance(moves, list)
        self.assertGreater(len(moves), 0)
        # Push directions are uppercase, walks are lowercase
        uppercase = [m for m in moves if m.isupper()]
        self.assertEqual(len(uppercase), 1)  # exactly one push

    def test_builtin_puzzles(self):
        """All built-in puzzles should be solvable within the state limit."""
        for name in get_puzzle_names():
            with self.subTest(puzzle=name):
                t0 = time.time()
                result = solve(PUZZLES[name])
                dt = time.time() - t0
                self.assertIsNotNone(
                    result,
                    f"Puzzle '{name}' was not solved"
                )
                print(f"  {name}: {len(result.pushes)} pushes, "
                      f"{result.states_explored} states, {dt:.2f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
