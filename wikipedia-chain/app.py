import signal
import threading
from urllib.parse import quote

from flask import Flask, jsonify, request, send_from_directory

from search import find_chain
from wiki_api import validate_article
from cache import clear_cache

app = Flask(__name__, static_folder="static")

SEARCH_TIMEOUT = 60
WIKI_BASE = "https://en.wikipedia.org/wiki/"


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/find-chain", methods=["POST"])
def api_find_chain():
    data = request.get_json(silent=True)
    if not data:
        return jsonify(status="error", message="Request body must be JSON."), 400

    start = data.get("start", "").strip()
    end = data.get("end", "").strip()

    if not start or not end:
        return jsonify(status="error",
                       message="Both 'start' and 'end' fields are required."), 400

    try:
        # Validate articles
        canonical_start = validate_article(start)
        if canonical_start is None:
            return jsonify(status="error",
                           message=f"Article '{start}' not found on Wikipedia."), 400

        canonical_end = validate_article(end)
        if canonical_end is None:
            return jsonify(status="error",
                           message=f"Article '{end}' not found on Wikipedia."), 400

        # Trivial case
        if canonical_start == canonical_end:
            return jsonify(status="found", chain=[_article(canonical_start)])

        # Run search with timeout
        result = [None]
        error = [None]

        def run_search():
            try:
                result[0] = find_chain(canonical_start, canonical_end)
            except Exception as e:
                error[0] = str(e)

        thread = threading.Thread(target=run_search)
        thread.start()
        thread.join(timeout=SEARCH_TIMEOUT)

        if thread.is_alive():
            return jsonify(status="error",
                           message="Search timed out. Try articles that are more closely related.")

        if error[0]:
            return jsonify(status="error", message=f"Search error: {error[0]}")

        if result[0] is None:
            return jsonify(status="not_found",
                           message="No chain found within 7 articles.")

        chain = [_article(title) for title in result[0]]
        return jsonify(status="found", chain=chain)

    except Exception as e:
        return jsonify(status="error", message=f"An error occurred: {e}"), 500


@app.route("/api/cache", methods=["DELETE"])
def api_clear_cache():
    clear_cache()
    return jsonify(status="ok", message="Cache cleared.")


def _article(title):
    return {"title": title, "url": WIKI_BASE + quote(title.replace(" ", "_"))}


if __name__ == "__main__":
    app.run(debug=True)
