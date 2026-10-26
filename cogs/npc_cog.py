import discord
from discord.ext import commands
import logging
from database import get_npc_status, get_player
from ollama_client import generate_npc_reply

logger = logging.getLogger("NpcCog")

CHANNEL_TO_NPC = {
    "the-kitchen-and-pantry": "gable",
    "the-carriage-house": "angus",
    "the-radio-room": "higgins",
    "the-grand-parlor": "giles",
}

class NpcCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot's own messages or DMs (DMs are handled by intake)
        if message.author.bot or message.guild is None:
            return

        # Check if bot was mentioned or if user replied to bot
        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = (
            message.reference and 
            message.reference.resolved and 
            message.reference.resolved.author.id == self.bot.user.id
        )

        if not (is_mentioned or is_reply_to_bot):
            return

        channel_name = message.channel.name
        npc_id = CHANNEL_TO_NPC.get(channel_name, "giles")

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
            reply_text = await generate_npc_reply(npc_id, clean_prompt, speaker_name, recent_messages)

        await message.reply(f"**{npc_display_name}:** {reply_text}")

async def setup(bot: commands.Bot):
    await bot.add_cog(NpcCog(bot))
