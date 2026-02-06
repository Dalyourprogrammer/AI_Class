import threading
import uuid
from urllib.parse import quote

from flask import Flask, jsonify, request, send_from_directory

from cache import clear_cache
from search import find_chain
from wiki_api import validate_article

app = Flask(__name__, static_folder="static")

SEARCH_TIMEOUT = 60
WIKI_BASE = "https://en.wikipedia.org/wiki/"

# Module-level job store: job_id -> job state dict
jobs: dict[str, dict] = {}


@app.route("/")
def index() -> str:
    """Serve the frontend."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/search", methods=["POST"])
def api_search() -> tuple:
    """Start a search job. Validates input synchronously, then runs
    the search in a background thread. Returns a job_id for polling."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify(status="error", message="Request body must be JSON."), 400

    start = data.get("start", "").strip()
    end = data.get("end", "").strip()

    if not start or not end:
        return jsonify(status="error",
                       message="Both 'start' and 'end' fields are required."), 400

    try:
        canonical_start = validate_article(start)
        if canonical_start is None:
            return jsonify(status="error",
                           message=f"Article '{start}' not found on Wikipedia."), 400

        canonical_end = validate_article(end)
        if canonical_end is None:
            return jsonify(status="error",
                           message=f"Article '{end}' not found on Wikipedia."), 400
    except Exception as e:
        return jsonify(status="error", message=f"Validation error: {e}"), 500

    # Trivial case — return immediately, no job needed
    if canonical_start == canonical_end:
        return jsonify(status="found", chain=[_article(canonical_start)])

    # Create job and run in background
    job_id = uuid.uuid4().hex
    job: dict = {
        "status": "searching",
        "progress": "Starting search...",
        "start": canonical_start,
        "end": canonical_end,
        "result": None,
    }
    jobs[job_id] = job

    thread = threading.Thread(target=_run_search, args=(job_id,), daemon=True)
    thread.start()

    return jsonify(status="ok", job_id=job_id)


@app.route("/api/search/<job_id>", methods=["GET"])
def api_poll(job_id: str) -> tuple:
    """Poll the status of a search job."""
    job = jobs.get(job_id)
    if job is None:
        return jsonify(status="error", message="Job not found."), 404

    if job["status"] == "searching":
        return jsonify(status="searching", progress=job["progress"])

    if job["status"] == "found":
        chain = [_article(title) for title in job["result"]]
        return jsonify(status="found", chain=chain)

    if job["status"] == "not_found":
        return jsonify(status="not_found",
                       message="No chain found within 7 articles.")

    # error
    return jsonify(status="error", message=job.get("message", "Unknown error."))


@app.route("/api/cache", methods=["DELETE"])
def api_clear_cache() -> tuple:
    """Clear the link cache."""
    clear_cache()
    return jsonify(status="ok", message="Cache cleared.")


def _run_search(job_id: str) -> None:
    """Run the search in a background thread with a timeout."""
    job = jobs[job_id]

    def on_progress(msg: str) -> None:
        job["progress"] = msg

    result = [None]
    error = [None]

    def do_search() -> None:
        try:
            result[0] = find_chain(job["start"], job["end"], on_progress=on_progress)
        except Exception as e:
            error[0] = str(e)

    thread = threading.Thread(target=do_search, daemon=True)
    thread.start()
    thread.join(timeout=SEARCH_TIMEOUT)

    if thread.is_alive():
        job["status"] = "error"
        job["message"] = "Search timed out. Try articles that are more closely related."
    elif error[0]:
        job["status"] = "error"
        job["message"] = f"Search error: {error[0]}"
    elif result[0] is None:
        job["status"] = "not_found"
    else:
        job["status"] = "found"
        job["result"] = result[0]


def _article(title: str) -> dict:
    """Build an article dict with title and Wikipedia URL."""
    return {"title": title, "url": WIKI_BASE + quote(title.replace(" ", "_"))}


if __name__ == "__main__":
    app.run(debug=True)
