import discord
import random
from database import (
    get_player, consume_token, record_player_clue, get_player_clues, get_npc_status, is_murder_active
)
from data.game_data import ROOM_POOLS, ROOM_ATMOSPHERES

ROOM_TO_NPC_INFO = {
    "kitchen": ("gable", "Mrs. Gable (Head Cook)", "Present by the roaring range", "Away tending to the linens in the East Wing"),
    "carriage": ("angus", "Old Angus (Groundskeeper)", "Present at the workbench cleaning motor parts", "Away checking the perimeter fences"),
    "radio": ("higgins", "Constable Higgins (Radio)", "Radio signal clear; listening over the airwaves", "Static squall interference; signal lost"),
    "study": ("abernathy", "Dr. Abernathy (Parish Physician)", "Present examining the crime scene with his medical bag", "Away consulting medical texts in the library"),
    "library": (None, None, None, None),
    "conservatory": (None, None, None, None),
    "dining": (None, None, None, None),
    "cellar": ("angus", "Old Angus (Groundskeeper)", "Present tending the coal furnace", "Away out on the grounds"),
    "bedroom": (None, None, None, None),
    "attic": (None, None, None, None),
    "crypt": (None, None, None, None),
}

def build_room_embed(room_id: str, room_name: str) -> discord.Embed:
    description = ROOM_ATMOSPHERES.get(room_id, "A shadow-draped chamber in Ravenscroft Hall.")
    
    embed = discord.Embed(
        title=f"🏰 {room_name}",
        description=f"*{description}*",
        color=0x2F4F4F
    )
    
    npc_info = ROOM_TO_NPC_INFO.get(room_id)
    if npc_info and npc_info[0]:
        npc_id, name, on_txt, off_txt = npc_info
        status = get_npc_status(npc_id)
        if status and status["is_on_shift"]:
            occupancy_str = f"🟢 **{name}** — *[{on_txt}]*"
        else:
            occupancy_str = f"🔴 **VACANT** — *[{off_txt}]*"
    else:
        occupancy_str = "⚪ **UNATTENDED** — *Quiet; only the sound of rain.*"

    embed.add_field(name="👤 CURRENT OCCUPANCY", value=occupancy_str, inline=False)
    embed.set_footer(text="Tap below to light a candle and search this chamber for evidence.")
    return embed

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

        if not is_murder_active():
            await interaction.response.send_message(
                "🕯️ **Searches Forbidden Before Dinner.**\n"
                "Lord Julian is currently resting upstairs and has strictly forbidden guests from prying through estate drawers.\n"
                "Please converse with your fellow guests in `#the-grand-parlor` until the evening bells.",
                ephemeral=True
            )
            return

        if player["tokens_remaining"] <= 0:
            await interaction.response.send_message(
                "🕯️ **Your candles have burned down to the wick.**\n"
                "You have no search candles remaining today. Giles will replenish them tomorrow morning at 9:00 AM.\n"
                "*(Hint: Interrogating an on-shift staff member can earn you a bonus candle!)*",
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

            # Permanent Clue Card in DM
            try:
                dm = await interaction.user.create_dm()
                dm_card = discord.Embed(
                    title=f"📁 Case File: {title}",
                    description=f"**Chamber:** {self.room_id.replace('-', ' ').title()}\n\n{text}",
                    color=0xD4AF37
                )
                dm_card.set_footer(text="Saved permanently to your personal detective dossier.")
                await dm.send(embed=dm_card)
            except Exception:
                pass

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

            # Permanent Clue Card in DM
            try:
                dm = await interaction.user.create_dm()
                dm_card = discord.Embed(
                    title=f"📜 Observation: {title}",
                    description=f"**Chamber:** {self.room_id.replace('-', ' ').title()}\n\n{text}",
                    color=0x708090
                )
                dm_card.set_footer(text="Saved permanently to your personal detective dossier.")
                await dm.send(embed=dm_card)
            except Exception:
                pass

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
