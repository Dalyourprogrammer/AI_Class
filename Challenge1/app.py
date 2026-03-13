"""
app.py — Flask web application for the Sun Tzu Conversation Simulator.
Run: python app.py
"""

import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from state_machine import ConvState, transition, next_topic, all_done, TOPICS, TOPIC_ORDER
from classifier import classify
from responder import generate_response
from rag import query_rag

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Keywords that signal each topic is being discussed
TOPIC_KEYWORDS = {
    "shi":     ["shi", "strategic advantage", "momentum", "potential energy", "positioning", "potential force"],
    "zhi":     ["zhi", "foreknowledge", "intelligence", "knowing before", "spies", "information", "foreknow"],
    "bian":    ["bian", "adaptability", "adapt", "variation", "flexibility", "fluid", "variations", "flexible"],
    "quanmou": ["quanmou", "holistic planning", "deliberation", "preparation", "deliberate", "whole plan"],
}

def detect_topic(text: str) -> str | None:
    """Return the topic ID if any topic keywords appear in text, else None."""
    lower = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return topic
    return None


def get_state() -> ConvState:
    if "state" not in session:
        session["state"] = ConvState().to_json()
    return ConvState.from_json(session["state"])


def save_state(state: ConvState):
    session["state"] = state.to_json()


def _opening_message(state: ConvState) -> str:
    """Generate the opening message for a topic without user input."""
    rag_chunks = query_rag(f"{state.topic} introduction strategy", n_results=2)
    return generate_response(
        user_input="[Open the conversation. Briefly introduce this topic and what it means, then ask the student a question to draw them in.]",
        state=state,
        classification="demonstrates_understanding",
        rag_chunks=rag_chunks,
    )


@app.route("/")
def index():
    # Fresh state on every page load
    state = ConvState()
    opening = _opening_message(state)
    state.history.append({"role": "assistant", "content": opening})
    save_state(state)
    return render_template("index.html", opening=opening, state=state.to_dict())


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "empty message"}), 400

    state = get_state()

    # ── Call 1: Classify ──────────────────────────────────────────────────
    classification = classify(user_input, state)

    # ── Transition state ──────────────────────────────────────────────────
    state = transition(state, classification)

    # ── RAG query ─────────────────────────────────────────────────────────
    rag_query = f"{state.topic} {state.stage}"
    rag_chunks = query_rag(rag_query, n_results=3)

    # ── Call 2: Generate response ─────────────────────────────────────────
    state.history.append({"role": "user", "content": user_input})
    response_text = generate_response(user_input, state, classification, rag_chunks)
    state.history.append({"role": "assistant", "content": response_text})

    # ── Auto-advance topic if resolution reached ───────────────────────────
    topic_advanced = False
    if state.stage == "resolution" and state.topic in state.completed_topics:
        nxt = next_topic(state)
        if nxt and nxt != state.topic:
            state.topic = nxt
            state.stage = "introduction"
            state.tone = "warm"
            topic_advanced = True

    save_state(state)

    # Detect which topic is being mentioned (user input or Sun Tzu's reply)
    mentioned_topic = detect_topic(user_input) or detect_topic(response_text)

    return jsonify({
        "response": response_text,
        "classification": classification,
        "state": state.to_dict(),
        "all_done": all_done(state),
        "topic_advanced": topic_advanced,
        "mentioned_topic": mentioned_topic,
    })


@app.route("/farewell", methods=["POST"])
def farewell():
    state = get_state()
    farewell_text = generate_response(
        user_input="[The student wishes to end the conversation.]",
        state=state,
        classification="demonstrates_understanding",
        rag_chunks=[],
    )
    session.clear()
    return jsonify({"farewell": farewell_text})


@app.route("/revisit/<topic>", methods=["POST"])
def revisit(topic):
    state = get_state()
    if topic not in state.completed_topics:
        return jsonify({"error": "topic not yet completed"}), 400

    state.topic = topic
    state.stage = "introduction"
    state.tone = "warm"

    rag_chunks = query_rag(f"{topic} introduction", n_results=2)
    opening = generate_response(
        user_input=f"[Revisit the topic of {topic}.]",
        state=state,
        classification="demonstrates_understanding",
        rag_chunks=rag_chunks,
    )
    state.history.append({"role": "assistant", "content": opening})
    save_state(state)

    return jsonify({"response": opening, "state": state.to_dict()})


@app.route("/new_game", methods=["POST"])
def new_game():
    session.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
