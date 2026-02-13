// ── Sokobot frontend ──────────────────────────────────────────
// Built incrementally:
//   Step A: Load puzzles from API, populate dropdown
//   Step B: Parse level text, render board grid
//   Step C: Submit solve, poll for result, show status
//   Step D: Playback controls (step, play/pause, speed)

"use strict";

// ── DOM refs ──────────────────────────────────────────────────
const puzzleSelect  = document.getElementById("puzzle-select");
const solveBtn      = document.getElementById("solve-btn");
const statusDiv     = document.getElementById("status");
const boardDiv      = document.getElementById("board");
const playbackDiv   = document.getElementById("playback");
const resetBtn      = document.getElementById("reset-btn");
const stepBackBtn   = document.getElementById("step-back-btn");
const playBtn       = document.getElementById("play-btn");
const stepFwdBtn    = document.getElementById("step-fwd-btn");
const endBtn        = document.getElementById("end-btn");
const speedSlider   = document.getElementById("speed");
const stepCounter   = document.getElementById("step-counter");

// Editor DOM refs
const modeLoadBtn      = document.getElementById("mode-load");
const modeCreateBtn    = document.getElementById("mode-create");
const loadControls     = document.getElementById("load-controls");
const editorControls   = document.getElementById("editor-controls");
const editorWidthIn    = document.getElementById("editor-width");
const editorHeightIn   = document.getElementById("editor-height");
const newGridBtn       = document.getElementById("new-grid-btn");
const editorValidation = document.getElementById("editor-validation");
const editorSolveBtn   = document.getElementById("editor-solve-btn");

// ── State ─────────────────────────────────────────────────────
let puzzles      = [];      // loaded from /api/levels
let currentLevel = null;    // raw level text
let boardState   = null;    // { width, height, walls, goals, boxes, player }
let solution     = null;    // { moves, pushes, states_explored }
let stepIndex    = 0;       // current playback position
let playing      = false;
let playTimer    = null;
let pollTimer    = null;

// Editor state
let editorMode    = false;
let editorGrid    = null;   // 2D array of { base, entity }
let selectedTool  = "goal";
let isDrawing     = false;

// ── Direction deltas ──────────────────────────────────────────
const DELTA = {
  u: [-1, 0], d: [1, 0], l: [0, -1], r: [0, 1],
  U: [-1, 0], D: [1, 0], L: [0, -1], R: [0, 1],
};

// ══════════════════════════════════════════════════════════════
// STEP A: Load puzzles from API, populate dropdown
// ══════════════════════════════════════════════════════════════

async function loadPuzzles() {
  try {
    const res = await fetch("/api/levels");
    puzzles = await res.json();
    puzzleSelect.innerHTML = '<option value="">-- select a puzzle --</option>';
    puzzles.forEach((p, i) => {
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = `${p.name}  (${p.boxes} box${p.boxes > 1 ? "es" : ""})`;
      puzzleSelect.appendChild(opt);
    });
  } catch (e) {
    showStatus("error", "Failed to load puzzles.");
  }
}

puzzleSelect.addEventListener("change", () => {
  const idx = puzzleSelect.value;
  if (idx === "") return;
  currentLevel = puzzles[idx].text;
  stopPlayback();
  solution = null;
  solveBtn.disabled = false;
  hideStatus();
  playbackDiv.classList.add("hidden");
  boardState = parseLevel(currentLevel);
  renderBoard();
});

// ══════════════════════════════════════════════════════════════
// STEP B: Parse level text, render board as CSS grid
// ══════════════════════════════════════════════════════════════

function parseLevel(text) {
  const lines = text.split("\n");
  const height = lines.length;
  const width = Math.max(...lines.map(l => l.length));
  const walls = new Set();
  const goals = new Set();
  const boxes = new Set();
  let player = null;

  for (let r = 0; r < height; r++) {
    for (let c = 0; c < lines[r].length; c++) {
      const ch = lines[r][c];
      const key = `${r},${c}`;
      if (ch === "#")       walls.add(key);
      else if (ch === ".")  goals.add(key);
      else if (ch === "$")  boxes.add(key);
      else if (ch === "@")  player = key;
      else if (ch === "*")  { boxes.add(key); goals.add(key); }
      else if (ch === "+")  { player = key; goals.add(key); }
    }
  }
  return { width, height, walls, goals, boxes, player };
}

function renderBoard() {
  if (!boardState) return;
  const { width, height, walls, goals, boxes, player } = boardState;

  boardDiv.style.gridTemplateColumns = `repeat(${width}, 48px)`;
  boardDiv.innerHTML = "";

  // Find interior cells (walls + flood-fill from player)
  const interior = new Set([...walls]);
  computeInterior(interior, boardState);

  for (let r = 0; r < height; r++) {
    for (let c = 0; c < width; c++) {
      const key = `${r},${c}`;
      const cell = document.createElement("div");
      cell.className = "cell";

      const isWall   = walls.has(key);
      const isGoal   = goals.has(key);
      const isBox    = boxes.has(key);
      const isPlayer = (key === player);
      const isInside = interior.has(key);

      if (isWall) {
        cell.classList.add("wall");
      } else if (!isInside) {
        cell.classList.add("outside");
      } else if (isPlayer && isGoal) {
        cell.classList.add("player-on-goal");
        cell.textContent = "@";
      } else if (isPlayer) {
        cell.classList.add("player");
        cell.textContent = "@";
      } else if (isBox && isGoal) {
        cell.classList.add("box-on-goal");
        cell.textContent = "\u2B1B";
      } else if (isBox) {
        cell.classList.add("box");
        cell.textContent = "\u2B1B";
      } else if (isGoal) {
        cell.classList.add("goal");
        cell.textContent = "\u00B7";
      } else {
        cell.classList.add("floor");
      }
      boardDiv.appendChild(cell);
    }
  }
}

// Flood-fill from player to find all interior floor cells
function computeInterior(interior, state) {
  if (!state.player) return;
  const [pr, pc] = state.player.split(",").map(Number);
  const queue = [[pr, pc]];
  const key0 = `${pr},${pc}`;
  if (!interior.has(key0)) interior.add(key0);

  // Also add all box and goal positions
  for (const k of state.boxes) interior.add(k);
  for (const k of state.goals) interior.add(k);

  while (queue.length > 0) {
    const [r, c] = queue.shift();
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = r + dr, nc = c + dc;
      const nk = `${nr},${nc}`;
      if (nr >= 0 && nr < state.height && nc >= 0 && nc < state.width &&
          !interior.has(nk) && !state.walls.has(nk)) {
        interior.add(nk);
        queue.push([nr, nc]);
      }
    }
  }
}

// ══════════════════════════════════════════════════════════════
// STEP C: Submit solve request, poll for result
// ══════════════════════════════════════════════════════════════

solveBtn.addEventListener("click", startSolve);

function getActiveSolveBtn() {
  return editorMode ? editorSolveBtn : solveBtn;
}

async function startSolve() {
  if (!currentLevel) return;
  stopPlayback();
  solution = null;
  playbackDiv.classList.add("hidden");
  getActiveSolveBtn().disabled = true;
  showStatus("searching", "Submitting puzzle...");

  try {
    const res = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: currentLevel }),
    });
    const data = await res.json();

    if (data.status === "error") {
      showStatus("error", data.message);
      getActiveSolveBtn().disabled = false;
      return;
    }

    showStatus("searching", "Searching...");
    pollForResult(data.job_id);
  } catch (e) {
    showStatus("error", "Network error.");
    getActiveSolveBtn().disabled = false;
  }
}

function pollForResult(jobId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/solve/${jobId}`);
      const data = await res.json();

      if (data.status === "searching") {
        showStatus("searching",
          `Searching... ${data.states_explored.toLocaleString()} states explored`);
        return;
      }

      clearInterval(pollTimer);
      pollTimer = null;

      if (data.status === "solved") {
        solution = data;
        stepIndex = 0;
        showStatus("solved",
          `Solved in ${data.pushes} pushes (${data.states_explored.toLocaleString()} states explored)`);
        boardState = parseLevel(currentLevel);
        boardDiv.classList.remove("editable");
        renderBoard();
        playbackDiv.classList.remove("hidden");
        updateStepCounter();
      } else if (data.status === "no_solution") {
        showStatus("error", "No solution found.");
      } else {
        showStatus("error", data.message || "Unknown error.");
      }
      getActiveSolveBtn().disabled = false;
    } catch (e) {
      clearInterval(pollTimer);
      showStatus("error", "Lost connection while polling.");
      getActiveSolveBtn().disabled = false;
    }
  }, 500);
}

function updateStepCounter() {
  if (!solution) return;
  stepCounter.textContent = `Step ${stepIndex} / ${solution.moves.length}`;
}

// ══════════════════════════════════════════════════════════════
// STEP D: Playback — step through moves, animate solution
// ══════════════════════════════════════════════════════════════

resetBtn.addEventListener("click", () => goToStep(0));
stepBackBtn.addEventListener("click", () => goToStep(stepIndex - 1));
stepFwdBtn.addEventListener("click", () => goToStep(stepIndex + 1));
endBtn.addEventListener("click", () => goToStep(solution.moves.length));
playBtn.addEventListener("click", togglePlay);

function goToStep(n) {
  if (!solution) return;
  n = Math.max(0, Math.min(n, solution.moves.length));
  stepIndex = n;

  // Rebuild board state from initial level, applying moves 0..n-1
  boardState = parseLevel(currentLevel);
  for (let i = 0; i < n; i++) {
    applyMove(boardState, solution.moves[i]);
  }
  renderBoard();
  updateStepCounter();
}

function applyMove(state, move) {
  const delta = DELTA[move];
  if (!delta || !state.player) return;

  const [pr, pc] = state.player.split(",").map(Number);
  const [dr, dc] = delta;
  const nr = pr + dr, nc = pc + dc;
  const newPlayerKey = `${nr},${nc}`;

  const isPush = move === move.toUpperCase();

  if (isPush) {
    // Push: move the box one step further in the same direction
    const boxTarget = `${nr + dr},${nc + dc}`;
    state.boxes.delete(newPlayerKey);
    state.boxes.add(boxTarget);
  }

  state.player = newPlayerKey;
}

function togglePlay() {
  if (playing) {
    stopPlayback();
  } else {
    if (stepIndex >= solution.moves.length) {
      goToStep(0);  // restart if at end
    }
    playing = true;
    playBtn.textContent = "\u23F8";  // pause icon
    tick();
  }
}

function tick() {
  if (!playing || !solution) return;
  if (stepIndex >= solution.moves.length) {
    stopPlayback();
    return;
  }
  goToStep(stepIndex + 1);
  const delay = 600 / speedSlider.value;
  playTimer = setTimeout(tick, delay);
}

function stopPlayback() {
  playing = false;
  if (playTimer) { clearTimeout(playTimer); playTimer = null; }
  playBtn.textContent = "\u25B6";  // play icon
}

// ── Status helpers ────────────────────────────────────────────
function showStatus(type, message) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
}

function hideStatus() {
  statusDiv.className = "status hidden";
}

// ══════════════════════════════════════════════════════════════
// STEP E: Puzzle Editor — mode switching, grid, tools, validation
// ══════════════════════════════════════════════════════════════

// ── Mode switching ───────────────────────────────────────────
modeLoadBtn.addEventListener("click", () => switchMode(false));
modeCreateBtn.addEventListener("click", () => switchMode(true));

function switchMode(toEditor) {
  editorMode = toEditor;
  stopPlayback();
  solution = null;
  playbackDiv.classList.add("hidden");
  hideStatus();

  modeLoadBtn.classList.toggle("active", !toEditor);
  modeCreateBtn.classList.toggle("active", toEditor);
  loadControls.classList.toggle("hidden", toEditor);
  editorControls.classList.toggle("hidden", !toEditor);
  boardDiv.classList.toggle("editable", toEditor);

  if (toEditor) {
    if (!editorGrid) initEditorGrid(+editorWidthIn.value, +editorHeightIn.value);
    renderEditorBoard();
    updateValidation();
  } else {
    // Restore load-mode board if a puzzle was selected
    if (currentLevel) {
      boardState = parseLevel(currentLevel);
      renderBoard();
    } else {
      boardDiv.innerHTML = "";
    }
  }
}

// ── Editor grid init ─────────────────────────────────────────
newGridBtn.addEventListener("click", () => {
  initEditorGrid(+editorWidthIn.value, +editorHeightIn.value);
  stopPlayback();
  solution = null;
  playbackDiv.classList.add("hidden");
  hideStatus();
  renderEditorBoard();
  updateValidation();
});

function initEditorGrid(w, h) {
  w = Math.max(4, Math.min(16, w));
  h = Math.max(4, Math.min(16, h));
  editorGrid = [];
  for (let r = 0; r < h; r++) {
    const row = [];
    for (let c = 0; c < w; c++) {
      const isBorder = (r === 0 || r === h - 1 || c === 0 || c === w - 1);
      row.push({ base: isBorder ? "wall" : "floor", entity: "none" });
    }
    editorGrid.push(row);
  }
}

// ── Render editor board ──────────────────────────────────────
function renderEditorBoard() {
  if (!editorGrid) return;
  const h = editorGrid.length;
  const w = editorGrid[0].length;

  boardDiv.style.gridTemplateColumns = `repeat(${w}, 48px)`;
  boardDiv.innerHTML = "";

  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      const cell = document.createElement("div");
      cell.className = "cell " + editorCellClass(editorGrid[r][c]);
      cell.textContent = editorCellText(editorGrid[r][c]);

      cell.addEventListener("mousedown", (e) => {
        e.preventDefault();
        isDrawing = true;
        applyTool(r, c);
      });
      cell.addEventListener("mouseenter", () => {
        if (isDrawing && selectedTool !== "player") applyTool(r, c);
      });

      boardDiv.appendChild(cell);
    }
  }
}

function editorCellClass(cell) {
  if (cell.base === "wall") return "wall";
  if (cell.entity === "player" && cell.base === "goal") return "player-on-goal";
  if (cell.entity === "player") return "player";
  if (cell.entity === "box" && cell.base === "goal") return "box-on-goal";
  if (cell.entity === "box") return "box";
  if (cell.base === "goal") return "goal";
  return "floor";
}

function editorCellText(cell) {
  if (cell.base === "wall") return "";
  if (cell.entity === "player") return "@";
  if (cell.entity === "box") return "\u2B1B";
  if (cell.base === "goal" && cell.entity === "none") return "\u00B7";
  return "";
}

// ── Tool selection ───────────────────────────────────────────
document.querySelectorAll(".tool-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tool-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    selectedTool = btn.dataset.tool;
  });
});

// ── Apply tool to cell ───────────────────────────────────────
function applyTool(r, c) {
  const cell = editorGrid[r][c];

  switch (selectedTool) {
    case "wall":
      cell.base = "wall";
      cell.entity = "none";
      break;
    case "floor":
      cell.base = "floor";
      // keep entity as-is
      break;
    case "goal":
      cell.base = (cell.base === "goal") ? "floor" : "goal";
      // keep entity as-is
      break;
    case "box":
      if (cell.entity === "box") {
        cell.entity = "none";
      } else {
        if (cell.base === "wall") cell.base = "floor";
        cell.entity = "box";
      }
      break;
    case "player":
      // Remove player from all other cells first
      for (const row of editorGrid)
        for (const c2 of row)
          if (c2.entity === "player") c2.entity = "none";
      if (cell.base === "wall") cell.base = "floor";
      cell.entity = "player";
      break;
    case "eraser":
      cell.base = "floor";
      cell.entity = "none";
      break;
  }

  renderEditorBoard();
  updateValidation();
}

// Global mouseup to stop drag-painting
document.addEventListener("mouseup", () => { isDrawing = false; });

// ── Live validation ──────────────────────────────────────────
function updateValidation() {
  if (!editorGrid) return;
  let boxes = 0, goals = 0, hasPlayer = false;

  for (const row of editorGrid) {
    for (const cell of row) {
      if (cell.entity === "box") boxes++;
      if (cell.entity === "player") hasPlayer = true;
      if (cell.base === "goal") goals++;
    }
  }

  const problems = [];
  if (!hasPlayer) problems.push("Need a player");
  if (boxes === 0) problems.push("Need at least 1 box");
  if (goals === 0) problems.push("Need at least 1 goal");
  if (boxes !== goals && boxes > 0 && goals > 0)
    problems.push(`Box count (${boxes}) must equal goal count (${goals})`);

  if (problems.length === 0) {
    editorValidation.textContent = `Boxes: ${boxes} | Goals: ${goals} | Player: Yes \u2014 Ready to solve!`;
    editorValidation.className = "editor-validation valid";
    editorSolveBtn.disabled = false;
  } else {
    editorValidation.textContent = problems.join(" \u2022 ");
    editorValidation.className = "editor-validation invalid";
    editorSolveBtn.disabled = true;
  }
}

// ── Convert editor grid to solver text ───────────────────────
function editorGridToText() {
  const CHAR_MAP = {
    "wall|none":   "#", "wall|box": "#", "wall|player": "#",
    "floor|none":  " ", "floor|box": "$", "floor|player": "@",
    "goal|none":   ".", "goal|box":  "*", "goal|player":  "+",
  };
  return editorGrid.map(row =>
    row.map(cell => CHAR_MAP[`${cell.base}|${cell.entity}`] || " ").join("")
  ).join("\n");
}

// ── Editor solve button ──────────────────────────────────────
editorSolveBtn.addEventListener("click", () => {
  currentLevel = editorGridToText();
  startSolve();
});

// ── Init ──────────────────────────────────────────────────────
loadPuzzles();
