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
- Implement `validate_article(title)`:
  - Call the Wikimedia query API with `&redirects=1`.
  - Return the canonical title if the article exists, or raise/return an error if it does not (page ID `-1` or `missing` key present).
- Implement `get_outgoing_links(title)`:
  - Call the Wikimedia API with `prop=links`, `plnamespace=0`, `pllimit=max`.
  - Handle pagination via `plcontinue`. Loop until all pages are fetched.
  - Return a list of linked article titles.
- Implement `get_backlinks(title)`:
  - Call the Wikimedia API with `list=backlinks`, `blnamespace=0`, `bllimit=max`.
  - Handle pagination via `blcontinue`. Loop until all pages are fetched.
  - Return a list of article titles that link to the given title.

### Tests before proceeding

Write and run a test script (`test_wiki_api.py`) that verifies:

- `validate_article("Python (programming language)")` returns the exact title `"Python (programming language)"`.
- `validate_article("USA")` resolves the redirect and returns `"United States"`.
- `validate_article("Xyzzyxyzzy12345")` returns an error or `None` indicating the article does not exist.
- `get_outgoing_links("Cat")` returns a list containing at least known links (e.g., `"Mammal"` should be in the list). Verify the return type is a list of strings. Verify all returned titles are in namespace 0 (no `Talk:`, `Wikipedia:`, `File:` prefixes).
- `get_backlinks("Cat")` returns a list of strings. Verify it is non-empty. Verify all returned titles are in namespace 0.
- Pagination: `get_outgoing_links("United States")` returns more than 500 results (confirming pagination works, since the API returns max 500 per page).

All tests must pass before proceeding.

## Step 3: Implement the search algorithm (`search.py`)

- Implement `find_chain(start, end)` using bidirectional iterative deepening search.
- Handle the trivial case: if `start == end`, return a chain of one article immediately.
- Data structures:
  - `forward_visited`: `dict[str, list[str]]` — title → path from start.
  - `backward_visited`: `dict[str, list[str]]` — title → path from end.
- Implement depth-limited DFS helper:
  - Takes an origin title, a max depth, a visited dict, and a direction (forward or backward).
  - Recursively expands nodes using `get_outgoing_links` (forward) or `get_backlinks` (backward).
  - Records each newly visited node and its path in the visited dict.
  - Skips nodes already present in the visited dict (visited at a shallower depth).
- Main loop (lockstep, depths 1 through 3):
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
- **Direct link**: `find_chain("Cat", "Mammal")` returns a chain of length 2: `["Cat", "Mammal"]`. (Verify "Mammal" is in Cat's outgoing links first.)
- **Short chain**: `find_chain("Cat", "Dog")` returns a chain. Verify the chain starts with `"Cat"` and ends with `"Dog"`. Verify the chain length is ≤ 7. Verify each consecutive pair in the chain is connected (the first links to the second) by calling `get_outgoing_links` on each article and checking the next article is in the list.
- **Chain validity**: For any returned chain, verify every consecutive link is valid (article N+1 appears in the outgoing links of article N).
- **No result**: Attempt a search that is unlikely to complete within depth 3 (if such a pair can be identified), and verify the function returns `None`.

All tests must pass before proceeding.

## Step 4: Implement the Flask app (`app.py`)

- Create the Flask app.
- Implement `GET /` to serve `static/index.html`.
- Implement `POST /api/find-chain`:
  - Parse JSON body for `start` and `end` fields.
  - Validate both articles using `validate_article()`. If either is invalid, return an error response.
  - Handle trivial case (start == end after redirect resolution).
  - Call `find_chain(start, end)` with a 60-second timeout (e.g., using `signal.alarm` or a threading timer).
  - On success, build the response with status `"found"` and the chain (each entry has `title` and `url`).
  - On not found, return status `"not_found"` with a message.
  - On timeout or exception, return status `"error"` with a message.
- Construct URLs deterministically: `https://en.wikipedia.org/wiki/` + URL-encoded title.

### Tests before proceeding

Write and run a test script (`test_app.py`) using Flask's test client that verifies:

- **Successful search**: `POST /api/find-chain` with `{"start": "Cat", "end": "Mammal"}` returns status code 200, JSON with `"status": "found"`, and a `chain` array where each entry has `title` and `url` keys. Verify the first entry's title is `"Cat"` and the last is `"Mammal"`. Verify URLs match the pattern `https://en.wikipedia.org/wiki/{encoded_title}`.
- **Trivial case**: `POST /api/find-chain` with `{"start": "Cat", "end": "Cat"}` returns `"status": "found"` with a chain of one article.
- **Redirect resolution**: `POST /api/find-chain` with `{"start": "USA", "end": "USA"}` returns `"status": "found"` with chain `[{"title": "United States", ...}]`.
- **Invalid article**: `POST /api/find-chain` with `{"start": "Xyzzyxyzzy12345", "end": "Cat"}` returns `"status": "error"` with a message indicating the article was not found.
- **Missing fields**: `POST /api/find-chain` with `{}` or `{"start": "Cat"}` returns `"status": "error"`.
- **`GET /`** returns status code 200 (requires `index.html` to exist; create a placeholder if the frontend isn't built yet).

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
- Attach a submit handler to the form.
- On submit:
  - Prevent default form submission.
  - Read the two input values.
  - Disable inputs and button; show a loading indicator in the result area.
  - Send `POST /api/find-chain` with `Content-Type: application/json` and the two titles.
  - Set a fetch timeout matching the server timeout (e.g., 90 seconds via `AbortController`).
  - On response, parse JSON and handle:
    - `"found"`: render the chain as clickable links with arrows between them.
    - `"not_found"`: display the message.
    - `"error"`: display the error message.
  - Re-enable inputs and button.

### Tests before proceeding

Start the Flask app and test in a browser (or via `curl` to simulate frontend behavior):

- Verify `GET /` serves the HTML page with the form visible.
- Verify the CSS loads and the page is styled (centered layout, readable fonts).
- Verify submitting the form with valid inputs shows a loading indicator, then displays the chain as clickable links with arrows.
- Verify submitting with a non-existent article displays the error message.
- Verify submitting with identical start and end displays a single-article chain.
- Verify inputs and button are disabled during the search and re-enabled after.
- Verify all links in the result open the correct Wikipedia page in a new tab.

All tests must pass before proceeding.

## Step 6: Add SQLite link caching

### Implement `cache.py`

- Use Python's built-in `sqlite3` module (no new dependencies).
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
- Implement `get_cached_links(title, link_type)`:
  - Query for a row matching `(title, link_type)`.
  - If found and `cached_at` is less than 1 day old, return the deserialized JSON list.
  - If found but expired, delete the row and return `None`.
  - If not found, return `None`.
- Implement `set_cached_links(title, link_type, links)`:
  - Insert or replace the row with the current timestamp and `json.dumps(links)`.
- Implement `clear_cache()`:
  - Delete all rows from `link_cache`.

### Integrate cache into `wiki_api.py`

- Modify `get_outgoing_links(title)`:
  - Call `get_cached_links(title, "outgoing")` first. If it returns a result, return it.
  - Otherwise, fetch from the API as before, call `set_cached_links(title, "outgoing", links)`, then return the links.
- Modify `get_backlinks(title)` the same way using `link_type="backlinks"`.

### Add `DELETE /api/cache` endpoint to `app.py`

- Import `clear_cache` from `cache.py`.
- Add a route `DELETE /api/cache` that calls `clear_cache()` and returns `{"status": "ok", "message": "Cache cleared."}`.

### Tests before proceeding

Write and run a test script (`test_cache.py`) that verifies:

- **Cache miss**: `get_cached_links("Cat", "outgoing")` returns `None` on a fresh database.
- **Cache write and read**: Call `set_cached_links("Cat", "outgoing", ["Dog", "Mammal"])`, then `get_cached_links("Cat", "outgoing")` returns `["Dog", "Mammal"]`.
- **Separate link types**: Caching outgoing links for "Cat" does not affect backlinks for "Cat". Both can be stored and retrieved independently.
- **Cache expiration**: Insert a row with a `cached_at` timestamp older than 1 day, then verify `get_cached_links` returns `None` for it.
- **Cache clear**: Populate several entries, call `clear_cache()`, verify all return `None`.
- **Integration with wiki_api**: Call `get_outgoing_links("Cat")` twice. Verify the second call returns the same result. Verify a row exists in the database for `("Cat", "outgoing")`.
- **DELETE /api/cache endpoint**: Using Flask's test client, send `DELETE /api/cache` and verify it returns `{"status": "ok", "message": "Cache cleared."}`. Verify the cache is actually empty afterward.
- **Search still works**: Run `find_chain("Cat", "Mammal")` and verify it returns a valid chain (confirming the cache integration doesn't break the search).

All tests must pass before proceeding.

## Step 7: End-to-end integration testing

Start the Flask app and run through the following full scenarios in the browser:

- **Happy path**: Search "Cat" → "Dog". Verify a chain is displayed with clickable links. Click each link to confirm it opens the correct Wikipedia article.
- **Trivial case**: Search "Python (programming language)" → "Python (programming language)". Verify a single-article chain is shown.
- **Redirect handling**: Search "USA" → "UK". Verify the chain uses canonical titles ("United States", "United Kingdom").
- **Non-existent article**: Search "Xyzzyxyzzy12345" → "Cat". Verify an error message is displayed immediately (no long wait).
- **Empty inputs**: Submit with one or both inputs empty. Verify an error is shown.
- **Not found**: If possible, find two articles unlikely to connect within 6 hops and verify the "not found" message appears.
- **Timeout behavior**: Verify the app does not hang indefinitely on difficult searches.
- **Multiple searches**: Run several searches in a row without reloading the page. Verify each search clears the previous result and displays the new one correctly.
