// ── Constants ─────────────────────────────────────────────────────────────────
const MOVE_RANGE = 2;

// ── State ─────────────────────────────────────────────────────────────────────
let state = null;
let preMoveTo = null;     // [row, col] — where the player moves before acting
let selectedAction = null;
let remainingSteps = MOVE_RANGE;
// Phases: "move1" → "action" → "move2" | "dash"
let phase = "move1";

// ── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  fetchState();
  document.getElementById("new-game-btn").addEventListener("click", newGame);
  document.getElementById("overlay-play-btn").addEventListener("click", newGame);
  setupActionButtons();
});

// ── API Calls ─────────────────────────────────────────────────────────────────
async function fetchState() {
  const res = await fetch("/state");
  state = await res.json();
  resetTurnState();
  render();
}

async function newGame() {
  const res = await fetch("/new_game", { method: "POST" });
  state = await res.json();
  resetTurnState();
  hideOverlay();
  render();
}

async function submitMove(preMoveArr, action, postMoveArr = null, dashToArr = null) {
  const body = { pre_move_to: preMoveArr, action };
  if (postMoveArr) body.post_move_to = postMoveArr;
  if (dashToArr) body.dash_to = dashToArr;

  const res = await fetch("/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  state = await res.json();
  resetTurnState();
  render();
}

function resetTurnState() {
  preMoveTo = null;
  selectedAction = null;
  remainingSteps = MOVE_RANGE;
  phase = "move1";
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function render() {
  if (!state) return;
  renderHUD();
  renderGrid();
  renderActions();
  renderMessage();
  renderLog();
  if (state.game_over) showOverlay();
}

function renderHUD() {
  const maxHp = state.max_hp || 3;
  const pct = (hp) => `${(hp / maxHp) * 100}%`;
  const hpColor = (hp) => hp >= maxHp ? "#66bb6a" : hp >= 2 ? "#ffa726" : "#ef5350";

  const pFill = document.getElementById("player-hp-fill");
  const aFill = document.getElementById("ai-hp-fill");

  pFill.style.width = pct(state.player_hp);
  pFill.style.background = hpColor(state.player_hp);
  aFill.style.width = pct(state.ai_hp);
  aFill.style.background = hpColor(state.ai_hp);

  document.getElementById("player-hp-text").textContent = `${state.player_hp} / ${maxHp}`;
  document.getElementById("ai-hp-text").textContent = `${state.ai_hp} / ${maxHp}`;

  document.getElementById("player-potion").textContent = state.player_has_potion ? "🧪 Potion" : "  Used";
  document.getElementById("ai-potion").textContent = state.ai_has_potion ? "🧪 Potion" : "  Used";
}

function renderGrid() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";

  const columns = new Set((state.columns || []).map(([r, c]) => `${r},${c}`));
  const playerKey = state.player_pos.join(",");
  const aiKey = state.ai_pos.join(",");
  const preKey = preMoveTo ? preMoveTo.join(",") : null;

  // Build highlight set based on current phase
  let highlightSet = new Set();
  if (!state.game_over && state.turn === "player") {
    if (phase === "move1") {
      highlightSet = new Set(state.valid_moves.map(([r, c]) => `${r},${c}`));
    } else if (phase === "move2") {
      highlightSet = new Set((state._move2_reachable || []).map(([r, c]) => `${r},${c}`));
    } else if (phase === "dash") {
      highlightSet = new Set((state._dash_reachable || []).map(([r, c]) => `${r},${c}`));
    }
  }

  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 5; c++) {
      const key = `${r},${c}`;
      const cell = document.createElement("div");
      cell.className = "cell";

      const isColumn = columns.has(key);
      const isPlayer = key === playerKey;
      const isAI = key === aiKey;
      const isPreMarker = preKey && key === preKey && !isPlayer && !isAI && !isColumn;

      if (isColumn) {
        cell.classList.add("column");
        cell.innerHTML = `<span class="icon">🗿</span>`;

      } else if (isPlayer) {
        cell.classList.add("player");
        cell.innerHTML = `<span class="icon">🧙</span>`;
        // Clickable in move1 to stay, and in move2 if player_pos is reachable from preMoveTo
        if (!state.game_over && state.turn === "player") {
          if (phase === "move1") {
            cell.style.cursor = "pointer";
            cell.title = "Stay in place";
            cell.addEventListener("click", () => onCellClicked(state.player_pos));
          } else if (phase === "move2" && highlightSet.has(key)) {
            cell.style.cursor = "pointer";
            cell.title = "Stay here";
            cell.addEventListener("click", () => onCellClicked([r, c]));
          }
        }

      } else if (isAI) {
        cell.classList.add("ai");
        cell.innerHTML = `<span class="icon">🤖</span>`;

      } else {
        cell.classList.add("empty");

        if (isPreMarker && (phase === "action" || phase === "move2" || phase === "dash")) {
          // Show the pre-move attack position marker
          cell.classList.add("selected");
          if (phase === "move2") {
            // Pre-move cell is always reachable (0 remaining steps) — click to stay
            cell.style.cursor = "pointer";
            cell.title = "Stay at attack position";
            cell.addEventListener("click", () => onCellClicked([r, c]));
          }
        } else if (phase === "dash" && highlightSet.has(key)) {
          cell.classList.add("dash-dest");
          cell.addEventListener("click", () => onDashDestSelected([r, c]));
        } else if ((phase === "move1" || phase === "move2") && highlightSet.has(key)) {
          cell.classList.add("reachable");
          cell.addEventListener("click", () => onCellClicked([r, c]));
        }
      }

      const coord = document.createElement("span");
      coord.className = "coord";
      coord.textContent = `${r},${c}`;
      cell.appendChild(coord);

      grid.appendChild(cell);
    }
  }
}

function renderActions() {
  const panel = document.getElementById("action-panel");
  const phaseEl = document.getElementById("phase-indicator");

  if (state.game_over || state.turn !== "player") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = "";
    return;
  }

  if (phase === "move1") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = "Step 1: Click where to move before attacking (or stay in place)";
  } else if (phase === "action") {
    panel.style.visibility = "visible";
    phaseEl.textContent = `Step 2: Choose an action (at [${preMoveTo}], ${remainingSteps} step(s) left)`;
    setActionButtonsEnabled(true, validActionsFromPos(preMoveTo));
  } else if (phase === "move2") {
    panel.style.visibility = "hidden";
    const stepWord = remainingSteps === 1 ? "step" : "steps";
    phaseEl.textContent = `Step 3: Click where to move after your action (${remainingSteps} ${stepWord} remaining)`;
  } else if (phase === "dash") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = "Dash: Click a purple cell to move";
  }
}

function setActionButtonsEnabled(enabled, validActions = []) {
  const actions = ["fire_bolt", "dagger", "heal", "dash"];
  for (const a of actions) {
    const btn = document.getElementById(`btn-${a.replace("_", "-")}`);
    if (!btn) continue;
    btn.disabled = !enabled || !validActions.includes(a);
  }
}

function renderMessage() {
  document.getElementById("message-bar").textContent = state.message || "";
}

function renderLog() {
  const container = document.getElementById("move-log-entries");
  const log = state.move_log || [];

  if (log.length === 0) {
    container.innerHTML = `<span style="color:#555;font-size:0.8rem;padding:6px 14px;display:block;">No moves yet.</span>`;
    return;
  }

  container.innerHTML = log.slice().reverse().map(entry => `
    <div class="log-entry">
      <div class="log-turn">Turn ${entry.turn}</div>
      <div class="log-player">${entry.player}</div>
      <div class="log-ai">${entry.ai}</div>
    </div>
  `).join("");
}

// ── Action Validity ───────────────────────────────────────────────────────────
function validActionsFromPos(pos) {
  // Compute valid actions for the player at `pos` (the pre-move attack position).
  const actions = ["fire_bolt"];
  const [pr, pc] = pos;
  const [ar, ac] = state.ai_pos;
  const chebyshev = Math.max(Math.abs(pr - ar), Math.abs(pc - ac));
  if (chebyshev === 1) actions.push("dagger");
  if (state.player_has_potion) actions.push("heal");
  actions.push("dash");
  return actions;
}

// ── BFS Helpers ───────────────────────────────────────────────────────────────
function bfsMinDist(from, to) {
  if (from[0] === to[0] && from[1] === to[1]) return 0;
  const columns = new Set((state.columns || []).map(([r, c]) => `${r},${c}`));
  const aiKey = state.ai_pos.join(",");
  const visited = new Set([from.join(",")]);
  const queue = [[from, 0]];

  while (queue.length) {
    const [pos, dist] = queue.shift();
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = pos[0] + dr, nc = pos[1] + dc;
      const nk = `${nr},${nc}`;
      if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5 &&
          !columns.has(nk) && nk !== aiKey && !visited.has(nk)) {
        if (nr === to[0] && nc === to[1]) return dist + 1;
        visited.add(nk);
        queue.push([[nr, nc], dist + 1]);
      }
    }
  }
  return MOVE_RANGE + 1; // unreachable
}

function computeMove2Reachable(from, steps) {
  // Cells reachable from `from` within `steps` moves (includes `from` at dist 0)
  const columns = new Set((state.columns || []).map(([r, c]) => `${r},${c}`));
  const aiKey = state.ai_pos.join(",");
  const visited = new Set([from.join(",")]);
  const queue = [[from, 0]];
  const reachable = [from]; // can always stay

  while (queue.length) {
    const [pos, dist] = queue.shift();
    if (dist === steps) continue;
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = pos[0] + dr, nc = pos[1] + dc;
      const nk = `${nr},${nc}`;
      if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5 &&
          !columns.has(nk) && nk !== aiKey && !visited.has(nk)) {
        visited.add(nk);
        reachable.push([nr, nc]);
        queue.push([[nr, nc], dist + 1]);
      }
    }
  }

  state._move2_reachable = reachable;
}

function computeDashReachable(from) {
  const columns = new Set((state.columns || []).map(([r, c]) => `${r},${c}`));
  const aiKey = state.ai_pos.join(",");
  const visited = new Set([from.join(",")]);
  const queue = [[from, 0]];
  const reachable = [];

  while (queue.length) {
    const [pos, dist] = queue.shift();
    if (dist > 0) reachable.push(pos);
    if (dist === MOVE_RANGE) continue;
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = pos[0] + dr, nc = pos[1] + dc;
      const nk = `${nr},${nc}`;
      if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5 &&
          !columns.has(nk) && nk !== aiKey && !visited.has(nk)) {
        visited.add(nk);
        queue.push([[nr, nc], dist + 1]);
      }
    }
  }

  state._dash_reachable = reachable;
}

// ── Interaction ───────────────────────────────────────────────────────────────
function onCellClicked(pos) {
  if (state.game_over || state.turn !== "player") return;

  if (phase === "move1") {
    preMoveTo = pos;
    remainingSteps = MOVE_RANGE - bfsMinDist(state.player_pos, pos);
    phase = "action";
    renderGrid();
    renderActions();

  } else if (phase === "move2") {
    // pos is the final position after the action
    submitMove(preMoveTo, selectedAction, pos);
  }
}

function setupActionButtons() {
  document.getElementById("btn-fire-bolt").addEventListener("click", () => onActionChosen("fire_bolt"));
  document.getElementById("btn-dagger").addEventListener("click", () => onActionChosen("dagger"));
  document.getElementById("btn-heal").addEventListener("click", () => onActionChosen("heal"));
  document.getElementById("btn-dash").addEventListener("click", () => onActionChosen("dash"));
}

function onActionChosen(action) {
  if (phase !== "action") return;
  selectedAction = action;

  if (action === "dash") {
    phase = "dash";
    computeDashReachable(preMoveTo);
    renderGrid();
    renderActions();
  } else if (remainingSteps === 0) {
    // No movement remaining — submit immediately with post_move = pre_move
    submitMove(preMoveTo, action, preMoveTo);
  } else {
    phase = "move2";
    computeMove2Reachable(preMoveTo, remainingSteps);
    renderGrid();
    renderActions();
  }
}

function onDashDestSelected(pos) {
  if (phase !== "dash" || !preMoveTo) return;
  submitMove(preMoveTo, "dash", null, pos);
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function showOverlay() {
  const overlay = document.getElementById("overlay");
  const title = document.getElementById("overlay-title");
  const sub = document.getElementById("overlay-sub");

  overlay.classList.add("show");

  if (state.winner === "player") {
    title.textContent = "Victory!";
    title.className = "overlay-title win";
    sub.textContent = "You outsmarted the AI. Well played!";
  } else {
    title.textContent = "Defeated!";
    title.className = "overlay-title lose";
    sub.textContent = "The AI outmaneuvered you. Try again?";
  }
}

function hideOverlay() {
  document.getElementById("overlay").classList.remove("show");
}
