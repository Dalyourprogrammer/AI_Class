"""
responder.py — LLM Call 2: generate Sun Tzu's in-character response.
Uses gpt-4o for quality.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from state_machine import ConvState, TOPICS

load_dotenv()

_client = None
_persona = None

PERSONA_PATH = os.path.join(os.path.dirname(__file__), "Sun Tzu Persona.txt")

TONE_INSTRUCTIONS = {
    "warm":        "Respond with gentle warmth and encouraging openness.",
    "probing":     "Respond with calm, penetrating questions to draw out deeper thought.",
    "delighted":   "Respond with visible delight and enthusiasm — the student has surprised you.",
    "skeptical":   "Respond with measured skepticism — probe their confidence carefully.",
    "disappointed":"Respond with quiet disappointment, but maintain patience and care.",
    "playful":     "Respond with light, dry humor — you are amused by the unexpected.",
}

STAGE_INSTRUCTIONS = {
    "introduction": "Introduce this topic. Orient the student. Set the stage.",
    "examination":  "Probe the student's understanding. Ask a focused question.",
    "challenge":    "Introduce tension or a harder angle. Challenge their current view.",
    "resolution":   "Guide toward a conclusion or rest in productive uncertainty.",
}

OFF_TOPIC_INSTRUCTION = (
    "The student has asked something off-topic or anachronistic. "
    "Acknowledge it with gracious, dry humor, and gently steer back to the current topic. "
    "If asked whether you are the real Sun Tzu, clarify that you are a simulation — "
    "the original passed long ago — and return to the teaching."
)

INSULTED_INSTRUCTION = (
    "The student has been rude or insulting. Respond with complete calm — no anger, no farewell. "
    "In your own measured words, let them know you are patient and will simply wait here "
    "until they are ready to engage with sincerity and respect. "
    "Make clear the conversation remains open whenever they choose to return to it."
)

FLIRTED_INSTRUCTION = (
    "The student is flirting or making an inappropriate advance. "
    "Respond with unhurried composure — neither flattered nor offended. "
    "In your own words, let them know you are content to wait until they wish to speak "
    "of things that matter. Do not end the conversation — simply pause it with dignity."
)

OFF_TOPIC_WAIT_INSTRUCTION = (
    "The student has said something strange or completely off-topic. "
    "Acknowledge it gently with dry patience. In your own words, let them know "
    "you are in no hurry — you will wait here until they are ready to explore something meaningful together. "
    "Do not dismiss them; keep the door open."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _get_persona() -> str:
    global _persona
    if _persona is None:
        with open(PERSONA_PATH, "r", encoding="utf-8") as f:
            _persona = f.read()
    return _persona


def generate_response(
    user_input: str,
    state: ConvState,
    classification: str,
    rag_chunks: list[str],
) -> str:
    """Generate Sun Tzu's next response in character."""
    persona = _get_persona()
    topic_desc = TOPICS.get(state.topic, state.topic)
    tone_instr = TONE_INSTRUCTIONS.get(state.tone, "")
    stage_instr = STAGE_INSTRUCTIONS.get(state.stage, "")

    if classification == "off_topic_anachronistic":
        behavior = OFF_TOPIC_WAIT_INSTRUCTION
    elif classification == "insulted":
        behavior = INSULTED_INSTRUCTION
    elif classification == "flirted":
        behavior = FLIRTED_INSTRUCTION
    else:
        behavior = f"Stage guidance: {stage_instr}\nTone guidance: {tone_instr}"

    rag_section = ""
    if rag_chunks:
        rag_section = "Relevant passages from The Art of War (use these to inform your response):\n"
        rag_section += "\n---\n".join(rag_chunks)

    system = (
        f"{persona}\n\n"
        "You are Sun Tzu — a simulation of the ancient Chinese strategist. "
        "Speak in character at all times. "
        "If asked whether you are real, acknowledge you are a simulation; the original passed long ago.\n\n"
        f"Current topic: {topic_desc}\n"
        f"Current stage: {state.stage}\n"
        f"Current tone: {state.tone}\n\n"
        f"{behavior}\n\n"
        f"{rag_section}\n\n"
        "IMPORTANT CONSTRAINTS:\n"
        "- Maximum 5 sentences. No bullet points. No lists.\n"
        "- Speak as Sun Tzu directly to the student.\n"
        "- Be aphoristic, measured, and wise.\n"
        "- Do not break character."
    )

    # Build message history (last 6 turns)
    messages = [{"role": "system", "content": system}]
    for turn in state.history[-6:]:
        messages.append(turn)
    messages.append({"role": "user", "content": user_input})

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=200,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()
