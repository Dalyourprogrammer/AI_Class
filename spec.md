# Wikipedia Chain Finder — Project Spec

## Overview

A web application that finds chains of linked Wikipedia articles between two given articles using bidirectional iterative deepening search.

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

## Backend (Python Flask)

### API Endpoint

**`POST /api/find-chain`**

Request body:
```json
{
  "start": "Cat",
  "end": "Science"
}
```

**Success response:**
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

**Not found response** (no chain within depth limit):
```json
{
  "status": "not_found",
  "message": "No chain found within 7 articles."
}
```

**Error response** (invalid input, API failure, timeout):
```json
{
  "status": "error",
  "message": "Article 'Xyzzy' not found on Wikipedia."
}
```

URLs are constructed deterministically: `https://en.wikipedia.org/wiki/` + URL-encoded title.

**`DELETE /api/cache`**

Clears all cached link data. Response:
```json
{
  "status": "ok",
  "message": "Cache cleared."
}
```

### Route for Frontend

Flask serves `static/index.html` at the root route (`GET /`).

### Input Validation

Before starting the search:

1. Validate that both articles exist using the Wikimedia API.
2. Resolve redirects using `&redirects=1` and return the canonical title. For example, if the user types "USA", resolve it to "United States".
3. Handle the trivial case where start == end (after redirect resolution): return a chain of one article immediately.

### Server-Side Timeout

Set a timeout of 60 seconds. If the search has not completed, return an error response rather than hanging.

## Wikimedia API Client (`wiki_api.py`)

All requests must include a descriptive `User-Agent` header as required by Wikimedia policy.

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

The caching logic lives in a new module `cache.py`. The `wiki_api.py` module imports from `cache.py` and wraps `get_outgoing_links()` and `get_backlinks()` to check/populate the cache transparently. The rest of the codebase (search, app) requires no changes.

### Single-Threaded

The search runs in a single thread. No parallel expansion.

## Frontend (`static/`)

### Layout (`index.html` + `style.css`)

- A title/heading at the top.
- Two text inputs labeled "Start article" and "End article".
- A submit button.
- A result area below the form.
- Clean, centered layout with readable fonts. No frameworks — plain HTML and CSS.

### Behavior (`script.js`)

- On submit, send a `POST` request to `/api/find-chain` with the two titles as JSON.
- While the request is in flight:
  - Disable the submit button and inputs.
  - Show a loading indicator (spinner or "Searching..." text).
- On success (`status: "found"`):
  - Display the chain as a sequence of clickable links (using the URLs from the response), connected by arrows or a similar visual separator.
- On not found (`status: "not_found"`):
  - Display the message from the response.
- On error (`status: "error"`):
  - Display the error message from the response.
- Set a generous `fetch` timeout to match the server-side timeout.
- Use vanilla JavaScript. No frameworks or libraries.

## Dependencies (`requirements.txt`)

```
flask
requests
```
