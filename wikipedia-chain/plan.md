# Wikipedia Chain Finder — Build Plan

## Step 1: Create project structure and dependencies

- Create the `wikipedia-chain/` directory and subdirectories (`static/`).
- Create `requirements.txt` with `flask` and `requests`.
- Install dependencies with `pip install -r requirements.txt`.

### Tests before proceeding

- Verify the directory structure exists: `wikipedia-chain/`, `wikipedia-chain/static/`.
- Verify `pip install -r requirements.txt` completes without errors.
- Verify `python -c "import flask; import requests"` runs without import errors.

## Step 2: Implement the Wikimedia API client (`wiki_api.py`)

- Set a descriptive `User-Agent` header on all requests.
- Add type hints on all function signatures and docstrings on public functions.
- Include retry logic for transient failures (non-JSON responses from Wikipedia).
- Implement `validate_article(title: str) -> str | None`:
  - Call the Wikimedia query API with `&redirects=1`.
  - Return the canonical title if the article exists, or `None` if it does not (page ID `-1` or `missing` key present).
- Implement `get_outgoing_links(title: str) -> list[str]`:
  - Call the Wikimedia API with `prop=links`, `plnamespace=0`, `pllimit=max`.
  - Handle pagination via `plcontinue`. Loop until all pages are fetched.
  - Return a list of linked article titles.
- Implement `get_backlinks(title: str) -> list[str]`:
  - Call the Wikimedia API with `list=backlinks`, `blnamespace=0`, `bllimit=max`.
  - Handle pagination via `blcontinue`. Loop until all pages are fetched.
  - Return a list of article titles that link to the given title.

### Tests before proceeding

Write and run a test script (`test_wiki_api.py`) that verifies:

- `validate_article("Python (programming language)")` returns the exact title `"Python (programming language)"`.
- `validate_article("USA")` resolves the redirect and returns `"United States"`.
- `validate_article("Xyzzyxyzzy12345")` returns `None`.
- `get_outgoing_links("Cat")` returns a list containing `"Mammal"`. Verify all returned titles are in namespace 0 (no `Talk:`, `Wikipedia:`, `File:` prefixes).
- `get_backlinks("Cat")` returns a non-empty list of strings in namespace 0.
- Pagination: `get_outgoing_links("United States")` returns more than 500 results.

All tests must pass before proceeding.

## Step 3: Implement the search algorithm (`search.py`)

- Implement `find_chain(start: str, end: str, on_progress: Callable[[str], None] | None = None) -> list[str] | None`.
- Add type hints and docstrings.
- Handle the trivial case: if `start == end`, return `[start]` immediately.
- Data structures:
  - `forward_visited`: `dict[str, list[str]]` — title → path from start.
  - `backward_visited`: `dict[str, list[str]]` — title → path from end.
- Implement depth-limited DFS helper:
  - Takes an origin title, a max depth, a visited dict, and a direction (forward or backward).
  - Recursively expands nodes using `get_outgoing_links` (forward) or `get_backlinks` (backward).
  - Records each newly visited node and its path in the visited dict.
  - Skips nodes already present in the visited dict (visited at a shallower depth).
- Main loop (lockstep, depths 1 through 3):
  - At each depth, call `on_progress(f"Searching depth {depth}...")` if provided.
  - Run forward DFS to current depth limit.
  - Run backward DFS to current depth limit.
  - Compute intersection of `forward_visited` keys and `backward_visited` keys.
  - If intersection is non-empty:
    - For each meeting node, build the full chain: forward path + reversed backward path (excluding duplicate meeting node).
    - Select the shortest chain.
    - Return it.
- If no intersection after depth 3, return `None` (not found).

### Tests before proceeding

Write and run a test script (`test_search.py`) that verifies:

- **Trivial case**: `find_chain("Cat", "Cat")` returns `["Cat"]`.
- **Direct link**: `find_chain("Cat", "Mammal")` returns a chain of length 2: `["Cat", "Mammal"]`.
- **Short chain**: `find_chain("Cat", "Dog")` returns a chain starting with `"Cat"`, ending with `"Dog"`, length ≤ 7.
- **Chain validity**: For the returned chain, verify every consecutive pair is connected (article N+1 is in outgoing links of article N).
- **Progress callback**: Pass a callback to `find_chain` and verify it is called with progress strings.

All tests must pass before proceeding.

## Step 4: Implement the Flask app (`app.py`)

- Create the Flask app with no classes — use simple functions and a module-level `jobs` dictionary.
- Add type hints and docstrings.
- Implement `GET /` to serve `static/index.html`.
- Implement `POST /api/search`:
  - Parse JSON body for `start` and `end` fields. Return error if missing or empty.
  - Validate both articles using `validate_article()`. Return error if either is invalid.
  - Handle trivial case (start == end after redirect resolution): return `{"status": "found", "chain": [...]}` immediately.
  - Otherwise, generate a job ID (`uuid.uuid4().hex`), store the job in the `jobs` dict with status `"searching"`, start a background thread that runs `find_chain()`, and return `{"status": "ok", "job_id": "..."}`.
  - The background thread updates the job's `progress` field via the `on_progress` callback, and sets the job's final status/result when done.
  - Apply a 60-second timeout to the search thread. If it exceeds the timeout, mark the job as errored.
- Implement `GET /api/search/<job_id>`:
  - Look up the job ID in the `jobs` dict. Return error if not found.
  - Return the current job state: `status`, `progress` (if searching), `chain` (if found), or `message` (if not found / error).
- Implement `DELETE /api/cache`:
  - Call `clear_cache()` from `cache.py` and return `{"status": "ok", "message": "Cache cleared."}`.
- Construct URLs deterministically: `https://en.wikipedia.org/wiki/` + URL-encoded title.

### Tests before proceeding

Write and run a test script (`test_app.py`) using Flask's test client that verifies:

- **Job creation**: `POST /api/search` with `{"start": "Cat", "end": "Mammal"}` returns `{"status": "ok", "job_id": "..."}` with a non-empty job ID.
- **Polling — searching**: Immediately after POST, `GET /api/search/<job_id>` returns `status` of `"searching"` or `"found"` (depending on speed).
- **Polling — found**: Poll `GET /api/search/<job_id>` until status is no longer `"searching"`. Verify final status is `"found"` with a valid chain.
- **Trivial case**: `POST /api/search` with `{"start": "Cat", "end": "Cat"}` returns `{"status": "found", ...}` immediately (no job ID needed).
- **Redirect resolution**: `POST /api/search` with `{"start": "USA", "end": "USA"}` returns `{"status": "found"}` with chain title `"United States"`.
- **Invalid article**: `POST /api/search` with `{"start": "Xyzzyxyzzy12345", "end": "Cat"}` returns `{"status": "error"}`.
- **Missing fields**: `POST /api/search` with `{}` returns `{"status": "error"}`.
- **Invalid job ID**: `GET /api/search/nonexistent` returns `{"status": "error"}`.
- **`GET /`** returns status code 200.
- **`DELETE /api/cache`** returns `{"status": "ok"}`.

All tests must pass before proceeding.

## Step 5: Build the frontend

### `static/index.html`
- Page title/heading.
- A form with two text inputs ("Start article", "End article") and a submit button.
- A result area `<div>` below the form.
- Link `style.css` and `script.js`.

### `static/style.css`
- Centered layout, max-width container.
- Clean typography and spacing.
- Styled inputs and button.
- Loading state styling (e.g., dimmed inputs).
- Result chain styling (articles as links separated by arrows).
- Error/not-found message styling.

### `static/script.js`
- On submit:
  - Prevent default form submission.
  - Disable inputs and button; show "Searching..." in the result area.
  - Send `POST /api/search` with `Content-Type: application/json` and the two titles.
  - If the response contains an error, display it and re-enable inputs.
  - If the response contains `"found"` (trivial case), render the chain immediately.
  - If the response contains a `job_id`, begin polling `GET /api/search/<job_id>` every 1–2 seconds.
- While polling:
  - If status is `"searching"`, update the loading area with the `progress` message.
  - If status is `"found"`, stop polling, render the chain as clickable links with arrows.
  - If status is `"not_found"` or `"error"`, stop polling, display the message.
  - Re-enable inputs and button when polling stops.
- Use vanilla JavaScript. No frameworks or libraries.

### Tests before proceeding

Start the Flask app and test via `curl`:

- Verify `GET /` serves the HTML page with the form.
- Verify static CSS and JS assets load at `/static/style.css` and `/static/script.js`.
- Verify `POST /api/search` returns a job ID, and polling `GET /api/search/<job_id>` eventually returns a result.
- Verify the HTML references `/static/style.css` and `/static/script.js` correctly.

All tests must pass before proceeding.

## Step 6: Add SQLite link caching

### Implement `cache.py`

- Use Python's built-in `sqlite3` module (no new dependencies).
- Add type hints and docstrings.
- On import, open (or create) `cache.db` in the `wikipedia-chain/` directory.
- Create the `link_cache` table if it does not exist:
  ```sql
  CREATE TABLE IF NOT EXISTS link_cache (
      title TEXT NOT NULL,
      link_type TEXT NOT NULL,
      links TEXT NOT NULL,
      cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (title, link_type)
  );
  ```
- Implement `get_cached_links(title: str, link_type: str) -> list[str] | None`:
  - Query for a row matching `(title, link_type)`.
  - If found and `cached_at` is less than 1 day old, return the deserialized JSON list.
  - If found but expired, delete the row and return `None`.
  - If not found, return `None`.
- Implement `set_cached_links(title: str, link_type: str, links: list[str]) -> None`:
  - Insert or replace the row with the current timestamp and `json.dumps(links)`.
- Implement `clear_cache() -> None`:
  - Delete all rows from `link_cache`.

### Integrate cache into `wiki_api.py`

- Modify `get_outgoing_links(title)`:
  - Call `get_cached_links(title, "outgoing")` first. If it returns a result, return it.
  - Otherwise, fetch from the API as before, call `set_cached_links(title, "outgoing", links)`, then return the links.
- Modify `get_backlinks(title)` the same way using `link_type="backlinks"`.

### Tests before proceeding

Write and run a test script (`test_cache.py`) that verifies:

- **Cache miss**: `get_cached_links("Cat", "outgoing")` returns `None` on a fresh database.
- **Cache write and read**: Call `set_cached_links("Cat", "outgoing", ["Dog", "Mammal"])`, then `get_cached_links("Cat", "outgoing")` returns `["Dog", "Mammal"]`.
- **Separate link types**: Caching outgoing links for "Cat" does not affect backlinks for "Cat".
- **Cache expiration**: Insert a row with a `cached_at` timestamp older than 1 day, then verify `get_cached_links` returns `None`.
- **Cache clear**: Populate several entries, call `clear_cache()`, verify all return `None`.
- **Integration with wiki_api**: Call `get_outgoing_links("Cat")` twice. Verify a row exists in the database after the first call. Verify the second call returns the same result.
- **DELETE /api/cache endpoint**: Send `DELETE /api/cache` and verify the cache is cleared.
- **Search still works**: Run `find_chain("Cat", "Mammal")` and verify it returns a valid chain.

All tests must pass before proceeding.

## Step 7: End-to-end integration testing

Start the Flask app and run through the following full scenarios:

- **Happy path**: POST to start "Cat" → "Dog" search, poll until found. Verify chain is valid with clickable URLs.
- **Trivial case**: POST "Python (programming language)" → "Python (programming language)". Verify immediate result (no job ID).
- **Redirect handling**: POST "USA" → "UK". Verify canonical titles in response.
- **Non-existent article**: POST "Xyzzyxyzzy12345" → "Cat". Verify immediate error (no job created).
- **Empty inputs**: POST with empty fields. Verify error.
- **Progress reporting**: Poll a running job and verify `progress` field updates.
- **Not found**: If possible, find two articles unlikely to connect within 6 hops. Verify `not_found` status.
- **Multiple searches**: Start several searches in sequence. Verify each gets its own job ID and returns independently.
- **Cache behavior**: Run the same search twice. Verify the second run is faster (cache hits).
- **Cache clear**: Call `DELETE /api/cache`, then re-run a search and verify it still works.
