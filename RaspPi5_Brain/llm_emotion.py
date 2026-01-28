import ollama

# Memory management: only keep last 5 exchanges to keep the Pi fast
chat_history = []

def process_text(user_input):
    global chat_history
    
    if len(chat_history) > 5:
        chat_history.pop(0)

    chat_history.append({'role': 'user', 'content': user_input})

    # Strict System Prompt for hardware mapping
    system_prompt = """
    You are TeruBot. You control a physical robot.
    Every response MUST end with one of these tags:
    [H] - Happy/Good news
    [S] - Sad/Bad news
    [Y] - If the user asks you to say YES or if you agree
    [N] - If you say NO or disagree
    [Q] - If you are asking a question
    [C] - Neutral
    """

    try:
        response = ollama.chat(
            model='qwen2.5:1.5b',
            messages=[{'role': 'system', 'content': system_prompt}] + chat_history,
            options={"temperature": 0.3} # Lower temp = faster and more focused
        )
        
        full_text = response['message']['content'].strip()
        chat_history.append({'role': 'assistant', 'content': full_text})

        # --- SMART COMMAND DETECTION ---
        # We search specifically for your requested 'Y' and 'N' first
        cmd_code = 'C'
        text_upper = full_text.upper()
        
        if "[Y]" in text_upper or "YES" in user_input.upper(): cmd_code = 'Y'
        elif "[N]" in text_upper or "NO" in user_input.upper(): cmd_code = 'N'
        elif "[H]" in text_upper: cmd_code = 'H'
        elif "[S]" in text_upper: cmd_code = 'S'
        elif "[Q]" in text_upper or "?" in full_text: cmd_code = 'Q'

        # --- CLEAN TEXT ---
        clean_text = full_text.split('[')[0].strip() # Cut off everything after the bracket
        
        return clean_text, cmd_code
            
    except Exception as e:
        return f"Speed Error: {e}", 'C'
