import aiohttp
import logging
from config import OLLAMA_HOST, OLLAMA_MODEL
from data.prompts import INTAKE_VALIDATOR_PROMPT, NPC_PROMPTS, REVEAL_PROMPT

logger = logging.getLogger("OllamaClient")

async def chat_completion(messages: list, system_prompt: str = "") -> str:
    url = f"{OLLAMA_HOST}/api/chat"
    
    formatted_messages = []
    if system_prompt:
        formatted_messages.append({"role": "system", "content": system_prompt})
    formatted_messages.extend(messages)
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": formatted_messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 400
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("message", {}).get("content", "").strip()
                else:
                    text = await resp.text()
                    logger.error(f"Ollama API error {resp.status}: {text}")
                    return "Giles clears his throat in silence. (AI service error)"
    except Exception as e:
        logger.error(f"Failed to communicate with Ollama: {e}")
        return "Giles stares forward impassively, lost in thought. (Local AI connection failed)"

async def validate_and_respond_intake(step: int, user_text: str, history: list) -> tuple:
    """
    Returns (is_accepted: bool, reply_text: str)
    """
    system = INTAKE_VALIDATOR_PROMPT.format(step=step)
    messages = list(history)
    messages.append({"role": "user", "content": user_text})
    
    raw_response = await chat_completion(messages, system_prompt=system)
    
    if "[ACCEPT]" in raw_response:
        clean_text = raw_response.replace("[ACCEPT]", "").strip()
        return True, clean_text
    elif "[REJECT]" in raw_response:
        clean_text = raw_response.replace("[REJECT]", "").strip()
        return False, clean_text
    else:
        # Default fallback to accept if the model didn't use tags but gave a good answer
        return True, raw_response

async def generate_npc_reply(npc_id: str, user_text: str, speaker_name: str, recent_channel_messages: list) -> str:
    system = NPC_PROMPTS.get(npc_id, NPC_PROMPTS["giles"])
    
    messages = []
    for msg in recent_channel_messages[-4:]:
        messages.append({"role": "user" if msg["author"] != "bot" else "assistant", "content": f"{msg['author']}: {msg['content']}"})
    
    messages.append({"role": "user", "content": f"{speaker_name}: {user_text}"})
    
    return await chat_completion(messages, system_prompt=system)

async def generate_custom_player_dossier(player_name: str, q1: str, q2: str, q3: str) -> dict:
    """
    Dynamically weaves the player's freely chosen profession, item, and dispute into
    a custom title, dirty secret, and secret objective.
    """
    system_prompt = (
        "You are the master Gothic storyteller of Ravenscroft Hall.\n"
        "A player has just created their own background during their intake interview.\n"
        "Your task: Weave their freely chosen profession, personal item, and conflict into a cohesive character profile.\n"
        "CRITICAL RULES:\n"
        "- TITLE: Combine their name with their freely chosen trade/profession (e.g. '[Name], The [Profession]').\n"
        "- SECRET: A 1-2 sentence suspicious act they committed between 10:00 and 11:30 PM involving their trade or item that looks incriminating, BUT they did NOT kill Julian.\n"
        "- GOAL: A 1-sentence objective for what they must hide or accomplish during the 14 days.\n\n"
        "FORMAT EXACTLY AS:\n"
        "TITLE: <title>\n"
        "SECRET: <secret>\n"
        "GOAL: <goal>"
    )
    user_prompt = (
        f"Player Name: {player_name}\n"
        f"Profession & Relation: {q1}\n"
        f"Personal Item: {q2}\n"
        f"Conflict/Tension: {q3}\n\n"
        f"Generate the custom dossier now."
    )
    messages = [{"role": "user", "content": user_prompt}]
    raw = await chat_completion(messages, system_prompt=system_prompt)
    
    title = f"{player_name}, The Mysterious Guest"
    secret = "You were seen wandering the upper corridors near Julian's study shortly before midnight."
    goal = "Keep anyone from discovering why you were wandering the halls."
    
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("SECRET:"):
            secret = line.replace("SECRET:", "").strip()
        elif line.startswith("GOAL:"):
            goal = line.replace("GOAL:", "").strip()
            
    return {"title": title, "secret": secret, "goal": goal}

async def generate_grand_reveal_speech(ballots_summary: str) -> str:
    messages = [
        {"role": "user", "content": f"The guests have cast their final ballots:\n{ballots_summary}\n\nDeliver the grand finale monologue now."}
    ]
    return await chat_completion(messages, system_prompt=REVEAL_PROMPT)
