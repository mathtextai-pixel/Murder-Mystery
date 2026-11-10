import discord
import random
from database import (
    get_player, consume_token, record_player_clue, get_player_clues, get_npc_status, is_murder_active,
    get_dynamic_room_clues
)
from data.game_data import ROOM_POOLS, ROOM_ATMOSPHERES, PRE_MURDER_ROOM_ATMOSPHERES
from data.prompts import evaluate_interrogation_state
from ollama_client import generate_npc_reply

CHANNEL_NAME_TO_ROOM_ID = {
    "the-study": "study",
    "the-library": "library",
    "the-conservatory": "conservatory",
    "the-dining-hall": "dining",
    "the-wine-cellar": "cellar",
    "julians-bedroom": "bedroom",
    "the-kitchen-and-pantry": "kitchen",
    "the-clocktower-attic": "attic",
    "the-carriage-house": "carriage",
    "the-family-crypt": "crypt",
    "the-radio-room": "radio",
    "the-grand-parlor": "parlor",
}

ROOM_TO_NPC_INFO = {
    "parlor": (
        "giles",
        "Filarello (Senior Steward)",
        "Present pouring aperitifs and appraising the room by the hearth",
        "Present maintaining dry decorum in the Grand Parlor",
        "Attending to estate matters in the West Wing"
    ),
    "kitchen": (
        "gable",
        "Mrs. Gable (Head Cook)",
        "Present preparing the Solstice dinner feast",
        "Present by the roaring range",
        "Away tending to the linens in the East Wing"
    ),
    "carriage": (
        "angus",
        "Old Angus (Groundskeeper)",
        "Present parking guest carriages out of the squall",
        "Present at the workbench cleaning motor parts",
        "Away checking the perimeter fences"
    ),
    "radio": (
        "higgins",
        "Constable Higgins (Radio)",
        "Broadcasting routine coastal storm warnings",
        "Radio signal clear; listening over the airwaves",
        "Static squall interference; signal lost"
    ),
    "study": (
        "abernathy",
        "Dr. Abernathy (Parish Physician)",
        "Present reviewing Lord Julian's medical charts by the hearth",
        "Present examining the crime scene with his medical bag",
        "Away consulting medical texts in the library"
    ),
    "library": (None, None, None, None, None),
    "conservatory": (None, None, None, None, None),
    "dining": (None, None, None, None, None),
    "cellar": (
        "angus",
        "Old Angus (Groundskeeper)",
        "Present stoking the coal furnace for the evening",
        "Present tending the coal furnace",
        "Away out on the grounds"
    ),
    "bedroom": (None, None, None, None, None),
    "attic": (None, None, None, None, None),
    "crypt": (None, None, None, None, None),
}

async def send_testimony_unlock_dm(user: discord.abc.User, newly_unlocked: list[dict]):
    """
    Sends a gold Dossier Testimony Card via DM whenever a player unlocks an NPC Testimony Clue.
    """
    if not newly_unlocked:
        return
    try:
        dm = await user.create_dm()
        for item in newly_unlocked:
            tier_badge = "🔐 Cross-Examination Breakthrough!" if item.get("tier") == 2 else "🗣️ Official Testimony Unlocked!"
            embed = discord.Embed(
                title=f"{tier_badge}\n📜 {item['title']}",
                description=(
                    f"**Witness Interrogated:** {item['npc_name']}\n\n"
                    f"*{item['clue_text']}*\n\n"
                    f"✅ **Logged permanently to your `/my_dossier` under Recorded Testimonies.**"
                ),
                color=0xD4AF37
            )
            embed.set_footer(text="Ravenscroft Hall — Detective Dossier Record")
            await dm.send(embed=embed)
    except Exception:
        pass


def build_room_embed(room_id: str, room_name: str) -> discord.Embed:
    murder_active = is_murder_active()
    if not murder_active and room_id in PRE_MURDER_ROOM_ATMOSPHERES:
        description = PRE_MURDER_ROOM_ATMOSPHERES[room_id]
    else:
        description = ROOM_ATMOSPHERES.get(room_id, "A shadow-draped chamber in Ravenscroft Hall.")
    
    embed = discord.Embed(
        title=f"🏰 {room_name}",
        description=f"*{description}*",
        color=0x2F4F4F
    )
    
    npc_info = ROOM_TO_NPC_INFO.get(room_id)
    if npc_info and npc_info[0]:
        npc_id, name, pre_murder_on_txt, post_murder_on_txt, off_txt = npc_info
        on_txt = post_murder_on_txt if murder_active else pre_murder_on_txt
        status = get_npc_status(npc_id)
        
        is_here = False
        if status and status["is_on_shift"]:
            if npc_id == "angus":
                active_loc = status["channel_name"] if "channel_name" in status.keys() else ""
                if room_id == "carriage" and active_loc == "the-carriage-house":
                    is_here = True
                elif room_id == "cellar" and active_loc == "the-wine-cellar":
                    is_here = True
            else:
                is_here = True

        if is_here:
            occupancy_str = f"🟢 **{name}** — *[{on_txt}]*"
        else:
            if status and status["is_on_shift"] and npc_id == "angus":
                if room_id == "carriage":
                    occupancy_str = "🔴 **VACANT** — *[Away down in the Wine Cellar stoking the furnace]*"
                else:
                    occupancy_str = "🔴 **VACANT** — *[Away up at the Carriage House workshop]*"
            else:
                occupancy_str = f"🔴 **VACANT** — *[{off_txt}]*"
    else:
        occupancy_str = "⚪ **UNATTENDED** — *Quiet; only the sound of rain.*"

    embed.add_field(name="👤 CURRENT OCCUPANCY", value=occupancy_str, inline=False)
    if murder_active:
        embed.set_footer(text="Tap below to search this chamber with a candle or present physical evidence to the staff.")
    else:
        embed.set_footer(text="Lord Julian is resting upstairs before dinner. Room searches are currently locked.")
    return embed


class PresentEvidenceSelect(discord.ui.Select):
    def __init__(self, npc_id: str, npc_display_name: str, physical_clues: list):
        self.npc_id = npc_id
        self.npc_display_name = npc_display_name
        options = []
        seen = set()
        for c in physical_clues:
            title = c["clue_title"]
            if title in seen or title == "Nothing of Note":
                continue
            seen.add(title)
            desc = (c["clue_text"] or "")[:95]
            options.append(discord.SelectOption(
                label=title[:100],
                value=title[:100],
                description=desc,
                emoji="🔍"
            ))
            if len(options) >= 25:
                break

        super().__init__(
            placeholder=f"Choose physical evidence to show {npc_display_name}...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        chosen_title = self.values[0]
        user_id = interaction.user.id
        speaker_name = interaction.user.display_name

        directive, newly_unlocked = evaluate_interrogation_state(
            user_id=user_id,
            npc_id=self.npc_id,
            user_message=f"I am presenting the physical clue '{chosen_title}' to you. What do you make of this?",
            murder_active=True,
            presented_clue_title=chosen_title
        )

        reply_text = await generate_npc_reply(
            npc_id=self.npc_id,
            user_text=f"*(Presents physical evidence: **{chosen_title}**)* What can you tell me about this?",
            speaker_name=speaker_name,
            recent_channel_messages=[],
            is_murder_active=True,
            interrogation_directive=directive
        )

        # Send the NPC's reaction ephemerally AND send any unlocked Testimony Clue to DMs + /my_dossier
        if newly_unlocked:
            await send_testimony_unlock_dm(interaction.user, newly_unlocked)
            unlocked_titles = ", ".join(f"**{t['title']}**" for t in newly_unlocked)
            status_note = f"\n\n🔐 **Breakthrough!** Unlocked {unlocked_titles} — sent to your **DMs** and logged in `/my_dossier`!"
            color = 0xD4AF37
        else:
            status_note = "\n\n*(No new hidden testimony unlocked with this item—try presenting a different clue or showing this item to another staff member!)*"
            color = 0x708090

        resp_embed = discord.Embed(
            title=f"🗂️ Evidence Presented: {chosen_title}",
            description=f"**{self.npc_display_name}:** {reply_text}{status_note}",
            color=color
        )
        await interaction.followup.send(embed=resp_embed, ephemeral=True)


class PresentEvidenceSelectView(discord.ui.View):
    def __init__(self, npc_id: str, npc_display_name: str, physical_clues: list):
        super().__init__(timeout=180)
        self.add_item(PresentEvidenceSelect(npc_id, npc_display_name, physical_clues))


class RoomSearchView(discord.ui.View):
    def __init__(self, room_id: str = "study"):
        super().__init__(timeout=None)
        self.room_id = room_id

    @discord.ui.button(label="🕯️ Search the Room", style=discord.ButtonStyle.secondary, custom_id="btn_search_room")
    async def search_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        player = get_player(user_id)
        
        if not player or player["interview_step"] < 5:
            await interaction.response.send_message(
                "You must complete your guest registration with Filarello at `#reception-gates` before searching the estate.",
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

        # Always resolve room_id dynamically from the channel where the button was clicked!
        ch_name = getattr(interaction.channel, "name", "")
        actual_room_id = CHANNEL_NAME_TO_ROOM_ID.get(ch_name, self.room_id)
        if actual_room_id == "parlor":
            await interaction.response.send_message(
                "🕯️ The Grand Parlor is a public gathering hall. Search the surrounding estate chambers (`#the-study`, `#the-library`, `#the-conservatory`, `#the-dining-hall`, etc.) for physical clues!",
                ephemeral=True
            )
            return

        if player["tokens_remaining"] <= 0:
            await interaction.response.send_message(
                "🕯️ **Your candles have burned down to the wick.**\n"
                "You have no search candles remaining today. Filarello will replenish them tomorrow morning at 9:00 AM.\n"
                "*(Hint: Interrogating an on-shift staff member can earn you a bonus candle!)*",
                ephemeral=True
            )
            return

        # Deduct token
        consume_token(user_id)
        tokens_left = player["tokens_remaining"] - 1

        # Determine clue pool using actual_room_id
        room_data = ROOM_POOLS.get(actual_room_id, ROOM_POOLS["study"])
        consecutive_empty = player["consecutive_empty"]

        # Check existing clues found by this player
        found_clues = get_player_clues(user_id)
        found_titles = {c["clue_title"] for c in found_clues}

        # Combine static major clues with dynamically generated player clues seeded into this chamber!
        dynamic_clues = get_dynamic_room_clues(actual_room_id)
        combined_majors = list(room_data.get("major", [])) + dynamic_clues

        available_majors = [c for c in combined_majors if c[0] not in found_titles]

        # Probability Roll: 40% major, 45% lore, 15% empty
        # Bad luck protection: if 3 consecutive non-majors, force major if available
        roll = random.random()
        force_major = (consecutive_empty >= 3 and len(available_majors) > 0)

        if (roll < 0.40 or force_major) and len(available_majors) > 0:
            clue = random.choice(available_majors)
            title, text = clue[0], clue[1]
            record_player_clue(user_id, actual_room_id, title, text, is_major=True)
            
            embed = discord.Embed(
                title=f"🔍 Physical Evidence Discovered: {title}",
                description=f"{text}\n\n💡 *Tip: You can present this physical evidence to staff members using the **🗂️ Present Evidence** button to unlock hidden testimonies!*",
                color=0xD4AF37 # Victorian Gold
            )
            embed.set_footer(text=f"Only you can see this. | Candles remaining: {tokens_left}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Permanent Clue Card in DM
            try:
                dm = await interaction.user.create_dm()
                dm_card = discord.Embed(
                    title=f"📁 Physical Evidence: {title}",
                    description=f"**Chamber:** {actual_room_id.replace('-', ' ').title()}\n\n{text}",
                    color=0xD4AF37
                )
                dm_card.set_footer(text="Saved permanently to your /my_dossier under Physical Evidence.")
                await dm.send(embed=dm_card)
            except Exception:
                pass

        elif roll < 0.85:
            # Lore clue
            clue = random.choice(room_data["lore"])
            title, text = clue[0], clue[1]
            record_player_clue(user_id, actual_room_id, title, text, is_major=False)

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
                    description=f"**Chamber:** {actual_room_id.replace('-', ' ').title()}\n\n{text}",
                    color=0x708090
                )
                dm_card.set_footer(text="Saved permanently to your personal detective dossier.")
                await dm.send(embed=dm_card)
            except Exception:
                pass

        else:
            # Empty / Atmosphere
            text = random.choice(room_data["empty"])
            record_player_clue(user_id, actual_room_id, "Nothing of Note", text, is_major=False)

            embed = discord.Embed(
                title="🕯️ Dust & Shadows",
                description=text,
                color=0x2F4F4F # Dark Slate
            )
            embed.set_footer(text=f"Only you can see this. | Candles remaining: {tokens_left}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🗂️ Present Evidence", style=discord.ButtonStyle.primary, custom_id="btn_present_evidence")
    async def present_evidence_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        player = get_player(user_id)
        if not player or player["interview_step"] < 5:
            await interaction.response.send_message(
                "You must complete your guest registration with Filarello at `#reception-gates` first.",
                ephemeral=True
            )
            return

        if not is_murder_active():
            await interaction.response.send_message(
                "🕯️ No crime has occurred yet! Enjoy the Solstice reception until dinner.",
                ephemeral=True
            )
            return

        ch_name = getattr(interaction.channel, "name", "")
        actual_room_id = CHANNEL_NAME_TO_ROOM_ID.get(ch_name, self.room_id)
        npc_info = ROOM_TO_NPC_INFO.get(actual_room_id)

        if not npc_info or not npc_info[0]:
            await interaction.response.send_message(
                "👤 **No Staff Member Present Here.**\n"
                "To cross-examine a witness with your physical evidence, visit a room with an attendant:\n"
                "• **Dr. Abernathy** in `#the-study`\n"
                "• **Filarello** in `#the-grand-parlor` (or use `/present_evidence`)\n"
                "• **Mrs. Gable** in `#the-kitchen-and-pantry`\n"
                "• **Old Angus** in `#the-carriage-house` or `#the-wine-cellar`\n"
                "• **Constable Higgins** in `#the-radio-room`",
                ephemeral=True
            )
            return

        npc_id, npc_display_name, _, _, off_txt = npc_info
        status = get_npc_status(npc_id)
        is_here = False
        if status and status["is_on_shift"]:
            if npc_id == "angus":
                active_loc = status["channel_name"] if "channel_name" in status.keys() else ""
                if actual_room_id == "carriage" and active_loc == "the-carriage-house":
                    is_here = True
                elif actual_room_id == "cellar" and active_loc == "the-wine-cellar":
                    is_here = True
            else:
                is_here = True

        if not is_here:
            if status and status["is_on_shift"] and npc_id == "angus":
                other_loc = "the Wine Cellar" if status["channel_name"] == "the-wine-cellar" else "the Carriage House"
                await interaction.response.send_message(
                    f"🔴 **Old Angus is not here right now.** He is currently over in **{other_loc}**!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"🔴 **{npc_display_name} is currently away** (*{off_txt}*). Return when they are on shift!",
                    ephemeral=True
                )
            return

        all_clues = get_player_clues(user_id)
        physical_clues = [
            c for c in all_clues
            if not str(c["room_id"]).startswith("npc:") and c["clue_title"] != "Nothing of Note"
        ]

        if not physical_clues:
            await interaction.response.send_message(
                "🔍 **Your Evidence Pocket is Empty!**\n"
                "You haven't discovered any physical clues in the rooms yet. Click **🕯️ Search the Room** to find physical evidence first, then present it here!",
                ephemeral=True
            )
            return

        view = PresentEvidenceSelectView(npc_id, npc_display_name, physical_clues)
        await interaction.response.send_message(
            f"🗂️ **Cross-Examine {npc_display_name}**\nSelect a piece of physical evidence from your `/my_dossier` to present:",
            view=view,
            ephemeral=True
        )

