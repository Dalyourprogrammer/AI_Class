# Sun Tzu Conversation Simulator — Game Plan

## Concept
A visual-novel-style web app for a chill 1-on-1 philosophical conversation with a simulated Sun Tzu. The user reads his teachings, responds, and the conversation evolves based on their engagement. The experience ends with a farewell or the option to revisit topics.

---

## Project File Structure

```
Challenge1/
├── Game_Plan.md               ← this document
├── Sun Tzu Persona.txt        ← persona reference
├── The Art of War.txt         ← source text for RAG
├── .env                       ← ANTHROPIC_API_KEY (gitignored)
├── requirements.txt
├── ingest.py                  ← one-time: chunk, embed, load ChromaDB
├── rag.py                     ← RAG query interface
├── state_machine.py           ← Topic × Stage × Tone state + transitions
├── classifier.py              ← LLM call 1: classify user input
├── responder.py               ← LLM call 2: generate Sun Tzu response
├── app.py                     ← Flask app (routes, session state)
├── templates/
│   └── index.html             ← visual novel UI
└── static/
    ├── style.css
    ├── game.js
    └── suntzu_sprite.css      ← CSS-animated statue + eyebrows
```

---

## Component 1 — RAG System

**Tools:** ChromaDB (local), `sentence-transformers` (`all-MiniLM-L6-v2`)

### Ingestion (`ingest.py`)
- Load `The Art of War.txt`
- Chunk by paragraph/verse with ~200-token chunks, 20-token overlap
- Embed each chunk with sentence-transformers
- Store in local ChromaDB collection `art_of_war`
- Run once; persist to `./chroma_db/`

### Query (`rag.py`)
- `query_rag(query_text, n_results=3) → list[str]`
- Embed query, search ChromaDB by cosine similarity, return top-k text chunks

### MVP Exercise
Build `rag_mvp.py` first — ingest 5 chunks, query "victory without fighting", print results. Validates that ChromaDB + sentence-transformers are working before full integration.

---

## Component 2 — State Machine

**File:** `state_machine.py`

### Topics (4 nodes)

| ID | Name | Description |
|----|------|-------------|
| `shi` | Strategic Advantage | Momentum, positioning, potential energy |
| `zhi` | Foreknowledge | Intelligence, knowing before acting |
| `bian` | Adaptability | Variation, fluidity, responding to change |
| `quanmou` | Holistic Planning | Deliberation, preparation, whole-picture strategy |

### Topic Graph (meaningful conceptual edges)
```
shi ←→ bian        (advantage requires adaptability)
shi ←→ quanmou     (advantage is planned, not accidental)
zhi ←→ quanmou     (planning requires foreknowledge)
zhi ←→ shi         (knowing enables positioning)
bian ←→ quanmou    (plans must flex)
```

### Stages (sequential, transition-triggerable)

| Stage | Description |
|-------|-------------|
| `introduction` | Sun Tzu introduces the topic, orients the student |
| `examination` | Probes understanding through questions |
| `challenge` | Introduces tension or a harder question |
| `resolution` | Arrives at conclusion or rests in productive uncertainty |

Normal progression: introduction → examination → challenge → resolution.
Early/late transitions are triggered by the classification result.

### Tones (6)

| Tone | Trigger |
|------|---------|
| `warm` | Default opening; student shows genuine curiosity |
| `probing` | Student gives shallow or evasive answers |
| `delighted` | Student offers a surprising or insightful response |
| `skeptical` | Student shows overconfidence or misunderstanding |
| `disappointed` | Repeated minimal/evasive answers (after 2x) |
| `playful` | Student asks an unexpected but on-topic question |

### State Dataclass
```python
@dataclass
class ConvState:
    topic: str              # shi | zhi | bian | quanmou
    stage: str              # introduction | examination | challenge | resolution
    tone: str               # warm | probing | delighted | skeptical | disappointed | playful
    turn_count: int
    history: list[dict]     # [{role, content}]
    completed_topics: list[str]
```

### Transition Table

| Classification | Stage Effect | Tone Effect |
|----------------|-------------|-------------|
| `demonstrates_understanding` | advance stage | → warm or delighted |
| `expresses_confusion` | hold or retreat stage | → probing |
| `insightful_response` | advance stage (may skip one) | → delighted |
| `clarifying_question` | hold stage | → warm |
| `minimal_evasive` | hold stage | → probing (→ disappointed after 2x) |
| `off_topic_anachronistic` | hold stage | → playful (graceful deflect) |

---

## Component 3 — LLM Classifier (Call 1)

**File:** `classifier.py` | **Function:** `classify(user_input, state) → str`

- Minimal focused prompt: current topic + stage + user message
- Output: JSON `{"category": "..."}` — one of:
  - `demonstrates_understanding`
  - `expresses_confusion`
  - `insightful_response`
  - `clarifying_question`
  - `minimal_evasive`
  - `off_topic_anachronistic`
- Model: `claude-haiku-4-5-20251001` (fast, cheap, structured output)
- Parse JSON; fallback to `minimal_evasive` on error

---

## Component 4 — Response Generator (Call 2)

**File:** `responder.py` | **Function:** `generate_response(user_input, state, classification, rag_chunks) → str`

Prompt assembles:
1. Sun Tzu system persona (loaded from `Sun Tzu Persona.txt`)
2. Current state (topic, stage, tone)
3. Classification result
4. RAG context (top 3 chunks, queried by `topic + stage`)
5. Last 6 turns of conversation history
6. User input

**Hard constraint in prompt:** "Respond in character as Sun Tzu. Maximum 5 sentences. Do not use bullet points."

**Model:** `claude-sonnet-4-6`

**Off-topic/anachronistic handling:** Sun Tzu deflects with gracious composure, acknowledges the curiosity, and steers back to The Art of War. If asked directly whether he is real, he clarifies he is a simulation — the original has long since passed.

---

## Component 5 — Flask App

**File:** `app.py`

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Serve index.html; initialize state (shi, introduction, warm) |
| `/chat` | POST | Body: `{message}`; classify → transition → RAG → generate; return `{response, state, completed_topics}` |
| `/new_game` | POST | Reset state |
| `/revisit/<topic>` | GET | Jump to a completed topic at introduction stage |

**Session:** `ConvState` stored as JSON in Flask session.

**End-of-conversation:** Once all 4 topics reach `resolution`, the UI offers "Revisit a topic" or "Say farewell." Farewell triggers a final in-character goodbye from Sun Tzu, then a closing quote screen.

---

## Component 6 — Frontend (Visual Novel Style)

**Files:** `templates/index.html`, `static/style.css`, `static/game.js`, `static/suntzu_sprite.css`

### UI Layout
```
┌─────────────────────────────────────────────────────┐
│  [Topic breadcrumb]            [Stage / Tone badge] │
├─────────────────────────────────────────────────────┤
│                                                     │
│         [Sun Tzu pixel statue — center]             │
│         [Animated eyebrows — CSS overlays]          │
│                                                     │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │  Sun Tzu: "..." (typewriter dialogue box)     │  │
│  └───────────────────────────────────────────────┘  │
│  [User input field]                    [Send btn]   │
└─────────────────────────────────────────────────────┘
```

### Sun Tzu Sprite
- CSS pixel-art of his famous statue (SVG or CSS box-shadow mosaic)
- Two eyebrow elements as CSS overlays with `@keyframes` per tone:
  - `warm` → neutral, relaxed
  - `probing` → one raised
  - `delighted` → both raised, slight tilt
  - `skeptical` → furrowed
  - `disappointed` → drooped inner corners
  - `playful` → asymmetric raise

### Style
- Font: Press Start 2P
- Color palette: dark ink / aged parchment
- Dialogue box: typewriter character-by-character animation
- End screen: fade to black + final Sun Tzu quote

---

## Incremental Development Order

1. **RAG MVP** — `rag_mvp.py`: ingest 5 chunks, query, print
2. **Full ingest** — `ingest.py`: entire Art of War into ChromaDB
3. **State machine** — `state_machine.py`: dataclass, transition logic
4. **Classifier** — `classifier.py`: Haiku LLM call, JSON parse
5. **Responder** — `responder.py`: Sonnet LLM call, full prompt
6. **Flask skeleton** — `app.py` + bare HTML: `/chat` works via curl
7. **Visual novel UI** — sprite, eyebrows, typewriter, parchment style
8. **End-of-conversation flow** — revisit / farewell / closing screen
9. **Polish** — tone badges, smooth transitions, ambient feel

---

## Key Design Decisions

- **Chunk size:** ~200 tokens, 20-token overlap — specific enough for RAG, enough context for meaning
- **RAG query:** `topic_id + " " + stage` (e.g. `"foreknowledge examination"`)
- **Two LLM calls always separate** — Haiku classifies (fast/cheap), Sonnet generates (quality)
- **5-sentence cap** enforced in both system prompt and user prompt
- **API key** in `.env`, loaded via `python-dotenv`; `.gitignore` covers `.env` and `chroma_db/`
- **Persona string** loaded once at startup as a module-level constant

---

## Verification Checklist

- [ ] `python ingest.py` → ChromaDB collection with 100+ entries
- [ ] `python rag_mvp.py` → relevant chunks returned for test queries
- [ ] `curl POST /chat` with "What is Shi?" → two LLM calls fire, ≤5 sentence response
- [ ] Browser smoke test: full 4-topic conversation, eyebrows animate per tone
- [ ] Off-topic test ("Tell me about the internet") → graceful deflection, stays in character
- [ ] Farewell flow: all topics resolvable, goodbye screen renders
