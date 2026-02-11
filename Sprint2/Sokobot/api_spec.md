# Sokobot Web API — Interface Specification

## 1. Problem

We have a working Sokoban solver (`solver.py`) that takes a level as text and
returns a sequence of moves.  We need a web interface so a user can:

1. Pick a pre-designed puzzle from a catalog
2. Submit it to the solver
3. Watch the solution play back move-by-move

## 2. Design Decisions

### 2a. Submission format

The solver's `parse_level()` already accepts a multi-line string in the standard
Sokoban format (`#` wall, `@` player, `$` box, `.` goal, `*` box-on-goal,
`+` player-on-goal).  We'll use this same string as the API's submission format
— the front-end sends `{"level": "<level_text>"}` as JSON.

**Why not send a grid array or coordinates?**  The text format is the universal
Sokoban interchange format.  Using it directly means zero translation between
what the front-end displays and what the solver accepts.  Encapsulation: the API
layer doesn't need to know about walls, boxes, or goals — it just passes a
string through.

### 2b. Solution representation

The solver returns a `Solution` object with a `.to_moves()` method that produces
a flat list of single-character direction strings:

- **lowercase** (`u`, `d`, `l`, `r`) = player walks without pushing
- **UPPERCASE** (`U`, `D`, `L`, `R`) = player pushes a box in that direction

The API returns this list directly.  The front-end replays it one step at a time.

**Why a flat move list instead of push-only?**  The front-end needs to animate
every player step, not just pushes.  A flat sequence of `[walk, walk, PUSH, walk,
PUSH, ...]` is trivial to replay: for each move, shift the player; if uppercase,
also shift the adjacent box.

### 2c. Synchronous vs. asynchronous solving

Harder puzzles (5 boxes) can take several seconds to solve.  A synchronous
`POST /api/solve` would block the HTTP connection, and the user would see no
feedback.

**Design: async job pattern.**

1. `POST /api/solve` — validates the level immediately, starts a background
   thread, returns a `job_id`
2. `GET /api/solve/<job_id>` — the front-end polls every 500ms to get progress
   (`states_explored`) or the final result

This keeps the UI responsive and lets us show a live state counter during search.

### 2d. Encapsulation boundary

The server (`app.py`) only touches these from the solver:

| Import | Type | Usage |
|--------|------|-------|
| `parse_level(text)` | function | Validate input; get `Level` object |
| `solve_level(level, ...)` | function | Run A*; get `Solution \| None` |
| `Solution.to_moves()` | method | Convert result to move list |
| `Solution.pushes` | attribute | Count of pushes (for display) |
| `Solution.states_explored` | attribute | Search stats (for display) |

The server **never** imports `State`, `PushAction`, `_heuristic`, or any private
function.  The solver **never** imports Flask.  `puzzles.py` is a pure data
module — just a dict of `name -> level_text`.

```
┌──────────────────┐         ┌──────────────────┐        ┌─────────────┐
│   Browser (JS)   │  HTTP   │   Flask (app.py) │  call  │ solver.py   │
│                  │ ──────> │                  │ ─────> │ puzzles.py  │
│  index.html      │ <────── │  /api/*          │ <───── │             │
│  style.css       │  JSON   │                  │ return │ (unchanged) │
│  script.js       │         │                  │        │             │
└──────────────────┘         └──────────────────┘        └─────────────┘
```

---

## 3. Endpoints

### `GET /`

Serves `static/index.html` (the single-page front-end).

### `GET /api/levels`

Returns the puzzle catalog so the front-end can populate a dropdown.

**Response 200:**
```json
[
  { "name": "One Box", "text": "####\n#. #\n#$ #\n#@ #\n####", "boxes": 1 },
  { "name": "Two Box Line", "text": "...", "boxes": 2 },
  ...
]
```

### `POST /api/solve`

Submit a level for solving.  Validation is synchronous (fast); solving is async.

**Request:**
```json
{ "level": "####\n#. #\n#$ #\n#@ #\n####" }
```

**Response 200 — job created:**
```json
{ "status": "ok", "job_id": "a1b2c3d4" }
```

**Response 400 — bad input:**
```json
{ "status": "error", "message": "Level has no player (@)" }
```

### `GET /api/solve/<job_id>`

Poll for result.

**Still searching:**
```json
{ "status": "searching", "states_explored": 42000 }
```

**Solved:**
```json
{
  "status": "solved",
  "states_explored": 351,
  "pushes": 10,
  "moves": ["d", "d", "r", "U", "l", "L", "u", "U", "r", "R"]
}
```

**No solution:**
```json
{ "status": "no_solution" }
```

**Error (timeout, crash):**
```json
{ "status": "error", "message": "Solver timed out." }
```

---

## 4. Implementation Plan

Build in this order, testing each step before moving on:

1. **`app.py` — `GET /api/levels`** — serve the puzzle list; test with curl
2. **`app.py` — `POST /api/solve`** — sync validation + async job launch; test with curl
3. **`app.py` — `GET /api/solve/<job_id>`** — poll loop; test full solve cycle with curl
4. **`static/index.html`** — page structure: dropdown, solve button, board div, playback
5. **`static/style.css`** — board grid styling, dark theme
6. **`static/script.js`** — wire it all together: load puzzles, render board, poll solve, playback
7. **Smoke test** — start server, solve each puzzle, verify playback
