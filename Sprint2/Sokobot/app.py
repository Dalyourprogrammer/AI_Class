"""
Sokobot — Flask web server.

Serves the frontend and provides an async job-based API for solving
Sokoban puzzles.  See api_spec.md for the full interface contract.

Encapsulation: this module only calls parse_level(), solve_level(), and
reads Solution attributes.  It never touches solver internals.
"""

import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory

from puzzles import PUZZLES, get_puzzle_names
from solver import parse_level, solve_level

app = Flask(__name__, static_folder="static")

SOLVE_TIMEOUT = 60  # seconds

# In-memory job store: job_id -> job dict
jobs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/levels", methods=["GET"])
def get_levels():
    """Return the built-in puzzle catalog."""
    levels = []
    for name in get_puzzle_names():
        text = PUZZLES[name]
        level = parse_level(text)
        levels.append({
            "name": name,
            "text": text,
            "boxes": len(level.initial_boxes),
        })
    return jsonify(levels)


@app.route("/api/solve", methods=["POST"])
def start_solve():
    """Validate a level synchronously, then solve in a background thread."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(status="error",
                       message="Request body must be JSON."), 400

    level_text = data.get("level", "").strip()
    if not level_text:
        return jsonify(status="error",
                       message="Missing 'level' field."), 400

    # Synchronous validation — fast, gives immediate feedback
    try:
        level = parse_level(level_text)
    except ValueError as e:
        return jsonify(status="error", message=str(e)), 400

    # Create job and launch solver thread
    job_id = uuid.uuid4().hex
    job: dict = {
        "status": "searching",
        "states_explored": 0,
        "pushes": None,
        "moves": None,
    }
    jobs[job_id] = job

    def run_solver():
        def on_progress(n):
            job["states_explored"] = n

        result_holder = [None]
        error_holder = [None]

        def do_solve():
            try:
                result_holder[0] = solve_level(
                    level, max_states=1_000_000,
                    progress_callback=on_progress,
                )
            except Exception as e:
                error_holder[0] = str(e)

        thread = threading.Thread(target=do_solve, daemon=True)
        thread.start()
        thread.join(timeout=SOLVE_TIMEOUT)

        if thread.is_alive():
            job["status"] = "error"
            job["message"] = "Solver timed out."
        elif error_holder[0]:
            job["status"] = "error"
            job["message"] = error_holder[0]
        elif result_holder[0] is None:
            job["status"] = "no_solution"
        else:
            result = result_holder[0]
            job["status"] = "solved"
            job["states_explored"] = result.states_explored
            job["pushes"] = len(result.pushes)
            job["moves"] = result.to_moves()

    threading.Thread(target=run_solver, daemon=True).start()

    return jsonify(status="ok", job_id=job_id)


@app.route("/api/solve/<job_id>", methods=["GET"])
def poll_solve(job_id):
    """Poll for the result of a solve job."""
    job = jobs.get(job_id)
    if job is None:
        return jsonify(status="error", message="Job not found."), 404
    return jsonify(job)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
