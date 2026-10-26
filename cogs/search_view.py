import discord
import random
from database import (
    get_player, consume_token, record_player_clue, get_player_clues
)
from data.game_data import ROOM_POOLS

class RoomSearchView(discord.ui.View):
    def __init__(self, room_id: str):
        super().__init__(timeout=None)
        self.room_id = room_id

    @discord.ui.button(label="🕯️ Search the Room", style=discord.ButtonStyle.secondary, custom_id="btn_search_room")
    async def search_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        player = get_player(user_id)
        
        if not player or player["interview_step"] < 4:
            await interaction.response.send_message(
                "You must complete your guest registration with Giles at `#reception-gates` before searching the estate.",
                ephemeral=True
            )
            return

        if player["tokens_remaining"] <= 0:
            await interaction.response.send_message(
                "🕯️ **Your candles have burned down to the wick.**\n"
                "You have no search candles remaining today. Giles will replenish them tomorrow morning at 9:00 AM.",
                ephemeral=True
            )
            return

        # Deduct token
        consume_token(user_id)
        tokens_left = player["tokens_remaining"] - 1

        # Determine clue pool
        room_data = ROOM_POOLS.get(self.room_id, ROOM_POOLS["study"])
        consecutive_empty = player["consecutive_empty"]

        # Check existing clues found by this player in this room
        found_clues = get_player_clues(user_id)
        found_titles = {c["clue_title"] for c in found_clues}

        available_majors = [c for c in room_data["major"] if c[0] not in found_titles]

        # Probability Roll: 40% major, 45% lore, 15% empty
        # Bad luck protection: if 3 consecutive non-majors, force major if available
        roll = random.random()
        force_major = (consecutive_empty >= 3 and len(available_majors) > 0)

        if (roll < 0.40 or force_major) and len(available_majors) > 0:
            clue = random.choice(available_majors)
            title, text = clue[0], clue[1]
            record_player_clue(user_id, self.room_id, title, text, is_major=True)
            
            embed = discord.Embed(
                title=f"🔍 Significant Discovery: {title}",
                description=text,
                color=0xD4AF37 # Victorian Gold
            )
            embed.set_footer(text=f"Only you can see this. | Candles remaining: {tokens_left}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif roll < 0.85:
            # Lore clue
            clue = random.choice(room_data["lore"])
            title, text = clue[0], clue[1]
            record_player_clue(user_id, self.room_id, title, text, is_major=False)

            embed = discord.Embed(
                title=f"📜 Observation: {title}",
                description=text,
                color=0x708090 # Slate Grey
            )
            embed.set_footer(text=f"Only you can see this. | Candles remaining: {tokens_left}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            # Empty / Atmosphere
            text = random.choice(room_data["empty"])
            record_player_clue(user_id, self.room_id, "Nothing of Note", text, is_major=False)

            embed = discord.Embed(
                title="🕯️ Dust & Shadows",
                description=text,
                color=0x2F4F4F # Dark Slate
            )
            embed.set_footer(text=f"Only you can see this. | Candles remaining: {tokens_left}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
