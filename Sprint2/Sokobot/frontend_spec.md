# Sokobot Front-End — Interface Specification

## 1. What the front-end must do

The front-end is a single HTML page that talks to the Flask API.  It has four
jobs:

1. **Load puzzles** — fetch `GET /api/levels`, populate a dropdown
2. **Render the board** — parse a level text string into a CSS grid of tiles
3. **Solve** — `POST /api/solve`, then poll `GET /api/solve/<job_id>` until done
4. **Playback** — step through the move list, animating player + box movement

## 2. Design Decisions

### 2a. Board rendering

The level text uses single characters (`#`, `@`, `$`, `.`, `*`, `+`, ` `).
The front-end parses this into sets of coordinates (walls, goals, boxes, player),
then renders a CSS grid where each cell gets a class based on what occupies it.

**Why a CSS grid?**  The board is a fixed-size rectangle.  CSS grid with
`grid-template-columns: repeat(width, 48px)` gives us a pixel-perfect layout
with zero JavaScript layout code.

**Interior detection:**  Spaces outside the walls are "exterior" — they should
look different from playable floor.  We flood-fill from the player position to
find all interior cells.

### 2b. Move replay

The API returns moves as `["d", "r", "U", "l", ...]`.  For each move:
- Compute the delta from the direction letter
- Move the player to the new position
- If the move is UPPERCASE (push), also move the box at that position one step
  further in the same direction

**Why rebuild from scratch each step?**  We could maintain mutable state, but
for step-backward and jump-to-start we'd need undo.  Instead, `goToStep(n)`
replays moves 0..n-1 from the initial board state.  This is simple and correct
— the board is small, so replaying even 50 moves is instant.

### 2c. Playback controls

- Reset (⏮) — go to step 0
- Step back (⏪) — go to step n-1
- Play/Pause (▶/⏸) — auto-advance with a timer
- Step forward (⏩) — go to step n+1
- Jump to end (⏭) — go to final step
- Speed slider — controls ms between steps

### 2d. Status feedback

A status bar shows:
- "Searching... N states explored" (updated by polling)
- "Solved in P pushes (N states explored)" (green, on success)
- Error messages (red)

## 3. File Structure

| File | Responsibility |
|------|---------------|
| `index.html` | Page structure — dropdown, button, board div, playback controls, legend |
| `style.css` | Visual styling — grid cells, dark theme, control layout |
| `script.js` | All behavior — API calls, parsing, rendering, playback |

## 4. Implementation Steps

Build and test incrementally:

1. **`index.html`** — static structure (dropdown, button, board div, controls)
2. **`style.css`** — board grid tiles, dark theme, controls layout
3. **`script.js` step A** — load puzzles from API, populate dropdown
4. **`script.js` step B** — parse level text, render board grid
5. **`script.js` step C** — submit solve, poll for result, show status
6. **`script.js` step D** — playback controls (step, play/pause, speed)
7. **Smoke test** — run server, solve each difficulty tier, verify playback
