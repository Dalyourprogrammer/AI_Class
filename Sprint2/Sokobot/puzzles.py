"""
Built-in Sokoban puzzle collection.

Small puzzles ranging from trivial to moderate.
All puzzles are ≤8x8 with ≤5 boxes.

Standard format:
  # = wall, ' ' = floor, . = goal, $ = box, @ = player,
  * = box on goal, + = player on goal
"""

PUZZLES: dict[str, str] = {}

# ------------------------------------------------------------------
# 1-box puzzles  (trivial)
# ------------------------------------------------------------------

PUZZLES["One Box"] = """\
####
#. #
#$ #
#@ #
####"""

PUZZLES["One Box Wide"] = """\
######
#.   #
# $  #
#  @ #
######"""

# ------------------------------------------------------------------
# 2-box puzzles
# ------------------------------------------------------------------

PUZZLES["Two Box Line"] = """\
######
#    #
# @  #
# $$ #
# .. #
######"""

PUZZLES["Two Box Across"] = """\
######
# .  #
#  $ #
# $  #
#  . #
# @  #
######"""

# ------------------------------------------------------------------
# 3-box puzzles
# ------------------------------------------------------------------

PUZZLES["Three Down"] = """\
#######
#     #
# $$$ #
#     #
# ... #
#  @  #
#######"""

PUZZLES["Three Box L"] = """\
######
#    #
# @$ #
# $  #
# $ .#
#  ..#
######"""

# ------------------------------------------------------------------
# 4-box puzzles
# ------------------------------------------------------------------

PUZZLES["Four Down"] = """\
########
#      #
# $$$$ #
#      #
# .... #
#  @   #
########"""

PUZZLES["Four Spread"] = """\
########
# .... #
#      #
# $  $ #
#      #
# $  $ #
#  @   #
########"""

# ------------------------------------------------------------------
# 5-box puzzles  (harder)
# ------------------------------------------------------------------

PUZZLES["Five in a Row"] = """\
#########
#       #
# $$$$$ #
#       #
# ..... #
#   @   #
#########"""

PUZZLES["Five Scatter"] = """\
########
# .  . #
#  $$  #
# $  $ #
#  $   #
# .  .@#
#  .   #
########"""


def get_puzzle_names() -> list[str]:
    """Return all puzzle names in order."""
    return list(PUZZLES.keys())


def get_puzzle(name: str) -> str:
    """Return the level text for a named puzzle."""
    return PUZZLES[name]
