import discord
from discord.ext import commands
import logging
from database import get_npc_status, get_player, get_current_day, check_and_award_interrogation_bonus, is_murder_active
from ollama_client import generate_npc_reply

logger = logging.getLogger("NpcCog")

CHANNEL_TO_NPC = {
    "the-kitchen-and-pantry": "gable",
    "the-carriage-house": "angus",
    "the-radio-room": "higgins",
    "the-grand-parlor": "giles",
}

NPC_TRIGGER_WORDS = {
    "gable": ["gable", "mrs. gable", "mrs gable", "cook"],
    "angus": ["angus", "old angus", "groundskeeper", "mechanic"],
    "higgins": ["higgins", "constable", "constable higgins", "police", "radio"],
    "giles": ["giles", "butler", "steward"]
}

BONUS_CANDLE_MESSAGES = {
    "gable": "\n\n🕯️ *[Mrs. Gable presses a fresh tallow candle into your hand: 'Here, dearie—take this from the larder box. You'll need it in the drafty halls tonight!'] (+1 Candle Added to your supply)*",
    "angus": "\n\n🕯️ *[Old Angus tosses you an extra lantern wick: 'Aye... at least someone in this house is asking proper questions. Don't go burning the place down.'] (+1 Candle Added to your supply)*",
    "higgins": "\n\n🕯️ *[Constable Higgins crackles over the wire: 'Procedural cooperation acknowledged. Keep this emergency flare in reserve.'] (+1 Candle Added to your supply)*",
    "giles": "\n\n🕯️ *[Giles retrieves a long silver taper from his waistcoat: 'For your diligence in estate inquiries, pray accept this additional candle for your rounds.'] (+1 Candle Added to your supply)*"
}

class NpcCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        # Check triggers:
        # 1. Bot is @mentioned
        # 2. User replied to a bot message
        # 3. User mentioned NPC name/role in the channel
        # 4. Message ends in a question mark in that NPC's dedicated room
        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference and 
            message.reference.resolved and 
            message.reference.resolved.author.id == self.bot.user.id
        )
        content_lower = message.content.lower()
        has_npc_name = any(trigger in content_lower for trigger in NPC_TRIGGER_WORDS.get(npc_id, []))
        is_direct_question = ("?" in message.content and channel_name in CHANNEL_TO_NPC)

        if not (is_mentioned or is_reply_to_bot or has_npc_name or is_direct_question):
            return

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
        npc_display_name = npc_status["name"] if npc_status else "Giles"

        async with message.channel.typing():
            murder_active = is_murder_active()
            reply_text = await generate_npc_reply(npc_id, clean_prompt, speaker_name, recent_messages, is_murder_active=murder_active)

        # Check and award interrogation bonus (+1 candle once per day)
        current_day = get_current_day()
        bonus_awarded = check_and_award_interrogation_bonus(message.author.id, current_day)
        if bonus_awarded:
            bonus_flavor = BONUS_CANDLE_MESSAGES.get(npc_id, BONUS_CANDLE_MESSAGES["giles"])
            reply_text += bonus_flavor

        await message.reply(f"**{npc_display_name}:** {reply_text}")

async def setup(bot: commands.Bot):
    await bot.add_cog(NpcCog(bot))
