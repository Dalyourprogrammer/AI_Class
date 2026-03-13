"""
classifier.py — LLM Call 1: classify user input into a fixed category.
Uses gpt-4o-mini for speed and cost efficiency.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from state_machine import ConvState

load_dotenv()

_client = None

CATEGORIES = [
    "demonstrates_understanding",
    "expresses_confusion",
    "insightful_response",
    "clarifying_question",
    "applied_question",
    "minimal_evasive",
    "off_topic_anachronistic",
    "insulted",
    "flirted",
    "greeting_casual",
]

SYSTEM_PROMPT = (
    "You are a text classifier for a philosophical conversation app. "
    "Your only job is to classify a student's response into one of these exact categories:\n"
    "- demonstrates_understanding: student shows they grasp the concept\n"
    "- expresses_confusion: student is confused or lost\n"
    "- insightful_response: student offers a surprising or deep insight\n"
    "- clarifying_question: student asks a genuine question about the topic\n"
    "- applied_question: student asks how the teaching applies to a real scenario, "
    "or asks a personal question about Sun Tzu himself (his life, battles, experience, opinions)\n"
    "- minimal_evasive: student gives a short, vague, or evasive answer\n"
    "- off_topic_anachronistic: strange, weird, or completely off-topic message\n"
    "- insulted: student is rude, disrespectful, or insulting toward Sun Tzu\n"
    "- flirted: student is flirting, making romantic or inappropriate advances\n"
    "- greeting_casual: student is greeting, saying hello, making small talk, "
    "or offering a social pleasantry (e.g. 'hi', 'thanks', 'good morning', 'how are you')\n"
    "\nRespond with only valid JSON in this format: {\"category\": \"<category_name>\"}\n"
    "No explanation, no extra text."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def classify(user_input: str, state: ConvState) -> str:
    """Classify user input. Returns one of the CATEGORIES strings."""
    prompt = (
        f"Current topic: {state.topic}\n"
        f"Current stage: {state.stage}\n"
        f"Student's message: {user_input}"
    )

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=30,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        category = parsed.get("category", "")
        if category in CATEGORIES:
            return category
    except Exception:
        pass

    return "minimal_evasive"  # safe fallback
