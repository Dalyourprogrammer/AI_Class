// ── Constants ─────────────────────────────────────────────────────────────────
const MOVE_RANGE = 2;

// ── State ─────────────────────────────────────────────────────────────────────
let state = null;
let preMoveTo = null;       // [row, col] — where the actor moves before acting
let selectedAction = null;
let remainingSteps = MOVE_RANGE;
let phase = "move1";        // "move1" → "action" → "move2" | "dash"
let preHealFlag = false;    // whether the current actor toggled "Use Potion"
let gameMode = "pvc";       // "pvc" | "pvp"

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-mode-pvc").addEventListener("click", () => startGame("pvc"));
  document.getElementById("btn-mode-pvp").addEventListener("click", () => startGame("pvp"));
  document.getElementById("new-game-btn").addEventListener("click", () => restartGame());
  document.getElementById("overlay-play-btn").addEventListener("click", () => restartGame());
  document.getElementById("player-potion-btn").addEventListener("click", () => togglePotion("player"));
  document.getElementById("ai-potion-btn").addEventListener("click", () => togglePotion("ai"));
  setupActionButtons();
});

async function startGame(mode) {
  gameMode = mode;
  document.getElementById("mode-select-screen").style.display = "none";
  document.getElementById("game-screen").style.display = "flex";
  document.getElementById("game-screen").style.flexDirection = "column";
  document.getElementById("game-screen").style.alignItems = "center";
  await newGame(mode);
}

async function restartGame() {
  await newGame(gameMode);
  hideOverlay();
}

// ── API Calls ─────────────────────────────────────────────────────────────────
async function newGame(mode) {
  const res = await fetch("/new_game", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  state = await res.json();
  gameMode = state.game_mode || mode;
  resetTurnState();
  updateLabels();
  render();
}

async function submitMove(preMoveArr, action, postMoveArr = null, dashToArr = null) {
  const body = {
    pre_heal: preHealFlag,
    pre_move_to: preMoveArr,
    action,
  };
  if (postMoveArr) body.post_move_to = postMoveArr;
  if (dashToArr) body.dash_to = dashToArr;

  const res = await fetch("/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json();

  // Play animations BEFORE updating state
  if (data.animation_data && data.animation_data.length > 0) {
    await playAnimations(data.animation_data);
  }

  state = data;
  resetTurnState();
  updateLabels();
  render();
}

function resetTurnState() {
  preMoveTo = null;
  selectedAction = null;
  remainingSteps = MOVE_RANGE;
  phase = "move1";
  preHealFlag = false;
  const pBtn = document.getElementById("player-potion-btn");
  if (pBtn) pBtn.classList.remove("active");
  const aBtn = document.getElementById("ai-potion-btn");
  if (aBtn) aBtn.classList.remove("active");
}

function updateLabels() {
  if (!state) return;
  const p1 = document.getElementById("p1-label");
  const p2 = document.getElementById("p2-label");
  const aiPotBtn = document.getElementById("ai-potion-btn");
  if (gameMode === "pvp") {
    if (p1) p1.textContent = "PLAYER 1";
    if (p2) p2.textContent = "PLAYER 2";
    // Show P2 potion button in PvP
    if (aiPotBtn) aiPotBtn.style.display = "";
  } else {
    if (p1) p1.textContent = "PLAYER";
    if (p2) p2.textContent = "BOT";
    if (aiPotBtn) aiPotBtn.style.display = "none";
  }
}

function togglePotion(actor) {
  if (!state || state.game_over) return;

  // In PvC, only player can toggle
  if (gameMode === "pvc" && actor !== "player") return;

  // In PvP, only the active actor's button works
  const currentActor = state.turn; // "player" | "ai"
  if (actor === "player" && currentActor !== "player") return;
  if (actor === "ai" && currentActor !== "ai") return;

  // Only usable before/during action phase
  if (phase !== "move1" && phase !== "action") return;

  // Check potion availability
  const hasPotion = actor === "player" ? state.player_has_potion : state.ai_has_potion;
  if (!hasPotion) return;

  preHealFlag = !preHealFlag;
  const btn = document.getElementById(actor === "player" ? "player-potion-btn" : "ai-potion-btn");
  if (btn) btn.classList.toggle("active", preHealFlag);
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
  const hpColor = (hp) => hp >= maxHp ? "#44cc44" : hp >= 2 ? "#cc8822" : "#cc2222";

  document.getElementById("player-hp-fill").style.width = pct(state.player_hp);
  document.getElementById("player-hp-fill").style.background = hpColor(state.player_hp);
  document.getElementById("ai-hp-fill").style.width = pct(state.ai_hp);
  document.getElementById("ai-hp-fill").style.background = hpColor(state.ai_hp);

  document.getElementById("player-hp-text").textContent = `${state.player_hp} / ${maxHp}`;
  document.getElementById("ai-hp-text").textContent = `${state.ai_hp} / ${maxHp}`;

  const pPotBtn = document.getElementById("player-potion-btn");
  const pPotStat = document.getElementById("player-potion-status");
  const aPotBtn = document.getElementById("ai-potion-btn");
  const aPotStat = document.getElementById("ai-potion-status");

  if (pPotBtn) pPotBtn.disabled = !state.player_has_potion;
  if (pPotStat) pPotStat.textContent = state.player_has_potion ? "READY" : "USED";
  if (pPotStat) pPotStat.style.color = state.player_has_potion ? "#44aa66" : "#444";

  if (aPotBtn) aPotBtn.disabled = !state.ai_has_potion;
  if (aPotStat) aPotStat.textContent = state.ai_has_potion ? "READY" : "USED";
  if (aPotStat) aPotStat.style.color = state.ai_has_potion ? "#aa4444" : "#444";
}

function renderGrid() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";

  const playerKey = state.player_pos.join(",");
  const aiKey = state.ai_pos.join(",");
  const preKey = preMoveTo ? preMoveTo.join(",") : null;

  // Determine active actor for PvP
  const activeActor = state.turn; // "player" or "ai"
  const isMyTurn = !state.game_over && (
    gameMode === "pvc" ? activeActor === "player" :
    true  // in PvP both actors are human
  );

  // Build highlight set based on current phase
  let highlightSet = new Set();
  if (isMyTurn) {
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


      const isPlayer = key === playerKey;
      const isAI = key === aiKey;
      const isPreMarker = preKey && key === preKey && !isPlayer && !isAI;

      if (isPlayer) {
        cell.classList.add("player-cell");
        const sprite = document.createElement("div");
        sprite.className = "cell-wizard blue";
        cell.appendChild(sprite);

        if (isMyTurn) {
          if (phase === "move1" && activeActor === "player") {
            cell.style.cursor = "pointer";
            cell.title = "Stay in place";
            cell.addEventListener("click", () => onCellClicked(state.player_pos));
          } else if (phase === "move2" && highlightSet.has(key) && activeActor === "player") {
            cell.style.cursor = "pointer";
            cell.addEventListener("click", () => onCellClicked([r, c]));
          }
        }
        // In PvP when it's P2's turn, clicking on P2 sprite starts their move
        if (isMyTurn && phase === "move1" && activeActor === "ai" && gameMode === "pvp") {
          // handled by aiKey branch below
        }

      } else if (isAI) {
        cell.classList.add("ai-cell");
        const sprite = document.createElement("div");
        sprite.className = "cell-wizard red";
        cell.appendChild(sprite);

        if (isMyTurn && gameMode === "pvp" && activeActor === "ai") {
          if (phase === "move1") {
            cell.style.cursor = "pointer";
            cell.title = "Stay in place";
            cell.addEventListener("click", () => onCellClicked(state.ai_pos));
          } else if (phase === "move2" && highlightSet.has(key)) {
            cell.style.cursor = "pointer";
            cell.addEventListener("click", () => onCellClicked([r, c]));
          }
        }

      } else {
        if (isPreMarker && (phase === "action" || phase === "move2" || phase === "dash")) {
          cell.classList.add("selected");
          if (phase === "move2") {
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

  const activeActor = state.turn;
  const isMyTurn = !state.game_over && (
    gameMode === "pvc" ? activeActor === "player" :
    true
  );

  if (!isMyTurn) {
    panel.style.visibility = "hidden";
    phaseEl.textContent = "";
    return;
  }

  const actorLabel = gameMode === "pvp" && activeActor === "ai" ? "PLAYER 2" : "PLAYER 1";

  if (phase === "move1") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = `${actorLabel} — STEP 1: MOVE BEFORE ACTING`;
  } else if (phase === "action") {
    panel.style.visibility = "visible";
    phaseEl.textContent = `${actorLabel} — STEP 2: CHOOSE ACTION (${remainingSteps} STEPS LEFT)`;
    setActionButtonsEnabled(true, validActionsFromPos(preMoveTo));
  } else if (phase === "move2") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = `${actorLabel} — STEP 3: MOVE AFTER ACTION (${remainingSteps} STEPS)`;
  } else if (phase === "dash") {
    panel.style.visibility = "hidden";
    phaseEl.textContent = `${actorLabel} — DASH: CLICK A PURPLE CELL`;
  }
}

function setActionButtonsEnabled(enabled, validActions = []) {
  for (const a of ["fire_bolt", "dagger", "dash"]) {
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
    container.innerHTML = `<span class="log-empty">No moves yet.</span>`;
    return;
  }

  const aiLabel = gameMode === "pvp" ? "P2" : "BOT";
  container.innerHTML = log.slice().reverse().map(entry => `
    <div class="log-entry">
      <div class="log-turn">TURN ${entry.turn}</div>
      <div class="log-player">${entry.player || ""}</div>
      <div class="log-ai">${entry.ai || ""}</div>
    </div>
  `).join("");
}

// ── Action Validity ───────────────────────────────────────────────────────────
function validActionsFromPos(pos) {
  const actions = ["fire_bolt"];
  const activeActor = state.turn;
  const [pr, pc] = pos;
  // Opponent position depends on who's acting
  const oppPos = activeActor === "player" ? state.ai_pos : state.player_pos;
  const [or, oc] = oppPos;
  const chebyshev = Math.max(Math.abs(pr - or), Math.abs(pc - oc));
  if (chebyshev === 1) actions.push("dagger");
  actions.push("dash");
  return actions;
}

// ── BFS Helpers (no column blocking) ─────────────────────────────────────────
function bfsMinDist(from, to, opponentPos) {
  if (from[0] === to[0] && from[1] === to[1]) return 0;
  const oppKey = opponentPos.join(",");
  const visited = new Set([from.join(",")]);
  const queue = [[from, 0]];

  while (queue.length) {
    const [pos, dist] = queue.shift();
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = pos[0] + dr, nc = pos[1] + dc;
      const nk = `${nr},${nc}`;
      if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5 &&
          nk !== oppKey && !visited.has(nk)) {
        if (nr === to[0] && nc === to[1]) return dist + 1;
        visited.add(nk);
        queue.push([[nr, nc], dist + 1]);
      }
    }
  }
  return MOVE_RANGE + 1;
}

function computeMove2Reachable(from, steps, opponentPos) {
  const oppKey = opponentPos.join(",");
  const visited = new Set([from.join(",")]);
  const queue = [[from, 0]];
  const reachable = [from];

  while (queue.length) {
    const [pos, dist] = queue.shift();
    if (dist === steps) continue;
    for (const [dr, dc] of [[-1,0],[1,0],[0,-1],[0,1]]) {
      const nr = pos[0] + dr, nc = pos[1] + dc;
      const nk = `${nr},${nc}`;
      if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5 &&
          nk !== oppKey && !visited.has(nk)) {
        visited.add(nk);
        reachable.push([nr, nc]);
        queue.push([[nr, nc], dist + 1]);
      }
    }
  }

  state._move2_reachable = reachable;
}

function computeDashReachable(from, opponentPos) {
  const oppKey = opponentPos.join(",");
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
          nk !== oppKey && !visited.has(nk)) {
        visited.add(nk);
        queue.push([[nr, nc], dist + 1]);
      }
    }
  }

  state._dash_reachable = reachable;
}

// Get the active actor's position and opponent's position
function getActorPositions() {
  const actor = state.turn;
  const actorPos = actor === "player" ? state.player_pos : state.ai_pos;
  const oppPos = actor === "player" ? state.ai_pos : state.player_pos;
  return { actorPos, oppPos };
}

// ── Interaction ───────────────────────────────────────────────────────────────
function onCellClicked(pos) {
  if (!state || state.game_over) return;
  // In PvC only player can interact; in PvP either can
  if (gameMode === "pvc" && state.turn !== "player") return;

  const { actorPos, oppPos } = getActorPositions();

  if (phase === "move1") {
    preMoveTo = pos;
    remainingSteps = MOVE_RANGE - bfsMinDist(actorPos, pos, oppPos);
    phase = "action";
    renderGrid();
    renderActions();

  } else if (phase === "move2") {
    submitMove(preMoveTo, selectedAction, pos);
  }
}

function setupActionButtons() {
  document.getElementById("btn-fire-bolt").addEventListener("click", () => onActionChosen("fire_bolt"));
  document.getElementById("btn-dagger").addEventListener("click", () => onActionChosen("dagger"));
  document.getElementById("btn-dash").addEventListener("click", () => onActionChosen("dash"));
}

function onActionChosen(action) {
  if (phase !== "action") return;
  selectedAction = action;

  const { oppPos } = getActorPositions();

  if (action === "dash") {
    phase = "dash";
    computeDashReachable(preMoveTo, oppPos);
    renderGrid();
    renderActions();
  } else if (remainingSteps === 0) {
    submitMove(preMoveTo, action, preMoveTo);
  } else {
    phase = "move2";
    computeMove2Reachable(preMoveTo, remainingSteps, oppPos);
    renderGrid();
    renderActions();
  }
}

function onDashDestSelected(pos) {
  if (phase !== "dash" || !preMoveTo) return;
  submitMove(preMoveTo, "dash", null, pos);
}

// ── Animation Engine ──────────────────────────────────────────────────────────
async function playAnimations(events) {
  const layer = document.getElementById("animation-layer");
  for (const event of events) {
    await playOneAnimation(layer, event);
    await delay(150);
  }
}

async function playOneAnimation(layer, event) {
  // Play pre-heal aura first if applicable
  if (event.pre_heal) {
    const healPos = event.actor === "player" ? state.player_pos : state.ai_pos;
    await playHealAura(layer, healPos, 500);
    await delay(100);
  }

  if (event.action === "fire_bolt") {
    await playFireball(layer, event, 550);
  } else if (event.action === "dagger") {
    await playSlash(layer, event, 500);
  } else if (event.action === "dash") {
    // Brief flash on actor's from_pos
    flashCellByPos(event.from_pos, "#4488ff");
  }
}

async function playFireball(layer, event, duration) {
  return new Promise(resolve => {
    const el = document.createElement("div");
    el.className = "anim-fireball";

    const fromCell = getCellElement(event.from_pos);
    const toCell   = getCellElement(event.to_pos);
    if (!fromCell || !toCell) { resolve(); return; }

    const layerRect = layer.getBoundingClientRect();
    const fromRect  = fromCell.getBoundingClientRect();
    const toRect    = toCell.getBoundingClientRect();

    const startX = fromRect.left - layerRect.left + fromRect.width / 2 - 5;
    const startY = fromRect.top  - layerRect.top  + fromRect.height / 2 - 5;
    const endX   = toRect.left   - layerRect.left + toRect.width / 2 - 5;
    const endY   = toRect.top    - layerRect.top  + toRect.height / 2 - 5;

    el.style.left = startX + "px";
    el.style.top  = startY + "px";
    layer.appendChild(el);

    const anim = el.animate([
      { transform: "translate(0, 0)", opacity: 1 },
      { transform: `translate(${endX - startX}px, ${endY - startY}px)`, opacity: 1 }
    ], { duration, easing: "linear", fill: "forwards" });

    anim.onfinish = () => {
      if (event.hit) flashCellByPos(event.to_pos, "#ff6600");
      el.remove();
      resolve();
    };
  });
}

async function playSlash(layer, event, duration) {
  return new Promise(resolve => {
    const el = document.createElement("div");
    el.className = "anim-slash";

    const targetCell = getCellElement(event.to_pos);
    if (!targetCell) { resolve(); return; }

    const layerRect  = layer.getBoundingClientRect();
    const targetRect = targetCell.getBoundingClientRect();

    el.style.left   = (targetRect.left - layerRect.left) + "px";
    el.style.top    = (targetRect.top  - layerRect.top)  + "px";
    el.style.width  = targetRect.width  + "px";
    el.style.height = targetRect.height + "px";

    // Draw pixel slash as inline SVG
    el.innerHTML = `<svg width="100%" height="100%" viewBox="0 0 ${targetRect.width} ${targetRect.height}">
      <line x1="8" y1="8" x2="${targetRect.width-8}" y2="${targetRect.height-8}" stroke="#cc44ff" stroke-width="5" stroke-linecap="square"/>
      <line x1="${targetRect.width-8}" y1="8" x2="8" y2="${targetRect.height-8}" stroke="#ee88ff" stroke-width="3" stroke-linecap="square"/>
    </svg>`;

    layer.appendChild(el);

    const anim = el.animate([
      { opacity: 0, transform: "scale(0.4) rotate(-20deg)" },
      { opacity: 1, transform: "scale(1.3) rotate(10deg)", offset: 0.25 },
      { opacity: 1, transform: "scale(1.0) rotate(0deg)", offset: 0.6 },
      { opacity: 0, transform: "scale(0.8) rotate(0deg)" }
    ], { duration, fill: "forwards" });

    anim.onfinish = () => {
      if (event.hit) flashCellByPos(event.to_pos, "#cc44ff");
      el.remove();
      resolve();
    };
  });
}

async function playHealAura(layer, pos, duration) {
  return new Promise(resolve => {
    const el = document.createElement("div");
    el.className = "anim-heal-aura";

    const cell = getCellElement(pos);
    if (!cell) { resolve(); return; }

    const layerRect = layer.getBoundingClientRect();
    const cellRect  = cell.getBoundingClientRect();

    el.style.left   = (cellRect.left - layerRect.left) + "px";
    el.style.top    = (cellRect.top  - layerRect.top)  + "px";
    el.style.width  = cellRect.width  + "px";
    el.style.height = cellRect.height + "px";
    layer.appendChild(el);

    const anim = el.animate([
      { opacity: 0, transform: "scale(0.7)" },
      { opacity: 1, transform: "scale(1.15)", offset: 0.35 },
      { opacity: 0.7, transform: "scale(1.0)", offset: 0.65 },
      { opacity: 0, transform: "scale(0.85)" }
    ], { duration, fill: "forwards" });

    anim.onfinish = () => { el.remove(); resolve(); };
  });
}

function getCellElement(pos) {
  const index = pos[0] * 5 + pos[1];
  const cells = document.querySelectorAll(".cell");
  return cells[index] || null;
}

function flashCellByPos(pos, color) {
  const cell = getCellElement(pos);
  if (!cell) return;
  cell.animate([
    { background: color },
    { background: "" }
  ], { duration: 350, easing: "ease-out" });
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function showOverlay() {
  const overlay = document.getElementById("overlay");
  const title   = document.getElementById("overlay-title");
  const sub     = document.getElementById("overlay-sub");

  overlay.classList.add("show");

  if (state.winner === "player") {
    title.textContent = gameMode === "pvp" ? "PLAYER 1 WINS!" : "VICTORY!";
    title.className = "overlay-title win";
    sub.textContent = gameMode === "pvp" ? "Player 1 defeated Player 2!" : "You outsmarted the bot!";
  } else {
    title.textContent = gameMode === "pvp" ? "PLAYER 2 WINS!" : "DEFEATED!";
    title.className = "overlay-title lose";
    sub.textContent = gameMode === "pvp" ? "Player 2 defeated Player 1!" : "The bot outmaneuvered you!";
  }
}

function hideOverlay() {
  document.getElementById("overlay").classList.remove("show");
}
