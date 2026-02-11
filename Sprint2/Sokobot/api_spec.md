# Sokobot Web API — Specification

## Overview

A Flask web server that lets users select a built-in Sokoban puzzle, submit it to
the A* solver, and receive the solution as a step-by-step sequence of moves.

The solver (`solver.py`) is a self-contained component.  The API layer's only job
is to accept puzzle text, hand it to the solver, and return the result.  It never
reaches into the solver's internals.

## Architecture

```
┌──────────────────┐         ┌──────────────────┐        ┌─────────────┐
│   Browser (JS)   │  HTTP   │   Flask (app.py) │  call  │ solver.py   │
│                  │ ──────> │                  │ ─────> │ puzzles.py  │
│  index.html      │ <────── │  /api/*          │ <───── │             │
│  style.css       │  JSON   │                  │ return │ (unchanged) │
│  script.js       │         │                  │        │             │
└──────────────────┘         └──────────────────┘        └─────────────┘
```

The solver exposes two functions the server uses:

| Function | Purpose |
|----------|---------|
| `parse_level(text) → Level` | Validate + parse; raises `ValueError` on bad input |
| `solve_level(level, ..., progress_callback) → Solution \| None` | Run A*; returns `None` if unsolvable |

And `Solution` exposes:
- `.pushes` — list of `PushAction` (length = number of pushes)
- `.states_explored` — int
- `.to_moves()` — flat list of direction strings for animation

The server also imports `puzzles.py` for the built-in puzzle catalog.

---

## Endpoints

### `GET /`

Serves `static/index.html`.

### `GET /api/levels`

Returns the list of built-in puzzles so the frontend can populate a dropdown.

**Response (200):**
```json
[
  {
    "name": "One Box",
    "text": "####\n#. #\n#$ #\n#@ #\n####",
    "boxes": 1
  },
  ...
]
```

### `POST /api/solve`

Submits a puzzle to be solved.  Validation happens synchronously (parse the
level text — does it have a player? matching box/goal counts?).  If valid,
the solver runs in a **background thread** and the endpoint returns a job ID
immediately.

**Request body:**
```json
{
  "level": "####\n#. #\n#$ #\n#@ #\n####"
}
```

**Response (200) — job started:**
```json
{
  "status": "ok",
  "job_id": "abc123"
}
```

**Response (400) — invalid level:**
```json
{
  "status": "error",
  "message": "Box count (2) != goal count (1)"
}
```

### `GET /api/solve/<job_id>`

Polls for the result of a solve job.

**Response — still searching:**
```json
{
  "status": "searching",
  "states_explored": 42000
}
```

**Response — solved:**
```json
{
  "status": "solved",
  "states_explored": 351,
  "pushes": 10,
  "moves": ["d", "d", "r", "U", "l", "L", ...]
}
```

Move encoding:
- **lowercase** (`u`, `d`, `l`, `r`) = player walks (no push)
- **UPPERCASE** (`U`, `D`, `L`, `R`) = player pushes a box in that direction

This encoding comes directly from `Solution.to_moves()`.  The frontend
replays the list one step at a time to animate the solution.

**Response — no solution:**
```json
{
  "status": "no_solution"
}
```

**Response — error:**
```json
{
  "status": "error",
  "message": "..."
}
```

---

## Encapsulation boundaries

- **`app.py`** never imports `State`, `PushAction`, `_heuristic`, or any
  private solver function.  It only calls `parse_level`, `solve_level`,
  and reads `Solution` attributes.
- **`solver.py`** has no knowledge of Flask, JSON, or HTTP.
- **`puzzles.py`** is a pure data module — a dict of name → level text.

---

## Implementation steps

1. Write `app.py` with all four endpoints
2. Write `static/index.html` — layout and structure
3. Write `static/style.css` — board styling
4. Write `static/script.js` — dropdown, solve button, polling, board rendering, solution playback
5. Manual smoke test: start server, solve a puzzle, watch playback
