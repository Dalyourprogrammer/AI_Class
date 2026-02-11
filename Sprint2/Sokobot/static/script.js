// ── Sokobot frontend ──────────────────────────────────────────
// Handles: puzzle loading, board rendering, solve polling,
// and step-by-step solution playback.

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

// ── State ─────────────────────────────────────────────────────
let puzzles      = [];      // loaded from /api/levels
let currentLevel = null;    // raw level text
let solution     = null;    // { moves, pushes, states_explored }
let stepIndex    = 0;       // current playback position
let playing      = false;
let playTimer    = null;
let pollTimer    = null;

// Board state: rebuilt from level text + applied moves
let boardState = null;  // { rows, player, boxes, goals, walls, width, height }

// ── Direction deltas ──────────────────────────────────────────
const DELTA = {
  u: [-1, 0], d: [1, 0], l: [0, -1], r: [0, 1],
  U: [-1, 0], D: [1, 0], L: [0, -1], R: [0, 1],
};

// ── Initialisation ────────────────────────────────────────────
loadPuzzles();

puzzleSelect.addEventListener("change", () => {
  const idx = puzzleSelect.value;
  if (idx === "") return;
  currentLevel = puzzles[idx].text;
  stopPlayback();
  solution = null;
  hideStatus();
  playbackDiv.classList.add("hidden");
  boardState = parseLevel(currentLevel);
  renderBoard();
  solveBtn.disabled = false;
});

solveBtn.addEventListener("click", startSolve);
resetBtn.addEventListener("click", () => goToStep(0));
stepBackBtn.addEventListener("click", () => goToStep(stepIndex - 1));
stepFwdBtn.addEventListener("click", () => goToStep(stepIndex + 1));
endBtn.addEventListener("click", () => goToStep(solution.moves.length));
playBtn.addEventListener("click", togglePlay);

// ── Load puzzles from API ─────────────────────────────────────
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

// ── Parse level text into board state ─────────────────────────
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

// ── Render the board to the DOM ───────────────────────────────
function renderBoard() {
  if (!boardState) return;
  const { width, height, walls, goals, boxes, player } = boardState;

  boardDiv.style.gridTemplateColumns = `repeat(${width}, 48px)`;
  boardDiv.innerHTML = "";

  // Build a set of "interior" cells for display purposes
  // (cells that are walls or reachable from the player)
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

// ── Solve ─────────────────────────────────────────────────────
async function startSolve() {
  if (!currentLevel) return;
  stopPlayback();
  solution = null;
  playbackDiv.classList.add("hidden");
  solveBtn.disabled = true;
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
      solveBtn.disabled = false;
      return;
    }

    showStatus("searching", "Searching...");
    pollForResult(data.job_id);
  } catch (e) {
    showStatus("error", "Network error.");
    solveBtn.disabled = false;
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
        showStatus("solved",
          `Solved in ${data.pushes} pushes (${data.states_explored.toLocaleString()} states explored)`);
        stepIndex = 0;
        boardState = parseLevel(currentLevel);
        renderBoard();
        playbackDiv.classList.remove("hidden");
        updateStepCounter();
      } else if (data.status === "no_solution") {
        showStatus("error", "No solution found.");
      } else {
        showStatus("error", data.message || "Unknown error.");
      }
      solveBtn.disabled = false;
    } catch (e) {
      clearInterval(pollTimer);
      showStatus("error", "Lost connection while polling.");
      solveBtn.disabled = false;
    }
  }, 500);
}

// ── Playback ──────────────────────────────────────────────────
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
    // Push: move the box too
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

function updateStepCounter() {
  if (!solution) return;
  stepCounter.textContent = `Step ${stepIndex} / ${solution.moves.length}`;
}

// ── Status helpers ────────────────────────────────────────────
function showStatus(type, message) {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
}

function hideStatus() {
  statusDiv.className = "status hidden";
}
