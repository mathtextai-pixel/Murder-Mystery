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

async def generate_grand_reveal_speech(ballots_summary: str) -> str:
    messages = [
        {"role": "user", "content": f"The guests have cast their final ballots:\n{ballots_summary}\n\nDeliver the grand finale monologue now."}
    ]
    return await chat_completion(messages, system_prompt=REVEAL_PROMPT)
