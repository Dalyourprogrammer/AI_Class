# Puzzle Editor — Design Plan

## Context

Add a puzzle editor so users can design custom Sokoban puzzles in the browser
and solve them.  The existing `/api/solve` endpoint already accepts arbitrary
level text, so **no back-end changes are needed**.

## Key Design: Editor Grid Storage & Conversion

### The editor grid is a 2D array of layered cells:

```javascript
editorGrid[row][col] = { base: 'floor' | 'wall' | 'goal',
                          entity: 'none' | 'box' | 'player' }
```

**Why layered instead of raw characters?**  Tools compose cleanly:
- "Goal" tool toggles the base without affecting the entity (a box stays)
- "Box" tool sets the entity without affecting whether it's a goal cell
- No complex character-switching logic

### Conversion to solver format — one character per cell:

| base  | entity | char | meaning         |
|-------|--------|------|-----------------|
| wall  | (any)  | `#`  | wall            |
| floor | none   | ` `  | empty floor     |
| floor | box    | `$`  | box             |
| floor | player | `@`  | player          |
| goal  | none   | `.`  | goal            |
| goal  | box    | `*`  | box on goal     |
| goal  | player | `+`  | player on goal  |

Join rows with `\n` → standard Sokoban text → POST to existing `/api/solve`.

## Files Changed

| File | Change |
|------|--------|
| `static/index.html` | Add mode toggle, editor controls (size inputs, tool palette, validation, solve button) |
| `static/style.css`  | Add ~65 lines: mode toggle, tool buttons, editable cursor, validation |
| `static/script.js`  | Add ~150 lines: editor state, mode switching, grid init/render, tool logic, validation, conversion, solve integration |
| `app.py`            | **No changes** |
| `solver.py`         | **No changes** |

## Implementation Steps

### Step 1: HTML structure
- Mode toggle (`Load Puzzle` / `Create Puzzle`) after subtitle
- Add `id="load-controls"` to existing controls div
- New `#editor-controls` div (hidden) with:
  - Width/height number inputs (min 4, max 12, default 7) + "New Grid" button
  - 6 tool buttons: Wall, Floor, Goal, Box, Player, Eraser
  - Validation display div
  - Solve button

### Step 2: CSS additions
- `.mode-btn` / `.mode-btn.active` — pill-shaped toggle
- `.editor-size` — flex row for width/height inputs
- `.tool-btn` / `.tool-btn.active` — palette buttons
- `.editor-validation` / `.valid` / `.invalid` — live feedback text
- `.board.editable .cell` — crosshair cursor + hover outline
- `#editor-solve-btn` — same style as existing solve button

### Step 3: Editor state + mode switching (JS)
- State vars: `editorMode`, `editorGrid`, `selectedTool`, `isDrawing`
- `switchMode(toEditor)`:
  - Toggle load/editor panels visibility
  - Toggle `.editable` on board div
  - Init editor grid if empty, render it
- `initEditorGrid(w, h)`:
  - Border cells → `{ base: 'wall', entity: 'none' }`
  - Interior cells → `{ base: 'floor', entity: 'none' }`

### Step 4: Tool selection + cell painting (JS)
- Tool button click → set `selectedTool`, toggle `.active`
- `renderEditorBoard()`:
  - Reads from `editorGrid`, uses same CSS classes as `renderBoard()`
  - `editorCellClass(cell)` maps `{base, entity}` → existing CSS class name
  - `editorCellText(cell)` maps → `@`, `⬛`, `·`, or empty
  - Attaches mousedown (start painting) + mouseenter (drag painting) handlers
- `applyTool(r, c)` — tool logic:
  - **Wall**: `base='wall', entity='none'`
  - **Floor**: `base='floor'`, keep entity
  - **Goal**: toggle base `goal↔floor`, keep entity
  - **Box**: toggle entity `box↔none` (wall→floor if needed)
  - **Player**: `entity='player'`, remove player from all other cells first
  - **Eraser**: `base='floor', entity='none'`
- Global mouseup → `isDrawing = false`
- Skip player tool during drag-painting

### Step 5: Live validation (JS)
- `updateValidation()`: count boxes, goals, check player exists
- Display: `Boxes: 2 | Goals: 2 | Player: Yes — Ready to solve!`
- Or error: `Need a player`, `Box count (2) must equal goal count (1)`
- Enable/disable editor solve button based on validity

### Step 6: Conversion + solve integration (JS)
- `editorGridToText()`: map each cell → char via lookup table, join rows
- Editor solve button: `currentLevel = editorGridToText(); startSolve();`
- Tweak `startSolve()`: use `getActiveSolveBtn()` to disable/enable correct button

### Step 7: Smoke test
- Existing solver tests still pass (no solver changes)
- Load mode still works (select built-in, solve, playback)
- Create mode: make simple puzzle, solve, verify playback
- Unsolvable puzzle shows "No solution found"
- Validation prevents solving with missing player / mismatched counts
- Mode switching preserves editor grid
- Drag-painting works for wall/floor/goal/eraser
