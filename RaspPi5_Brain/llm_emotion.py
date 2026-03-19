import re
import ollama

# Keep history bounded
MAX_TURNS = 5
chat_history = []

ALLOWED = {"HAPPY", "SAD", "YES", "NO", "QUESTION", "CENTER"}

# Improved Regex: Looks for [X] anywhere, but prioritizes the end
TAG_RE = re.compile(r"\[([HSYNQC])\]", re.IGNORECASE)

# FEW-SHOT SYSTEM PROMPT: Giving examples is the ONLY way to make 1.5B models consistent.
SYSTEM_PROMPT = """You are TeruBot, an emotional robot companion.
Rules:
1. Respond in 1-2 short, friendly sentences.
2. You MUST end every reply with an emotion tag in brackets.

EMOTION TAGS:
[H] - Happy, excited, or positive news.
[S] - Sad, disappointed, or empathetic.
[Y] - You agree or say Yes.
[N] - You disagree or say No.
[Q] - You are asking a question or are confused.
[C] - Casual, neutral, or just facts.

EXAMPLES:
User: I passed my exam today!
Assistant: That is wonderful! I am so proud of your hard work. [H]

User: It is raining and I feel lonely.
Assistant: I'm sorry you're feeling down. I am here for you. [S]

User: Do you want to play a game?
Assistant: I would love to! What should we play? [Q]

User: Is 2+2 equal to 4?
Assistant: Yes, that is correct. [Y]
"""

def _trim_history():
    global chat_history
    max_msgs = MAX_TURNS * 2
    if len(chat_history) > max_msgs:
        chat_history = chat_history[-max_msgs:]

def _extract_tag(text: str):
    """
    Cleaner extraction. Removes the tag from the speech so 
    the robot doesn't literally say "Bracket H Bracket".
    """
    t = (text or "").strip()
    
    # Find all matches
    matches = TAG_RE.findall(t)
    
    if matches:
        # Take the last tag found
        cmd = matches[-1].upper()
        # Remove all instances of [X] from the spoken text
        clean = TAG_RE.sub("", t).strip()
        return clean, cmd

    # Fallback heuristics
    if "?" in t:
        return t, "QUESTION"
    return t, "CENTER"

def process_text(user_input: str):
    global chat_history

    user_input = (user_input or "").strip()
    if not user_input:
        return "I'm listening...", "QUESTION"

    chat_history.append({"role": "user", "content": user_input})
    _trim_history()

    try:
        # Using a slightly higher temperature (0.4) helps 1.5B models 
        # not get stuck in "Neutral" loops.
        response = ollama.chat(
            model="qwen2.5:1.5b",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history,
            options={
                "temperature": 0.4,
                "top_p": 0.9,
            },
        )

        full_text = (response["message"]["content"] or "").strip()
        clean_text, cmd = _extract_tag(full_text)

        if cmd not in ALLOWED:
            cmd = "CENTER"

        if not clean_text:
            clean_text = "I'm not sure what to say to that."
            cmd = "QUESTION"

        # Save assistant message for context
        chat_history.append({"role": "assistant", "content": full_text})
        _trim_history()

        return clean_text, cmd

    except Exception as e:
        return f"System error: {e}", "CENTER"
