# Wikipedia Chain Finder — Project Spec

## Overview

A web app that finds the shortest path of links between two Wikipedia articles using bidirectional search. Flask backend with vanilla JS frontend.

## Core Requirements

- User enters start/end article titles, app finds the shortest link path connecting them.
- Maximum search depth: 7 articles (6 hops), corresponding to max depth 3 per side.
- Uses Wikipedia MediaWiki API (no local database for article data).
- Only mainspace articles (namespace 0) — no `File:`, `Wikipedia:`, `Help:`, etc.
- Bidirectional iterative deepening search algorithm.

## Project Structure

```
wikipedia-chain/
├── app.py              # Flask app, API endpoints, serves static files
├── search.py           # Bidirectional IDS algorithm
├── wiki_api.py         # Wikimedia API client (get links, backlinks, validate)
├── cache.py            # SQLite link cache
├── cache.db            # SQLite database (auto-created, not committed to git)
├── requirements.txt    # flask, requests
└── static/
    ├── index.html
    ├── style.css
    └── script.js
```

## Coding Standards

- Keep dependencies minimal (`flask`, `requests` only).
- No classes where simple functions suffice.
- Type hints on all function signatures.
- Docstrings on public functions.
- Handle Wikipedia API pagination (continuation tokens).
- Include reasonable error handling for API failures.
- Set a polite `User-Agent` header for Wikipedia requests.

## Backend (Python Flask)

### API Endpoints

**`POST /api/search`** — Start a search job.

Request body:
```json
{
  "start": "Cat",
  "end": "Science"
}
```

Response (job created):
```json
{
  "status": "ok",
  "job_id": "abc123"
}
```

Error response (invalid input):
```json
{
  "status": "error",
  "message": "Article 'Xyzzy' not found on Wikipedia."
}
```

Input validation happens synchronously before creating the job:
1. Both `start` and `end` fields must be non-empty.
2. Validate that both articles exist using the Wikimedia API.
3. Resolve redirects using `&redirects=1` and return canonical titles.
4. If start == end after redirect resolution, return the result immediately without creating a background job.

**`GET /api/search/<job_id>`** — Poll job status.

While searching:
```json
{
  "status": "searching",
  "progress": "Searching depth 2..."
}
```

On success:
```json
{
  "status": "found",
  "chain": [
    {"title": "Cat", "url": "https://en.wikipedia.org/wiki/Cat"},
    {"title": "Mammal", "url": "https://en.wikipedia.org/wiki/Mammal"},
    {"title": "Science", "url": "https://en.wikipedia.org/wiki/Science"}
  ]
}
```

Not found (search exhausted depth limit):
```json
{
  "status": "not_found",
  "message": "No chain found within 7 articles."
}
```

Error (search failed):
```json
{
  "status": "error",
  "message": "Search error: ..."
}
```

Invalid job ID:
```json
{
  "status": "error",
  "message": "Job not found."
}
```

URLs are constructed deterministically: `https://en.wikipedia.org/wiki/` + URL-encoded title.

**`DELETE /api/cache`** — Clear link cache.

Response:
```json
{
  "status": "ok",
  "message": "Cache cleared."
}
```

### Route for Frontend

Flask serves `static/index.html` at the root route (`GET /`).

### Job Management

- Jobs are stored in a module-level dictionary: `dict[str, dict]` mapping job ID to job state.
- Job IDs are generated using `uuid.uuid4().hex` (or similar).
- Each job runs in a background thread.
- Job state includes: `status`, `progress`, `result` (chain or error), and `start`/`end` titles.
- The search function should accept a callback or update a shared state object so that progress (current depth) can be reported to the polling endpoint.
- No automatic cleanup of old jobs is required for the first version. Jobs persist in memory until the server restarts.

### Server-Side Timeout

Set a timeout of 60 seconds per job. If the search has not completed, mark the job as errored with a timeout message.

## Wikimedia API Client (`wiki_api.py`)

All requests must include a descriptive `User-Agent` header as required by Wikimedia policy. Include retry logic for transient failures (non-JSON responses).

### Validate Article

```
GET https://en.wikipedia.org/w/api.php?action=query&titles={title}&redirects=1&format=json
```

An article does not exist if the returned page ID is `-1` or the `missing` key is present. If the article is a redirect, use the resolved title.

### Get Outgoing Links (Forward Search)

```
GET https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=links&plnamespace=0&pllimit=max&format=json
```

Handle pagination via the `plcontinue` parameter. Fetch **all** links by following continuation until exhausted.

### Get Backlinks (Backward Search)

```
GET https://en.wikipedia.org/w/api.php?action=query&list=backlinks&bltitle={title}&blnamespace=0&bllimit=max&format=json
```

Handle pagination via the `blcontinue` parameter. Fetch **all** backlinks by following continuation until exhausted.

### Rate Limiting

No artificial delays are needed. The single-threaded sequential nature of the search provides natural throttling. Use `pllimit=max` and `bllimit=max` to minimize the total number of API requests.

## Search Algorithm (`search.py`)

### Bidirectional Iterative Deepening Search

Two iterative deepening depth-limited searches run in lockstep: one forward from the start article (following outgoing links) and one backward from the end article (following backlinks).

### Depth Limits

- Each side searches to a maximum depth of **3** (3 hops).
- Maximum chain length: **7 articles** (6 hops).
- Iterative deepening increments per side: 1, 2, 3.

### Execution Order (Lockstep)

```
Depth 1: Forward DFS to depth 1, Backward DFS to depth 1 → check intersection
Depth 2: Forward DFS to depth 2, Backward DFS to depth 2 → check intersection
Depth 3: Forward DFS to depth 3, Backward DFS to depth 3 → check intersection
```

If no intersection is found after depth 3 on both sides, return not found.

### Progress Reporting

The `find_chain` function accepts a progress callback. At the start of each depth iteration, it calls the callback with a progress string (e.g., `"Searching depth 2..."`). This allows the app layer to update the job state for polling.

### Data Structures

Each side maintains a visited dictionary: `dict[str, list[str]]` mapping each visited article title to the path from the origin to that node.

- Forward visited: title → path from start to title
- Backward visited: title → path from end to title

### Intersection Check

After **both** sides complete a depth level, compute the intersection of the two visited sets' keys. If the intersection is non-empty:

1. For each meeting node, compute the total chain: forward path to meeting node + reversed backward path from meeting node (excluding the meeting node itself from the backward path to avoid duplication).
2. Select the meeting node that produces the **shortest total chain**.
3. Return that chain.

### Skipping Visited Nodes

Within each side's search, across depth iterations, **skip nodes that were already visited at a shallower depth**. This avoids redundant Wikimedia API calls. Since iterative deepening re-runs shallower depths, this optimization is significant.

### Link Caching (SQLite)

Cache the results of `get_outgoing_links()` and `get_backlinks()` in a local SQLite database (`cache.db`) so that repeated lookups for the same article skip the Wikimedia API entirely.

#### Database Schema

A single table with a denormalized design (one row per article per direction):

```sql
CREATE TABLE IF NOT EXISTS link_cache (
    title TEXT NOT NULL,
    link_type TEXT NOT NULL,  -- 'outgoing' or 'backlinks'
    links TEXT NOT NULL,      -- JSON array of article titles
    cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (title, link_type)
);
```

#### Cache Behavior

- **On read**: Before making an API call, check the cache for a matching `(title, link_type)` row. If found and `cached_at` is less than **1 day** old, deserialize the JSON `links` column and return it. If found but expired, delete the row and treat it as a miss.
- **On write**: After fetching links from the API, insert or replace the row with the current timestamp and the links serialized as a JSON array.
- **Cache location**: `wikipedia-chain/cache.db`, created automatically on first use.
- **Database creation**: The table is created via `CREATE TABLE IF NOT EXISTS` when the cache module initializes, so no separate setup step is needed.

#### Cache Clearing

- **API endpoint**: `DELETE /api/cache` — deletes all rows from `link_cache` and returns `{"status": "ok", "message": "Cache cleared."}`.
- **Manual**: Users can also delete the `cache.db` file directly; it will be recreated on next use.

#### Integration

The caching logic lives in `cache.py`. The `wiki_api.py` module imports from `cache.py` and wraps `get_outgoing_links()` and `get_backlinks()` to check/populate the cache transparently. The rest of the codebase (search, app) requires no changes.

### Single-Threaded

Each search job runs in a single background thread. No parallel expansion within a search.

## Frontend (`static/`)

### Layout (`index.html` + `style.css`)

- A title/heading at the top.
- Two text inputs labeled "Start article" and "End article".
- A submit button.
- A result area below the form.
- Clean, centered layout with readable fonts. No frameworks — plain HTML and CSS.

### Behavior (`script.js`)

- On submit:
  - Prevent default form submission.
  - Disable inputs and button; show a loading indicator in the result area.
  - Send `POST /api/search` with the two titles as JSON.
  - If the POST returns an error, display it and re-enable inputs.
  - If the POST returns a `job_id`, begin polling `GET /api/search/<job_id>` every 1–2 seconds.
- While polling:
  - If status is `"searching"`, update the loading indicator with the progress message.
  - If status is `"found"`, stop polling and render the chain as clickable links with arrows.
  - If status is `"not_found"`, stop polling and display the message.
  - If status is `"error"`, stop polling and display the error message.
  - Re-enable inputs and button when polling stops.
- Use vanilla JavaScript. No frameworks or libraries.

## Dependencies (`requirements.txt`)

```
flask
requests
```
