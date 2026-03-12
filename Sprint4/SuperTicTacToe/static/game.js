let state = null;
let waiting = false;

async function fetchState() {
  const res = await fetch('/state');
  state = await res.json();
  render();
}

async function newGame() {
  waiting = false;
  const res = await fetch('/new_game', { method: 'POST' });
  state = await res.json();
  render();
}

async function sendMove(macro, micro) {
  if (waiting) return;
  waiting = true;
  setStatus('<span class="thinking">Thinking...</span>');

  const res = await fetch('/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ macro, micro }),
  });
  state = await res.json();
  waiting = false;
  render();
}

function render() {
  if (!state) return;
  renderBoard();
  renderStatus();
}

function renderStatus() {
  const el = document.getElementById('status');
  if (state.terminal) {
    if (state.winner === 1) {
      el.innerHTML = '<span class="winner-x">X wins!</span>';
    } else if (state.winner === 2) {
      el.innerHTML = '<span class="winner-o">O wins!</span>';
    } else {
      el.innerHTML = '<span class="draw">Draw!</span>';
    }
  } else if (state.current === 1) {
    el.innerHTML = 'Your turn — <span class="x-color">X</span>';
  } else {
    el.innerHTML = '<span class="o-color">O</span> is thinking...';
  }
}

function setStatus(html) {
  document.getElementById('status').innerHTML = html;
}

function renderBoard() {
  const container = document.getElementById('macro-board');
  container.innerHTML = '';

  const legalSet = new Set(
    (state.legal_moves || []).map(([m, i]) => `${m},${i}`)
  );

  for (let macroIdx = 0; macroIdx < 9; macroIdx++) {
    const macroStatus = state.macro[macroIdx]; // 0, 1, 2, or -1
    const isActive = state.active === -1
      ? macroStatus === 0
      : state.active === macroIdx;

    const macroCell = document.createElement('div');
    macroCell.className = 'macro-cell';

    if (macroStatus === 1) {
      macroCell.classList.add('won-x');
    } else if (macroStatus === 2) {
      macroCell.classList.add('won-o');
    } else if (macroStatus === -1) {
      macroCell.classList.add('drawn');
    } else if (isActive && !state.terminal && state.current === 1 && !waiting) {
      macroCell.classList.add('active');
    }

    // Overlay for won/drawn boards
    if (macroStatus !== 0) {
      const overlay = document.createElement('div');
      overlay.className = 'macro-overlay';
      if (macroStatus === 1) {
        overlay.classList.add('x');
        overlay.textContent = 'X';
      } else if (macroStatus === 2) {
        overlay.classList.add('o');
        overlay.textContent = 'O';
      } else {
        overlay.classList.add('draw-icon');
        overlay.textContent = '—';
      }
      macroCell.appendChild(overlay);
    }

    // Micro cells
    for (let microIdx = 0; microIdx < 9; microIdx++) {
      const cellVal = state.boards[macroIdx][microIdx];
      const microCell = document.createElement('div');
      microCell.className = 'micro-cell';

      if (cellVal === 1) {
        microCell.classList.add('x');
        microCell.textContent = 'X';
      } else if (cellVal === 2) {
        microCell.classList.add('o');
        microCell.textContent = 'O';
      }

      const key = `${macroIdx},${microIdx}`;
      const isLegal = legalSet.has(key) && !state.terminal && state.current === 1 && !waiting;

      if (isLegal) {
        microCell.classList.add('clickable');
        microCell.addEventListener('click', () => sendMove(macroIdx, microIdx));
      } else if (macroStatus !== 0) {
        microCell.classList.add('blocked');
      }

      macroCell.appendChild(microCell);
    }

    container.appendChild(macroCell);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('new-game-btn').addEventListener('click', newGame);
  fetchState();
});
