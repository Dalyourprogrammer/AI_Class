"""
state_machine.py — Topic × Stage × Tone state and transition logic.
"""

from dataclasses import dataclass, field, asdict
import json

# ── Topics ──────────────────────────────────────────────────────────────────
TOPICS = {
    "shi":      "Strategic Advantage — momentum, positioning, potential energy",
    "zhi":      "Foreknowledge — intelligence, knowing before acting",
    "bian":     "Adaptability — variation, fluidity, responding to change",
    "quanmou":  "Holistic Planning — deliberation, preparation, whole-picture strategy",
}

TOPIC_ORDER = ["shi", "zhi", "bian", "quanmou"]

# Topic graph edges (conceptually adjacent topics for natural flow)
TOPIC_GRAPH = {
    "shi":     ["bian", "quanmou"],
    "zhi":     ["quanmou", "shi"],
    "bian":    ["shi", "quanmou"],
    "quanmou": ["zhi", "bian"],
}

# ── Stages ───────────────────────────────────────────────────────────────────
STAGES = ["introduction", "examination", "challenge", "resolution"]

# ── Tones ────────────────────────────────────────────────────────────────────
TONES = ["warm", "probing", "delighted", "skeptical", "disappointed", "playful"]

# ── State ────────────────────────────────────────────────────────────────────
@dataclass
class ConvState:
    topic: str = "shi"
    stage: str = "introduction"
    tone: str = "warm"
    turn_count: int = 0
    history: list = field(default_factory=list)          # [{role, content}]
    completed_topics: list = field(default_factory=list)
    consecutive_evasive: int = 0                         # track evasive streak

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ConvState":
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, s: str) -> "ConvState":
        return cls.from_dict(json.loads(s))


# ── Transitions ───────────────────────────────────────────────────────────────
def _advance_stage(state: ConvState, skip: bool = False) -> str:
    idx = STAGES.index(state.stage)
    if skip and idx < len(STAGES) - 2:
        return STAGES[idx + 2]
    if idx < len(STAGES) - 1:
        return STAGES[idx + 1]
    return state.stage  # already at resolution


def _hold_or_retreat_stage(state: ConvState) -> str:
    idx = STAGES.index(state.stage)
    if idx > 0:
        return STAGES[idx - 1]
    return state.stage


def transition(state: ConvState, classification: str) -> ConvState:
    """Return a new ConvState after applying classification-driven transitions."""
    new_stage = state.stage
    new_tone = state.tone
    new_evasive = 0

    if classification == "demonstrates_understanding":
        new_stage = _advance_stage(state)
        new_tone = "warm" if state.tone != "delighted" else "delighted"

    elif classification == "insightful_response":
        new_stage = _advance_stage(state, skip=True)
        new_tone = "delighted"

    elif classification == "expresses_confusion":
        new_stage = _hold_or_retreat_stage(state)
        new_tone = "probing"

    elif classification == "clarifying_question":
        # hold stage, become warm/welcoming
        new_tone = "warm"

    elif classification == "minimal_evasive":
        new_evasive = state.consecutive_evasive + 1
        new_tone = "disappointed" if new_evasive >= 2 else "probing"

    elif classification == "off_topic_anachronistic":
        new_tone = "playful"

    elif classification == "insulted":
        new_tone = "skeptical"   # composed but firm

    elif classification == "flirted":
        new_tone = "probing"     # redirects with patience

    # Mark topic complete if we've reached resolution
    completed = list(state.completed_topics)
    if new_stage == "resolution" and state.topic not in completed:
        completed.append(state.topic)

    return ConvState(
        topic=state.topic,
        stage=new_stage,
        tone=new_tone,
        turn_count=state.turn_count + 1,
        history=state.history,
        completed_topics=completed,
        consecutive_evasive=new_evasive,
    )


def next_topic(state: ConvState) -> str | None:
    """Return the next unvisited topic, or None if all done."""
    for t in TOPIC_ORDER:
        if t not in state.completed_topics:
            return t
    return None


def all_done(state: ConvState) -> bool:
    return set(TOPIC_ORDER).issubset(set(state.completed_topics))
