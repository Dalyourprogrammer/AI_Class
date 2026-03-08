// ── State ────────────────────────────────────────────────────────────────────
let state = null;
let selectedMove = null;   // [row, col] — chosen move destination
let selectedAction = null; // chosen action (when attacking first)
let actionFirst = false;   // whether player chose attack-first order
let phase = "order";       // "order" | "move" | "action" | "action_first" | "move_after" | "dash"

// ── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  fetchState();
  document.getElementById("new-game-btn").addEventListener("click", newGame);
  document.getElementById("overlay-play-btn").addEventListener("click", newGame);
  document.getElementById("btn-order-move").addEventListener("click", () => chooseOrder(false));
  document.getElementById("btn-order-attack").addEventListener("click", () => chooseOrder(true));
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

async function submitMove(moveTo, action, dashTo = null) {
  const body = { move_to: moveTo, action, action_first: actionFirst };
  if (dashTo) body.dash_to = dashTo;

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
  selectedMove = null;
  selectedAction = null;
  actionFirst = false;
  phase = "order";
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function render() {
  if (!state) return;
  renderHUD();
  renderOrderButtons();
  renderGrid();
  renderActions();
  renderMessage();
  renderLog();
  if (state.game_over) showOverlay();
}

function renderHUD() {
  const pct = (hp) => `${(hp / 5) * 100}%`;
  const hpColor = (hp) => hp >= 4 ? "#66bb6a" : hp >= 2 ? "#ffa726" : "#ef5350";

  const pFill = document.getElementById("player-hp-fill");
  const aFill = document.getElementById("ai-hp-fill");

  pFill.style.width = pct(state.player_hp);
  pFill.style.background = hpColor(state.player_hp);
  aFill.style.width = pct(state.ai_hp);
  aFill.style.background = hpColor(state.ai_hp);

  document.getElementById("player-hp-text").textContent = `${state.player_hp} / 5`;
  document.getElementById("ai-hp-text").textContent = `${state.ai_hp} / 5`;

  document.getElementById("player-potion").textContent = state.player_has_potion ? "🧪 Potion" : "  Used";
  document.getElementById("ai-potion").textContent = state.ai_has_potion ? "🧪 Potion" : "  Used";
}

function renderOrderButtons() {
  const panel = document.getElementById("order-panel");
  const showOrder = !state.game_over && state.turn === "player" && phase === "order";
  panel.style.display = showOrder ? "flex" : "none";
}

function renderGrid() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";

  const columns = new Set((state.columns || []).map(([r, c]) => `${r},${c}`));
  const playerKey = state.player_pos.join(",");
  const aiKey = state.ai_pos.join(",");

  let highlightSet = new Set();
  if (!state.game_over && state.turn === "player") {
    if (phase === "move" || phase === "move_after") {
      highlightSet = new Set(state.valid_moves.map(([r, c]) => `${r},${c}`));
    } else if (phase === "dash") {
      highlightSet = new Set((state._dash_reachable || []).map(([r, c]) => `${r},${c}`));
    }
  }

  const selectedKey = selectedMove ? selectedMove.join(",") : null;

  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 5; c++) {
      const key = `${r},${c}`;
      const cell = document.createElement("div");
      cell.className = "cell";

      if (columns.has(key)) {
        cell.classList.add("column");
        cell.innerHTML = `<span class="icon">🗿</span>`;
      } else if (key === playerKey) {
        cell.classList.add("player");
        cell.innerHTML = `<span class="icon">🧙</span>`;
      } else if (key === aiKey) {
        cell.classList.add("ai");
        cell.innerHTML = `<span class="icon">🤖</span>`;
      } else {
        cell.classList.add("empty");

        if (key === selectedKey) {
          cell.classList.add("selected");
        } else if (phase === "dash" && highlightSet.has(key)) {
          cell.classList.add("dash-dest");
          cell.addEventListener("click", () => onDashDestSelected([r, c]));
        } else if ((phase === "move" || phase === "move_after") && highlightSet.has(key)) {
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

  // Allow clicking player's own cell to stay in place during move phases
  if (!state.game_over && state.turn === "player" && (phase === "move" || phase === "move_after")) {
    const cellIndex = state.player_pos[0] * 5 + state.player_pos[1];
    const playerCell = grid.children[cellIndex];
    playerCell.style.cursor = "pointer";
    playerCell.title = "Stay in place";
    playerCell.addEventListener("click", () => onCellClicked(state.player_pos));
  }
}

function renderActions() {
  const panel = document.getElementById("action-panel");
  const phaseEl = document.getElementById("phase-indicator");

  if (state.game_over || state.turn !== "player" || phase === "order") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = "";
    return;
  }

  panel.style.visibility = "visible";

  if (phase === "move") {
    phaseEl.textContent = "Step 1: Click to move (or stay), then pick an action";
    setActionButtonsEnabled(false);
  } else if (phase === "action") {
    phaseEl.textContent = `Step 2: Choose an action (moved to [${selectedMove}])`;
    setActionButtonsEnabled(true, validActionsFromPos(selectedMove));
  } else if (phase === "action_first") {
    phaseEl.textContent = "Step 1: Choose an action (from current position), then move";
    setActionButtonsEnabled(true, state.valid_actions.filter(a => a !== "dash"));
  } else if (phase === "move_after") {
    phaseEl.textContent = `Step 2: Click to move after ${selectedAction.replace("_", " ")}`;
    setActionButtonsEnabled(false);
  } else if (phase === "dash") {
    phaseEl.textContent = "Dash: click a purple cell to move again";
    setActionButtonsEnabled(false);
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
  // Recompute valid actions for the player at `pos` (post-move).
  const actions = ["fire_bolt"];
  const [pr, pc] = pos;
  const [ar, ac] = state.ai_pos;
  const chebyshev = Math.max(Math.abs(pr - ar), Math.abs(pc - ac));
  if (chebyshev === 1) actions.push("dagger");
  if (state.player_has_potion) actions.push("heal");
  actions.push("dash");
  return actions;
}

// ── Order Selection ───────────────────────────────────────────────────────────
function chooseOrder(attackFirst) {
  actionFirst = attackFirst;
  if (attackFirst) {
    phase = "action_first";
  } else {
    phase = "move";
  }
  renderOrderButtons();
  renderGrid();
  renderActions();
}

// ── Interaction ───────────────────────────────────────────────────────────────
function onCellClicked(pos) {
  if (state.game_over || state.turn !== "player") return;

  if (phase === "move") {
    selectedMove = pos;
    phase = "action";
    renderGrid();
    renderActions();
  } else if (phase === "move_after") {
    selectedMove = pos;
    submitMove(selectedMove, selectedAction);
  }
}

function setupActionButtons() {
  document.getElementById("btn-fire-bolt").addEventListener("click", () => onActionChosen("fire_bolt"));
  document.getElementById("btn-dagger").addEventListener("click", () => onActionChosen("dagger"));
  document.getElementById("btn-heal").addEventListener("click", () => onActionChosen("heal"));
  document.getElementById("btn-dash").addEventListener("click", () => onActionChosen("dash"));
}

function onActionChosen(action) {
  if (phase === "action") {
    // Move-first order: action chosen after moving
    if (action === "dash") {
      phase = "dash";
      computeDashReachable(selectedMove);
      renderGrid();
      renderActions();
    } else {
      submitMove(selectedMove, action);
    }
  } else if (phase === "action_first") {
    // Attack-first order: action chosen before moving
    selectedAction = action;
    phase = "move_after";
    renderGrid();
    renderActions();
  }
}

function computeDashReachable(from) {
  const columns = new Set((state.columns || []).map(([r, c]) => `${r},${c}`));
  const aiKey = state.ai_pos.join(",");
  const DIRS = [[-1,0],[1,0],[0,-1],[0,1]];
  const visited = new Set([from.join(",")]);
  const queue = [[from, 0]];
  const reachable = [];

  while (queue.length) {
    const [pos, dist] = queue.shift();
    if (dist > 0) reachable.push(pos);
    if (dist === 2) continue;
    for (const [dr, dc] of DIRS) {
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

function onDashDestSelected(pos) {
  if (phase !== "dash" || !selectedMove) return;
  submitMove(selectedMove, "dash", pos);
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
