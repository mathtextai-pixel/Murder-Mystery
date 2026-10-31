import discord
from discord.ext import commands
import logging
import time
from database import get_npc_status, get_player, get_current_day, check_and_award_interrogation_bonus, is_murder_active
from data.prompts import evaluate_interrogation_state
from cogs.search_view import send_testimony_unlock_dm
from ollama_client import generate_npc_reply

logger = logging.getLogger("NpcCog")

CHANNEL_TO_NPC = {
    "the-kitchen-and-pantry": "gable",
    "the-carriage-house": "angus",
    "the-wine-cellar": "angus",
    "the-radio-room": "higgins",
    "the-grand-parlor": "giles",
    "the-study": "abernathy",
}

NPC_TRIGGER_WORDS = {
    "gable": ["gable", "mrs. gable", "mrs gable", "cook", "housekeeper", "ma'am"],
    "angus": ["angus", "old angus", "groundskeeper", "mechanic", "scotsman"],
    "higgins": ["higgins", "constable", "constable higgins", "police", "radio", "officer"],
    "giles": ["filarello", "giles", "butler", "steward"],
    "abernathy": ["abernathy", "doctor", "doc", "physician", "coroner", "dr abernathy", "dr. abernathy", "examiner"]
}

CONVERSATION_PHRASES = (
    "tell me", "show me", "explain", "look at", "check", "examine", "inspect",
    "what", "where", "who", "how", "why", "when", "did you", "do you", "have you",
    "can you", "could you", "would you", "will you", "is there", "are there",
    "were there", "was there", "i think", "i found", "i saw", "hello", "hi ",
    "hey", "good evening", "good morning", "pardon", "excuse me"
)

BONUS_CANDLE_MESSAGES = {
    "gable": "\n\n🕯️ *[Mrs. Gable presses a fresh tallow candle into your hand: 'Here, dearie—take this from the larder box. You'll need it in the drafty halls tonight!'] (+1 Candle Added to your supply)*",
    "angus": "\n\n🕯️ *[Old Angus tosses you an extra lantern wick: 'Aye... at least someone in this house is asking proper questions. Don't go burning the place down.'] (+1 Candle Added to your supply)*",
    "higgins": "\n\n🕯️ *[Constable Higgins crackles over the wire: 'Procedural cooperation acknowledged. Keep this emergency flare in reserve.'] (+1 Candle Added to your supply)*",
    "giles": "\n\n🕯️ *[Filarello retrieves a slender silver taper with an understated flick of his wrist: 'For your diligence—or perhaps morbid curiosity. Do try not to set the drapes ablaze.'] (+1 Candle Added to your supply)*",
    "abernathy": "\n\n🕯️ *[Dr. Abernathy adjusts his spectacles and hands you a small brass inspection lamp from his black leather bag: 'Here—take this surgical lamp. If you are examining dark corners of this house, you will need proper illumination.'] (+1 Candle Added to your supply)*"
}

class NpcCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Maps (channel_id, user_id) -> unix timestamp of last NPC interaction
        self.active_conversations: dict[tuple[int, int], float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot's own messages or DMs
        if message.author.bot or message.guild is None:
            return

        channel_name = message.channel.name
        npc_id = CHANNEL_TO_NPC.get(channel_name)
        if not npc_id:
            # If in another room, default to Giles only if Giles is specifically mentioned
            content_lower = message.content.lower()
            if any(w in content_lower for w in NPC_TRIGGER_WORDS["giles"]) or (self.bot.user in message.mentions):
                npc_id = "giles"
            else:
                return

        # Ignore messages where a player is explicitly @mentioning another human player (without @mentioning the bot)
        mentions_other_human = any(not m.bot for m in message.mentions) and (self.bot.user not in message.mentions)
        if mentions_other_human:
            return

        # Check triggers:
        # 1. Bot is @mentioned
        # 2. User replied to a bot message
        # 3. User mentioned NPC name/role in the channel
        # 4. Message contains '?' in that NPC's dedicated room
        # 5. User is within an active 3-minute conversation window with that room's NPC
        # 6. In dedicated NPC rooms (excluding Grand Parlor social chat), message starts with/contains conversational inquiry phrases
        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference and 
            message.reference.resolved and 
            message.reference.resolved.author.id == self.bot.user.id
        )
        content_lower = message.content.lower().strip()
        has_npc_name = any(trigger in content_lower for trigger in NPC_TRIGGER_WORDS.get(npc_id, []))
        is_direct_question = ("?" in message.content and channel_name in CHANNEL_TO_NPC)

        now = time.time()
        last_active = self.active_conversations.get((message.channel.id, message.author.id), 0.0)
        window_seconds = 120.0 if channel_name == "the-grand-parlor" else 180.0
        in_active_conversation = (now - last_active) <= window_seconds

        is_dedicated_npc_room = (channel_name in CHANNEL_TO_NPC and channel_name != "the-grand-parlor")
        is_conversational_prompt = is_dedicated_npc_room and (
            content_lower.startswith(CONVERSATION_PHRASES) or
            any(p in content_lower for p in ("tell me", "show me", "let me see", "what about", "how about"))
        )

        if not (is_mentioned or is_reply_to_bot or has_npc_name or is_direct_question or in_active_conversation or is_conversational_prompt):
            return

        # Refresh active conversation window for this player in this room!
        self.active_conversations[(message.channel.id, message.author.id)] = now

        # Check NPC shift status
        npc_status = get_npc_status(npc_id)
        if npc_status and not npc_status["is_on_shift"]:
            away_msg = npc_status["away_message"] or "The staff member is currently off duty."
            await message.reply(f"*(The room is quiet. A handwritten slate reads: '{away_msg}')*")
            return

        # Clean text
        clean_prompt = message.clean_content.replace(f"@{self.bot.user.name}", "").strip()
        if not clean_prompt:
            clean_prompt = "Hello?"

        # Fetch recent channel messages for context
        recent_messages = []
        try:
            async for msg in message.channel.history(limit=6, before=message):
                if msg.content:
                    recent_messages.append({
                        "author": "bot" if msg.author.id == self.bot.user.id else msg.author.display_name,
                        "content": msg.clean_content
                    })
            recent_messages.reverse()
        except Exception as e:
            logger.error(f"Failed to fetch history: {e}")

        # Generate NPC dialogue using local Hermes 3
        speaker_name = message.author.display_name
        npc_display_name = npc_status["name"] if npc_status else "Filarello"

        async with message.channel.typing():
            murder_active = is_murder_active()
            directive, newly_unlocked = evaluate_interrogation_state(
                user_id=message.author.id,
                npc_id=npc_id,
                user_message=clean_prompt,
                murder_active=murder_active
            )
            reply_text = await generate_npc_reply(
                npc_id,
                clean_prompt,
                speaker_name,
                recent_messages,
                is_murder_active=murder_active,
                interrogation_directive=directive
            )

        if newly_unlocked:
            await send_testimony_unlock_dm(message.author, newly_unlocked)

        # Check and award interrogation bonus (+1 candle once per day)
        # ONLY if the murder is active AND the player asked a substantive investigative question!
        if murder_active:
            words = clean_prompt.split()
            investigative_keywords = {
                "murder", "killed", "dead", "body", "blood", "poison", "laudanum", "fracture",
                "skull", "fall", "stairs", "alibi", "weapon", "poker", "clock", "cellar",
                "crypt", "attic", "dumbwaiter", "will", "emerald", "ring", "barnaby", "finch",
                "secret", "where", "who", "why", "how", "when", "what", "saw", "heard",
                "suspicious", "tea", "wine", "port", "wire", "telephone", "search", "clue"
            }
            lower_words = {w.strip(".,!?\"'").lower() for w in words}
            is_substantive_inquiry = (
                len(words) >= 6 and ("?" in clean_prompt or bool(lower_words & investigative_keywords) or bool(newly_unlocked))
            )
            if is_substantive_inquiry:
                current_day = get_current_day()
                bonus_awarded = check_and_award_interrogation_bonus(message.author.id, current_day)
                if bonus_awarded:
                    bonus_flavor = BONUS_CANDLE_MESSAGES.get(npc_id, BONUS_CANDLE_MESSAGES["giles"])
                    reply_text += bonus_flavor

        await message.reply(f"**{npc_display_name}:** {reply_text}")

async def setup(bot: commands.Bot):
    await bot.add_cog(NpcCog(bot))
