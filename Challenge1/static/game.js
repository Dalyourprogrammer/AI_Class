"use strict";

// ── State ────────────────────────────────────────────────────────────────
let currentState = window.INITIAL_STATE || {};

// ── DOM refs ─────────────────────────────────────────────────────────────
const dialogueText   = document.getElementById("dialogue-text");
const userInput      = document.getElementById("user-input");
const sendBtn        = document.getElementById("send-btn");
const stateBadge     = document.getElementById("state-badge");
const statueEl       = document.getElementById("suntzu-statue");
const scene          = document.getElementById("scene");
const endPanel       = document.getElementById("end-panel");
const farewellScreen = document.getElementById("farewell-screen");
const farewellQuote  = document.getElementById("farewell-quote");
const restartBtn     = document.getElementById("restart-btn");
const farewellBtn    = document.getElementById("farewell-btn");
const inputArea      = document.getElementById("input-area");

// ── Typewriter ────────────────────────────────────────────────────────────
function typewrite(el, text, speed = 22) {
  return new Promise(resolve => {
    el.textContent = "";
    el.classList.add("cursor");
    let i = 0;
    const interval = setInterval(() => {
      el.textContent += text[i];
      i++;
      if (i >= text.length) {
        clearInterval(interval);
        el.classList.remove("cursor");
        resolve();
      }
    }, speed);
  });
}

// ── Background mood ───────────────────────────────────────────────────────
const MOOD_CLASSES = ["mood-green", "mood-red", "mood-blue", "mood-pink"];

const CLASSIFICATION_MOOD = {
  demonstrates_understanding:  "mood-green",
  insightful_response:         "mood-green",
  expresses_confusion:         null,
  clarifying_question:         null,
  minimal_evasive:             null,
  off_topic_anachronistic:     "mood-blue",
  insulted:                    "mood-red",
  flirted:                     "mood-pink",
};

function setMood(classification) {
  const mood = CLASSIFICATION_MOOD[classification] ?? null;
  MOOD_CLASSES.forEach(c => scene.classList.remove(c));
  if (mood) scene.classList.add(mood);
}

// ── Statue speak pulse ────────────────────────────────────────────────────
function speakPulse() {
  statueEl.classList.remove("speaking");
  void statueEl.offsetWidth;
  statueEl.classList.add("speaking");
}

// ── Topic highlight — only lights up when a topic is mentioned ────────────
function highlightTopic(topicId) {
  document.querySelectorAll(".topic-node").forEach(node => {
    const t = node.dataset.topic;
    node.className = "topic-node";
    if (topicId && t === topicId) node.classList.add("active");
    else if (currentState.completed_topics && currentState.completed_topics.includes(t))
      node.classList.add("done");
  });
}

// ── Update UI from state ──────────────────────────────────────────────────
function updateUI(state) {
  currentState = state;
  stateBadge.textContent = `${cap(state.stage)} · ${cap(state.tone)}`;
  // don't highlight any topic node here — let highlightTopic handle it
  highlightTopic(null);
}

function cap(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : "";
}

// ── Send message ──────────────────────────────────────────────────────────
async function sendMessage() {
  const msg = userInput.value.trim();
  if (!msg) return;

  userInput.value = "";
  sendBtn.disabled = true;
  userInput.disabled = true;

  dialogueText.textContent = "";
  dialogueText.classList.add("loading");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    dialogueText.classList.remove("loading");

    if (data.error) {
      dialogueText.textContent = "[Error: " + data.error + "]";
      return;
    }

    setMood(data.classification);
    speakPulse();
    updateUI(data.state);
    highlightTopic(data.mentioned_topic || null);
    await typewrite(dialogueText, data.response);

    if (data.topic_advanced) {
      await new Promise(r => setTimeout(r, 600));
      const banner = document.createElement("div");
      banner.style.cssText = "color:#c9a84c;font-size:7px;margin-top:8px;opacity:0;transition:opacity 0.8s;";
      banner.textContent = `— Moving to: ${TOPIC_NAMES[data.state.topic] || data.state.topic} —`;
      dialogueText.parentNode.appendChild(banner);
      requestAnimationFrame(() => { banner.style.opacity = "1"; });
      await new Promise(r => setTimeout(r, 2000));
      banner.remove();
    }

    if (data.all_done) {
      inputArea.classList.add("hidden");
      endPanel.classList.remove("hidden");
    }

  } catch (err) {
    dialogueText.classList.remove("loading");
    dialogueText.textContent = "[Connection error]";
  } finally {
    sendBtn.disabled = false;
    userInput.disabled = false;
    userInput.focus();
  }
}

// ── Farewell ──────────────────────────────────────────────────────────────
farewellBtn.addEventListener("click", async () => {
  farewellBtn.disabled = true;
  const res = await fetch("/farewell", { method: "POST" });
  const data = await res.json();
  farewellScreen.classList.remove("hidden");
  await typewrite(farewellQuote, data.farewell || "May your path be clear, and your knowledge ever deeper.", 30);
});

restartBtn.addEventListener("click", async () => {
  await fetch("/new_game", { method: "POST" });
  window.location.reload();
});

// ── Revisit buttons ───────────────────────────────────────────────────────
document.querySelectorAll(".revisit-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const topic = btn.dataset.topic;
    endPanel.classList.add("hidden");
    inputArea.classList.remove("hidden");
    dialogueText.classList.add("loading");

    const res = await fetch(`/revisit/${topic}`, { method: "POST" });
    const data = await res.json();
    dialogueText.classList.remove("loading");

    updateUI(data.state);
    speakPulse();
    await typewrite(dialogueText, data.response);
  });
});

// ── Send on Enter ─────────────────────────────────────────────────────────
userInput.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});
sendBtn.addEventListener("click", sendMessage);

// ── Boot ──────────────────────────────────────────────────────────────────
(async () => {
  if (window.INITIAL_STATE) updateUI(window.INITIAL_STATE);
  if (window.OPENING_MESSAGE) {
    speakPulse();
    await typewrite(dialogueText, window.OPENING_MESSAGE);
  }
  userInput.focus();
})();
