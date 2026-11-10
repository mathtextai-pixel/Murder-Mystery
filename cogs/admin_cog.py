import discord
from discord import app_commands
from discord.ext import commands
import logging
from config import (
    GUEST_ROLE_NAME, ESTATE_CATEGORY_NAME, GATES_CHANNEL_NAME,
    BULLETIN_CHANNEL_NAME, PARLOR_CHANNEL_NAME, ACT_1_ROOMS, ACT_2_ROOMS, ACT_3_ROOMS
)
from database import (
    get_current_day, set_current_day, refill_all_tokens, set_npc_shift,
    get_npc_status, reset_entire_game, get_all_ballots, get_all_players,
    get_player, get_player_clues, is_murder_active, set_murder_active,
    update_player_interview
)
from data.game_data import DISPATCHES, PARLOR_POLLS, CANON_SOLUTION, get_parlor_poll
from cogs.intake_view import BeginRegistrationView, restart_guest_interview, send_day2_alibi_prompts
from cogs.search_view import (
    RoomSearchView, build_room_embed, PresentEvidenceSelectView,
    CHANNEL_NAME_TO_ROOM_ID, ROOM_TO_NPC_INFO
)
from cogs.inquest_view import InquestView
from cogs.poll_view import ParlorPollView
from ollama_client import generate_grand_reveal_speech

logger = logging.getLogger("AdminCog")

NPC_CHANNELS = {
    "gable": "the-kitchen-and-pantry",
    "angus": "the-carriage-house",
    "higgins": "the-radio-room",
    "giles": "the-grand-parlor",
    "abernathy": "the-study"
}

NPC_MOVEMENT_NOTICES = {
    "gable": {
        "on": "*(The pantry door creaks open. Mrs. Gable bustles inside, shaking out her wet apron and lighting the hearth stove. She is now in the kitchen).* ",
        "off": "*(Mrs. Gable wipes her hands on her apron, pulls on her wool shawl, and heads upstairs to turn down the bedchambers. The kitchen is now quiet and unattended).* "
    },
    "angus": {
        "on": "*(Heavy muddy boots echo on the floor. Old Angus stomps into the workshop, shaking off the rain and lighting his pipe. He is now present).* ",
        "off": "*(Old Angus knocks the ash from his pipe, grabs his oilcloth coat, and heads out into the squall to inspect the fences. The workshop is now empty).* "
    },
    "higgins": {
        "on": "*(The radio vacuum tubes hum to life with a crackle of static. 'Constable Higgins here... frequency open.' Constable Higgins is on the radio).* ",
        "off": "*(A burst of howling maritime static drowns the frequency, followed by silence. The mainland radio link is dead for now).* "
    },
    "giles": {
        "on": "*(Filarello steps into the Grand Parlor with an easy, elegant grace, running a hand through his dark hair as he sets out crystal glasses).* ",
        "off": "*(Filarello excuses himself with a faint, knowing smirk to tend to estate matters in the West Wing).* "
    },
    "abernathy": {
        "on": "*(Dr. Abernathy unclasps his black leather physician's bag with a sharp click, adjusting his round wire spectacles to examine the crime scene).* ",
        "off": "*(Dr. Abernathy snaps his medical bag shut and steps out to consult reference charts in the library).* "
    }
}

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _build_or_refresh_estate(self, guild: discord.Guild, deep_clean: bool = False):
        # 1. Create or get Guest Role
        guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
        if not guest_role:
            guest_role = await guild.create_role(name=GUEST_ROLE_NAME, color=discord.Color.dark_gold(), mentionable=True)
        
        everyone_role = guild.default_role

        # 2. Create Category
        category = discord.utils.get(guild.categories, name=ESTATE_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(ESTATE_CATEGORY_NAME)

        # If deep_clean is active, purge all previous chat and embeds from all estate channels
        if deep_clean and category:
            for ch in category.text_channels:
                try:
                    await ch.purge(limit=500)
                except Exception as e:
                    logger.warning(f"Deep clean purge failed on {ch.name}: {e}")

        # 3. Create or Refresh Reception Gates
        gates_channel = discord.utils.get(category.text_channels, name=GATES_CHANNEL_NAME)
        if not gates_channel:
            overwrites = {
                everyone_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            }
            gates_channel = await category.create_text_channel(
                GATES_CHANNEL_NAME, 
                overwrites=overwrites,
                topic="Register your arrival with Filarello the Butler before entering the estate."
            )
        else:
            await gates_channel.edit(topic="Register your arrival with Filarello the Butler before entering the estate.")
            await gates_channel.set_permissions(everyone_role, view_channel=True, send_messages=False)
            if not deep_clean:
                try:
                    await gates_channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
                except Exception:
                    pass

        embed = discord.Embed(
            title="🏰 Welcome to Ravenscroft Hall",
            description=(
                "The Solstice storm has severed all contact with the mainland.\n"
                "Before Lord Julian Ravenscroft receives you tonight, all guests must register.\n\n"
                "Click the button below to begin your private registration with **Filarello the Butler** in your DMs."
            ),
            color=0xD4AF37
        )
        await gates_channel.send(embed=embed, view=BeginRegistrationView())

        # 4. Create or Refresh Morning Post (Bulletin)
        bulletin_channel = discord.utils.get(category.text_channels, name=BULLETIN_CHANNEL_NAME)
        if not bulletin_channel:
            overwrites = {
                everyone_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            }
            bulletin_channel = await category.create_text_channel(
                BULLETIN_CHANNEL_NAME, 
                overwrites=overwrites,
                topic="The official daily gazette of Ravenscroft Hall. Dispatches published at 9:00 AM."
            )
        else:
            await bulletin_channel.edit(topic="The official daily gazette of Ravenscroft Hall. Dispatches published at 9:00 AM.")
            await bulletin_channel.set_permissions(everyone_role, view_channel=True, send_messages=False)
            if not deep_clean:
                try:
                    await bulletin_channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
                except Exception:
                    pass

        first_dispatch = DISPATCHES[1]
        dispatch_embed = discord.Embed(
            title=f"📜 {first_dispatch['headline']}",
            description=first_dispatch["body"],
            color=0xD4AF37
        )
        await bulletin_channel.send(embed=dispatch_embed)

        # 5. Create or Refresh Grand Parlor (Main Gathering Chat)
        parlor_channel = discord.utils.get(category.text_channels, name=PARLOR_CHANNEL_NAME)
        if not parlor_channel:
            overwrites = {
                everyone_role: discord.PermissionOverwrite(view_channel=False),
                guest_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            parlor_channel = await category.create_text_channel(
                PARLOR_CHANNEL_NAME, 
                overwrites=overwrites,
                topic="🔥 The Grand Parlor Hearth. Daily estate polls and guest debates."
            )
        else:
            await parlor_channel.edit(topic="🔥 The Grand Parlor Hearth. Daily estate polls and guest debates.")
            await parlor_channel.set_permissions(everyone_role, view_channel=False)
            await parlor_channel.set_permissions(guest_role, view_channel=True, send_messages=True)
            if not deep_clean:
                try:
                    await parlor_channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
                except Exception:
                    pass

        await parlor_channel.send(
            "🔥 **The Grand Parlor Hearth is lit.** Guests may converse, dispute alibis, and interrogate Filarello here."
        )
        p1 = get_parlor_poll(1)
        if p1:
            poll_embed = discord.Embed(
                title=f"🗳️ DAY 1 PARLOR INQUIRY",
                description=f"**{p1['question']}**\n\n*Cast your vote below:*",
                color=0x800000
            )
            await parlor_channel.send(embed=poll_embed, view=ParlorPollView(1, p1["options"]))

        # 6. Create or Refresh Act 1 Rooms (Open Day 1)
        for room in ACT_1_ROOMS:
            channel = discord.utils.get(category.text_channels, name=room["channel"])
            if not channel:
                overwrites = {
                    everyone_role: discord.PermissionOverwrite(view_channel=False),
                    guest_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                channel = await category.create_text_channel(
                    room["channel"], 
                    overwrites=overwrites,
                    topic=f"🏰 {room['name']} | Status: 🔓 Unlocked for inquiry."
                )
            else:
                await channel.edit(topic=f"🏰 {room['name']} | Status: 🔓 Unlocked for inquiry.")
                await channel.set_permissions(everyone_role, view_channel=False)
                await channel.set_permissions(guest_role, view_channel=True, send_messages=True)
                if not deep_clean:
                    try:
                        await channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
                    except Exception:
                        pass

            embed = build_room_embed(room["id"], room["name"])
            await channel.send(embed=embed, view=RoomSearchView(room["id"]))

        # 7. Create or Refresh Act 2 & 3 Rooms
        all_later_rooms = ACT_2_ROOMS + ACT_3_ROOMS
        current_day = get_current_day()
        for room in all_later_rooms:
            channel = discord.utils.get(category.text_channels, name=room["channel"])
            is_unlocked = (room in ACT_2_ROOMS and current_day >= 5) or (room in ACT_3_ROOMS and current_day >= 9)
            
            if not channel:
                overwrites = {
                    everyone_role: discord.PermissionOverwrite(view_channel=False),
                    guest_role: discord.PermissionOverwrite(view_channel=is_unlocked)
                }
                status_txt = "🔓 Unlocked for inquiry." if is_unlocked else "🔒 Sealed by order of the estate."
                channel = await category.create_text_channel(
                    room["channel"], 
                    overwrites=overwrites,
                    topic=f"🏰 {room['name']} | Status: {status_txt}"
                )
            else:
                status_txt = "🔓 Unlocked for inquiry." if is_unlocked else "🔒 Sealed by order of the estate."
                await channel.edit(topic=f"🏰 {room['name']} | Status: {status_txt}")
                await channel.set_permissions(everyone_role, view_channel=False)
                await channel.set_permissions(guest_role, view_channel=is_unlocked)
                if not deep_clean:
                    try:
                        await channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
                    except Exception:
                        pass

            embed = build_room_embed(room["id"], room["name"])
            await channel.send(embed=embed, view=RoomSearchView(room["id"]))

        # 8. Create Voice Rooms
        voice_rooms = [
            ("Grand Ballroom", None),
            ("The Wine Cellar [2]", 2),
            ("The Library Alcove [3]", 3),
            ("The Clocktower [1]", 1)
        ]
        for vname, cap in voice_rooms:
            vchan = discord.utils.get(category.voice_channels, name=vname)
            if not vchan:
                overwrites = {
                    everyone_role: discord.PermissionOverwrite(view_channel=False),
                    guest_role: discord.PermissionOverwrite(view_channel=True, connect=True)
                }
                await category.create_voice_channel(vname, user_limit=cap, overwrites=overwrites)
            else:
                await vchan.set_permissions(everyone_role, view_channel=False)
                await vchan.set_permissions(guest_role, view_channel=True, connect=True)

    @app_commands.command(name="my_dossier", description="Review your secret character dossier, physical clues, and recorded NPC testimonies.")
    async def my_dossier(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        player = get_player(user_id)
        if not player or player["interview_step"] < 5:
            await interaction.response.send_message(
                "You haven't completed your intake registration with Filarello yet! Visit `#reception-gates`.", 
                ephemeral=True
            )
            return

        clues = get_player_clues(user_id)
        physical_clues = [
            c for c in clues
            if not str(c["room_id"]).startswith("npc:") and c["clue_title"] != "Nothing of Note"
        ]
        testimony_clues = [
            c for c in clues
            if str(c["room_id"]).startswith("npc:")
        ]

        phys_summary = (
            "\n".join([f"• **{c['clue_title']}** ({c['room_id']}): {c['clue_text']}" for c in physical_clues])
            if physical_clues else "No physical clues found yet. Use **🕯️ Search the Room** to inspect chambers!"
        )
        test_summary = (
            "\n".join([f"• **{c['clue_title']}** ({str(c['room_id']).replace('npc:', '')}): {c['clue_text']}" for c in testimony_clues])
            if testimony_clues else "No official testimonies recorded yet. Question NPCs about specific details or click **🗂️ Present Evidence**!"
        )

        embed = discord.Embed(
            title=f"📜 Dossier: {player['character_title']}",
            color=0x4A0E4E
        )
        embed.add_field(name="🎒 Personal Item", value=player["item_brought"] or "None declared", inline=False)
        alibi_txt = dict(player).get("alibi_claim") or "*(Not yet recorded — Filarello will request your 11:42 PM alibi once the investigation begins, or DM `alibi: <your statement>` to Filarello)*"
        embed.add_field(name="📍 Stated 11:42 PM Alibi & Sighting", value=alibi_txt, inline=False)
        embed.add_field(name="🤫 Dirty Secret (Strictly Confidential)", value=player["dirty_secret"], inline=False)
        embed.add_field(name="🎯 Secret Objective", value=player["secret_goal"], inline=False)
        embed.add_field(name="🕯️ Candles Remaining", value=f"{player['tokens_remaining']} candles", inline=True)
        embed.add_field(name=f"🔍 Physical Evidence Found ({len(physical_clues)})", value=phys_summary[:1024], inline=False)
        embed.add_field(name=f"🗣️ Recorded NPC Testimonies ({len(testimony_clues)})", value=test_summary[:1024], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="present_evidence", description="Present a piece of physical evidence from your dossier to the NPC in this room.")
    async def present_evidence_cmd(self, interaction: discord.Interaction):
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
        actual_room_id = CHANNEL_NAME_TO_ROOM_ID.get(ch_name, "parlor" if interaction.guild is None else None)
        npc_info = ROOM_TO_NPC_INFO.get(actual_room_id) if actual_room_id else None

        if not npc_info or not npc_info[0]:
            await interaction.response.send_message(
                "👤 **No Staff Member Present Here.**\n"
                "Use `/present_evidence` or the **🗂️ Present Evidence** button inside a chamber with an attendant:\n"
                "• **Filarello** in `#the-grand-parlor` (or in your DMs)\n"
                "• **Dr. Abernathy** in `#the-study`\n"
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

    @app_commands.command(name="redo_interview", description="Restart your 3-question registration interview with Filarello in DMs if your dossier needs fixing.")
    async def redo_interview_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await restart_guest_interview(interaction.user)
            await interaction.followup.send(
                "📬 Filarello has opened a fresh page in the guest registry! Check your Direct Messages to redo your 3-question interview.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Could not send a Direct Message to you ({e}). Please ensure DMs from server members are enabled.",
                ephemeral=True
            )

    @app_commands.command(name="guest_roster", description="Host command: View which guests have registered, their progress, and parlor arrival status.")
    @app_commands.default_permissions(administrator=True)
    async def guest_roster_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        import json
        players = [dict(r) for r in get_all_players()]
        if not players:
            await interaction.followup.send("No guests have clicked the registry gates yet.", ephemeral=True)
            return

        confirmed = []
        in_progress = []

        for p in players:
            step = p.get("interview_step", 0)
            intake = json.loads(p.get("intake_data") or "{}")
            announced = intake.get("announced_in_parlor", False)
            ann_icon = "📢 Announced in Parlor" if announced else "⚠️ Not Announced Yet"
            
            if step >= 5:
                title = p.get("character_title") or "Unknown Title"
                item = p.get("item_brought") or "None"
                confirmed.append(
                    f"• <@{p['discord_id']}> ({p.get('display_name') or p.get('username')})\n"
                    f"  **Persona:** {title}\n"
                    f"  **Luggage Prop:** {item}\n"
                    f"  **Status:** {ann_icon}"
                )
            else:
                step_str = f"Question {step}/4" if 1 <= step <= 4 else ("Awaiting Confirmation (Reviewing Dossier)" if step in (35, 45) else f"Step {step}")
                confirmed_ans = len([k for k in intake.keys() if k.startswith("question_")])
                in_progress.append(
                    f"• <@{p['discord_id']}> ({p.get('display_name') or p.get('username')}) — **{step_str}** ({confirmed_ans}/4 questions answered)"
                )

        embed = discord.Embed(
            title="🏰 Ravenscroft Hall — Guest Registry Status",
            color=0xD4AF37
        )
        if confirmed:
            embed.add_field(
                name=f"✅ Confirmed & Checked-In Guests ({len(confirmed)})",
                value="\n\n".join(confirmed),
                inline=False
            )
        else:
            embed.add_field(name="✅ Confirmed & Checked-In Guests (0)", value="None yet.", inline=False)

        if in_progress:
            embed.add_field(
                name=f"⏳ Intake In Progress ({len(in_progress)})",
                value="\n".join(in_progress),
                inline=False
            )

        embed.set_footer(text=f"Total: {len(confirmed)} Confirmed, {len(in_progress)} In Progress • Use /announce_guest to re-post an arrival.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="announce_guest", description="Host command: Manually trigger Filarello's Grand Parlor arrival announcement for a guest.")
    @app_commands.default_permissions(administrator=True)
    async def announce_guest_cmd(self, interaction: discord.Interaction, guest: discord.Member):
        await interaction.response.defer(ephemeral=True)
        import json
        player = get_player(guest.id)
        if not player or player["interview_step"] < 5:
            await interaction.followup.send(
                f"{guest.mention} has not completed registration yet (Current step: {player['interview_step'] if player else 0}).",
                ephemeral=True
            )
            return

        parlor = discord.utils.get(interaction.guild.text_channels, name=PARLOR_CHANNEL_NAME)
        if not parlor:
            await interaction.followup.send("Could not find `#the-grand-parlor` channel.", ephemeral=True)
            return

        await parlor.send(
            f"🔔 *(Filarello smoothly opens the heavy oak doors of the Grand Parlor, bowing with dry elegance)*\n"
            f"**Filarello:** *\"Pray welcome **{player['character_title']}** ({guest.mention}), who has managed to cross the flooded causeway carrying **{player['item_brought']}**. Do make yourselves civil.\"*"
        )
        intake_data = json.loads(player["intake_data"] or "{}")
        intake_data["announced_in_parlor"] = True
        update_player_interview(guest.id, step=player["interview_step"], intake_dict=intake_data)
        await interaction.followup.send(f"✅ Announced {guest.mention} (**{player['character_title']}**) in `#the-grand-parlor`!", ephemeral=True)

    @app_commands.command(name="setup_estate", description="Host only: Auto-creates all Ravenscroft channels, roles, and permissions.")
    @app_commands.default_permissions(administrator=True)
    async def setup_estate(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._build_or_refresh_estate(interaction.guild)
        await interaction.followup.send("✅ Ravenscroft Hall has been built! Rich room descriptions, occupancy badges, and estate polls are active.", ephemeral=True)

    @app_commands.command(name="test_advance_day", description="Test Mode: Advance to any day (1-14) instantly.")
    @app_commands.default_permissions(administrator=True)
    async def test_advance_day(self, interaction: discord.Interaction, day: int):
        if day < 1 or day > 14:
            await interaction.response.send_message("Day must be between 1 and 14.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        set_current_day(day)
        set_murder_active(day >= 2)
        refill_all_tokens()

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=ESTATE_CATEGORY_NAME)
        guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
        bulletin = discord.utils.get(guild.text_channels, name=BULLETIN_CHANNEL_NAME)
        parlor = discord.utils.get(guild.text_channels, name=PARLOR_CHANNEL_NAME)

        dispatch_info = DISPATCHES.get(day, DISPATCHES[1])

        # 1. Post morning dispatch in Bulletin
        if bulletin:
            embed = discord.Embed(
                title=f"📜 DAY {day}: {dispatch_info['headline']}",
                description=dispatch_info["body"],
                color=0xD4AF37
            )
            embed.set_footer(text="🕯️ All guests have had their 2 candles replenished.")
            await bulletin.send(embed=embed)

        # 2. Post Daily Parlor Poll in Grand Parlor
        if parlor:
            p_data = get_parlor_poll(day)
            if p_data:
                poll_embed = discord.Embed(
                    title=f"🗳️ DAY {day} PARLOR INQUIRY",
                    description=f"**{p_data['question']}**\n\n*Cast your vote below:*",
                    color=0x800000
                )
                await parlor.send(embed=poll_embed, view=ParlorPollView(day, p_data["options"]))

        # 3. Handle unlocks
        if day >= 5 and category and guest_role:
            for room in ACT_2_ROOMS:
                chan = discord.utils.get(category.text_channels, name=room["channel"])
                if chan:
                    await chan.set_permissions(guest_role, view_channel=True, send_messages=True)
                    await chan.edit(topic=f"🏰 {room['name']} | Status: 🔓 UNLOCKED FOR INQUIRY")

        if day >= 9 and category and guest_role:
            for room in ACT_3_ROOMS:
                chan = discord.utils.get(category.text_channels, name=room["channel"])
                if chan:
                    await chan.set_permissions(guest_role, view_channel=True, send_messages=True)
                    await chan.edit(topic=f"🏰 {room['name']} | Status: 🔓 UNLOCKED FOR INQUIRY")

        # 4. Refresh room embeds in place so phase descriptions and occupancy badges stay in sync
        await refresh_all_room_embeds(guild, self.bot.user)

        # 5. Day 14 Inquest button
        if day == 14 and parlor:
            inquest_embed = discord.Embed(
                title="⚖️ THE GRAND INQUEST HAS BEGUN",
                description=(
                    "All guests are summoned to the Grand Parlor.\n"
                    "Review your evidence and click below to submit your official accusation ballot!"
                ),
                color=0x800000
            )
            await parlor.send(embed=inquest_embed, view=InquestView())

        # If advancing into Post-Murder (Day 2+), send the 11:42 PM Alibi & Sighting prompt to any registered guest who hasn't recorded one yet
        if day >= 2:
            await send_day2_alibi_prompts(self.bot)

        await interaction.followup.send(f"✅ Advanced to Day {day}. Dispatches, Daily Poll, room headers, and candle refills complete.", ephemeral=True)

    @app_commands.command(name="test_refill", description="Test Mode: Refill 2 candles for all guests immediately.")
    @app_commands.default_permissions(administrator=True)
    async def test_refill(self, interaction: discord.Interaction):
        refill_all_tokens()
        await interaction.response.send_message("🕯️ All player candles have been refilled to 2!", ephemeral=True)

    @app_commands.command(name="test_npc_shift", description="Test Mode: Set an NPC on or off shift, and optionally choose Angus's room (carriage or cellar).")
    @app_commands.default_permissions(administrator=True)
    async def test_npc_shift_cmd(self, interaction: discord.Interaction, npc: str, on_shift: bool, location: str = ""):
        npc = npc.lower()
        if npc not in ("giles", "gable", "angus", "higgins", "abernathy"):
            await interaction.response.send_message("NPC must be one of: giles, gable, angus, higgins, abernathy.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        chan_name = NPC_CHANNELS.get(npc)
        
        if npc == "angus":
            if "cellar" in location.lower() or "wine" in location.lower():
                chan_name = "the-wine-cellar"
            else:
                chan_name = "the-carriage-house"
            set_npc_shift("angus", on_shift, channel_name=chan_name)
        else:
            set_npc_shift(npc, on_shift)

        status_text = "ON SHIFT (Available)" if on_shift else "OFF SHIFT (Away message)"

        # Post in-character movement announcement and refresh room embed badge
        if chan_name:
            chan = discord.utils.get(guild.text_channels, name=chan_name)
            if chan:
                notice_text = NPC_MOVEMENT_NOTICES.get(npc, {}).get("on" if on_shift else "off", "")
                if notice_text:
                    await chan.send(notice_text)
                topic_status = "🟢 PRESENT & ACTIVE" if on_shift else "🔴 AWAY ON DUTIES"
                await chan.edit(topic=f"🏰 {chan_name.replace('-', ' ').title()} | Status: {topic_status}")

        await refresh_all_room_embeds(guild, self.bot.user)
        await interaction.followup.send(f"✅ Set {npc.capitalize()} to {status_text} and updated room occupancy badge.", ephemeral=True)

    @app_commands.command(name="trigger_murder", description="Host command: Trigger the 11:42 PM murder blackout, unlock searches, and begin Day 2.")
    @app_commands.default_permissions(administrator=True)
    async def trigger_murder_cmd(self, interaction: discord.Interaction):
        await self.test_trigger_murder.callback(self, interaction)

    @app_commands.command(name="trigger_final_inquest", description="Host command: Pause the clock, summon everyone to the Grand Parlor, and open the accusation ballot.")
    @app_commands.default_permissions(administrator=True)
    async def trigger_final_inquest_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        set_current_day(14)
        guild = interaction.guild
        parlor = discord.utils.get(guild.text_channels, name=PARLOR_CHANNEL_NAME)
        target_channel = parlor if parlor else interaction.channel

        inquest_embed = discord.Embed(
            title="⚖️ THE GRAND INQUEST HAS OFFICIALLY BEGUN",
            description=(
                "**Filarello:** *\"Ladies and gentlemen, the hour has arrived. Fourteen days of whispers, searching dark corridors, and nursing private secrets.* \n\n"
                "*The county authorities will reach the manor shortly. Before they arrive, Lord Julian's estate requires our official conclusion.* \n\n"
                "**Review your evidence with `/my_dossier` and click below to submit your official Accusation Ballot.**\n"
                "Once all ballots are sealed, I shall present the final truth of Ravenscroft Hall.\"*"
            ),
            color=0x800000
        )
        inquest_embed.set_footer(text="Ballots are private until the Grand Inquest reveal monologue.")
        await target_channel.send(embed=inquest_embed, view=InquestView())
        await interaction.followup.send("⚖️ The Final Inquest has been opened in #the-grand-parlor! The game clock is paused. Guests may now submit their ballots.")

    @app_commands.command(name="trigger_reveal", description="Host command: Tally ballots, crown the Master Sleuth, and deliver Filarello's reveal monologue.")
    @app_commands.default_permissions(administrator=True)
    async def trigger_reveal_cmd(self, interaction: discord.Interaction):
        await self.test_trigger_reveal.callback(self, interaction)

    @app_commands.command(name="reset_game", description="Host command: Full factory reset. Wipes all chat, revokes guest roles, resets to Day 1 pre-murder.")
    @app_commands.default_permissions(administrator=True)
    async def reset_game_cmd(self, interaction: discord.Interaction):
        await self.test_reset_game.callback(self, interaction)

    @app_commands.command(name="test_trigger_murder", description="Test Mode: Trigger the dramatic 11:42 PM murder blackout and unlock searches.")
    @app_commands.default_permissions(administrator=True)
    async def test_trigger_murder(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        set_murder_active(True)
        set_current_day(2)
        refill_all_tokens()

        guild = interaction.guild
        parlor = discord.utils.get(guild.text_channels, name=PARLOR_CHANNEL_NAME)
        bulletin = discord.utils.get(guild.text_channels, name=BULLETIN_CHANNEL_NAME)

        # 1. Dramatic Blackout Broadcast in Parlor
        if parlor:
            blackout_embed = discord.Embed(
                title="⚡ MIDNIGHT BLACKOUT — 11:42 PM",
                description=(
                    "*(A violent thunderclap shatters the leaded glass windows! The grand chandeliers flicker violently and die into pitch darkness. "
                    "A muffled cry and a sickening crash echo from the top of the Grand Staircase. The grandfather clock strikes 11:42 PM).* \n\n"
                    "**Filarello:** *'Good heavens... How dreadfully inconvenient. Ladies and gentlemen, pray remain where you are. Lord Julian... the master has fallen at the base of the stairs. "
                    "He is quite dead, and the estate gates have been locked from without. It appears none of us are leaving.'*"
                ),
                color=0x800000
            )
            blackout_embed.set_footer(text="🕯️ The crime scene is now active. All guests have received 2 search candles.")
            await parlor.send(embed=blackout_embed)

            # Day 2 Poll
            p2 = get_parlor_poll(2)
            if p2:
                poll_embed = discord.Embed(
                    title=f"🗳️ DAY 2 PARLOR INQUIRY",
                    description=f"**{p2['question']}**\n\n*Cast your suspicion below:*",
                    color=0x800000
                )
                await parlor.send(embed=poll_embed, view=ParlorPollView(2, p2["options"]))

        # 2. Bulletin Dispatch
        if bulletin:
            d2 = DISPATCHES[2]
            dispatch_embed = discord.Embed(
                title=f"📜 DAY 2: {d2['headline']}",
                description=d2["body"],
                color=0xD4AF37
            )
            dispatch_embed.set_footer(text="🕯️ All guests have had their 2 candles replenished. Searches are now active.")
            await bulletin.send(embed=dispatch_embed)

        # 3. Update all room headers in place to Crime Scene descriptions & Dr. Abernathy post-murder state!
        await refresh_all_room_embeds(guild, self.bot.user)

        # 4. Dispatch Filarello's urgent Day 2 Morning Alibi & Sighting inquiry to all registered guests in DMs!
        alibi_count = await send_day2_alibi_prompts(self.bot)

        await interaction.followup.send(
            f"⚡ The murder event has been triggered! Searches are now unlocked, room descriptions updated to crime-scene mode, and Filarello dispatched the 11:42 PM Alibi Inquiry to {alibi_count} guest(s) in DMs.",
            ephemeral=True
        )

    @app_commands.command(name="test_trigger_reveal", description="Test Mode: Tally ballots and trigger Hermes 3's Grand Inquest reveal monologue.")
    @app_commands.default_permissions(administrator=True)
    async def test_trigger_reveal(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild
        parlor = discord.utils.get(guild.text_channels, name=PARLOR_CHANNEL_NAME)
        target_channel = parlor if parlor else interaction.channel

        ballots = get_all_ballots()
        if not ballots:
            await interaction.followup.send("⚠️ No ballots have been submitted yet. Submit an accusation first via `/test_advance_day day:14`!", ephemeral=True)
            return

        scores = []
        for b in ballots:
            score = 0
            if "finch" in b["killer_guess"].lower() or "barnaby" in b["killer_guess"].lower():
                score += 50
            if "poker" in b["weapon_guess"].lower() or "iron" in b["weapon_guess"].lower():
                score += 25
            if "clock" in b["passage_guess"].lower() or "wall" in b["passage_guess"].lower() or "tunnel" in b["passage_guess"].lower():
                score += 25
            scores.append((b["display_name"], score, b["killer_guess"], b["statement"]))

        scores.sort(key=lambda x: x[1], reverse=True)
        winner = scores[0]

        summary_text = "\n".join([f"- {s[0]} accused {s[2]} (Score: {s[1]}/100)" for s in scores])
        reveal_speech = await generate_grand_reveal_speech(summary_text)

        reveal_embed = discord.Embed(
            title="⚖️ THE GRAND INQUEST: THE TRUTH REVEALED",
            description=reveal_speech[:4000],
            color=0x800000
        )
        reveal_embed.add_field(name="🏆 MASTER SLEUTH OF RAVENSCROFT", value=f"**{winner[0]}** with {winner[1]} points!", inline=False)
        
        await target_channel.send(embed=reveal_embed)
        await interaction.followup.send("✅ The grand reveal monologue has been delivered to the Grand Parlor!")

    @app_commands.command(name="test_reset_game", description="Test Mode: Wipe all conversations, revoke all Guest roles, and reset to Day 1 Pre-Murder.")
    @app_commands.default_permissions(administrator=True)
    async def test_reset_game(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. Capture previous players before wiping DB so we can clean up their DMs and roles
        previous_players = [dict(p) for p in get_all_players()]

        # 2. Reset SQLite database (players, clues, ballots, day=1, murder_active=0, npc shifts=1)
        reset_entire_game()

        # 3. Clear in-memory NPC conversation timers and Poll votes
        from cogs.poll_view import POLL_VOTES
        POLL_VOTES.clear()
        npc_cog = self.bot.get_cog("NpcCog")
        if npc_cog and hasattr(npc_cog, "active_conversations"):
            npc_cog.active_conversations.clear()

        # 4. Completely delete the 'Estate Guest' role (instantly revokes Guest status from 100% of server members
        # even without Server Members Intent!), then _build_or_refresh_estate recreates a fresh role and locks all rooms.
        guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
        if guest_role:
            try:
                await guest_role.delete(reason="Full Estate Reset — revoking all guest access")
            except Exception as e:
                logger.warning(f"Could not delete Guest role directly ({e}); falling back to per-member removal.")
                for p in previous_players:
                    try:
                        member = await guild.fetch_member(p["discord_id"])
                        if member:
                            await member.remove_roles(guest_role, reason="Estate reset to Day 1 Pre-Murder")
                    except Exception:
                        pass

        # 5. Deep-clean all estate channels (purges up to 500 messages per channel) and rebuild fresh Day 1 headers
        await self._build_or_refresh_estate(guild, deep_clean=True)

        # 6. Clean up the bot's own messages in previous players' DM channels so their DMs are fresh too
        for p in previous_players:
            try:
                user = await self.bot.fetch_user(p["discord_id"])
                if user:
                    dm = await user.create_dm()
                    async for msg in dm.history(limit=40):
                        if msg.author.id == self.bot.user.id:
                            try:
                                await msg.delete()
                            except Exception:
                                pass
            except Exception:
                pass

        await interaction.followup.send(
            "🔄 **Ravenscroft Hall has been completely wiped and reset to Day 1 (Pre-Murder)!**\n"
            "• **Database:** All player dossiers, clues, testimonies, and ballots erased.\n"
            "• **Guest Status:** `@Estate Guest` role revoked from **all** members (everyone is locked out of the rooms until they check in at `#reception-gates`).\n"
            "• **Conversations:** All room channels and bot DM cards have been purged and restored to fresh Day 1 headers.",
            ephemeral=True
        )

    @app_commands.command(name="test_nightly_summary", description="Test Mode: Send the 10:30 PM personalized nightly briefing to all registered guests' DMs.")
    @app_commands.default_permissions(administrator=True)
    async def test_nightly_summary(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = await send_nightly_summaries_to_all(self.bot)
        await interaction.followup.send(f"📬 Delivered personalized Nightly Dispatches to {count} registered guest(s) in DMs!", ephemeral=True)

    @app_commands.command(name="test_send_rumor", description="Test Mode: Slip a secret folded note from Filarello under a specific player's door.")
    @app_commands.default_permissions(administrator=True)
    async def test_send_rumor(self, interaction: discord.Interaction, guest: discord.Member, rumor_text: str):
        try:
            dm = await guest.create_dm()
            rumor_embed = discord.Embed(
                title="✉️ DISCREET NOTE FROM FILARELLO",
                description=f"*(A sealed parchment slip was slid beneath your bedchamber door)*:\n\n*\"{rumor_text}\"*\n\n— *Filarello, in strictest confidence*",
                color=0xD4AF37
            )
            await dm.send(embed=rumor_embed)
            await interaction.response.send_message(f"✉️ Secret rumor successfully slipped to {guest.display_name}'s DMs!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Failed to deliver DM to {guest.display_name}: {e}", ephemeral=True)

async def refresh_all_room_embeds(guild: discord.Guild, bot_user: discord.ClientUser):
    """
    Updates the room header embed in place across all estate rooms so that
    Pre-Murder vs Post-Murder descriptions and NPC occupancy badges stay in sync
    without wiping player chat history.
    """
    if not guild:
        return
    category = discord.utils.get(guild.categories, name=ESTATE_CATEGORY_NAME)
    if not category:
        return

    all_rooms = ACT_1_ROOMS + ACT_2_ROOMS + ACT_3_ROOMS
    for room in all_rooms:
        channel = discord.utils.get(category.text_channels, name=room["channel"])
        if not channel:
            continue
        new_embed = build_room_embed(room["id"], room["name"])
        updated = False
        try:
            async for msg in channel.history(limit=30):
                if msg.author.id == bot_user.id and msg.embeds:
                    if msg.embeds[0].title and msg.embeds[0].title.startswith("🏰"):
                        await msg.edit(embed=new_embed, view=RoomSearchView(room["id"]))
                        updated = True
                        break
            if not updated:
                await channel.send(embed=new_embed, view=RoomSearchView(room["id"]))
        except Exception as e:
            logger.warning(f"Failed to refresh room embed in {channel.name}: {e}")

async def send_nightly_summaries_to_all(bot: commands.Bot) -> int:
    players = get_all_players()
    day = get_current_day()
    murder = is_murder_active()
    status_headline = "Lord Julian was discovered dead at 11:42 PM; the house is on high alert." if murder else "Lord Julian is resting upstairs; dinner concluded peacefully."

    delivered = 0
    for p in players:
        if p["interview_step"] < 5:
            continue
        try:
            user = await bot.fetch_user(p["discord_id"])
            if not user:
                continue
            dm = await user.create_dm()
            clues = get_player_clues(p["discord_id"])
            recent_clues_txt = "\n".join([f"• {c['clue_title']} ({c['room_id']})" for c in clues[:4]]) if clues else "No new clues uncovered today."

            embed = discord.Embed(
                title=f"🕯️ RAVENSCROFT HALL — NIGHTLY DISPATCH (DAY {day})",
                description=f"*Discreet summary for: **{p['character_title']}***\n\n{status_headline}",
                color=0x4A0E4E
            )
            embed.add_field(name="📜 Evidence in Your Pocket", value=recent_clues_txt, inline=False)
            embed.add_field(name="🤫 Personal Reminder", value=p["secret_goal"] or "Keep your actions hidden from the other guests.", inline=False)
            embed.add_field(name="🕯️ Morning Provisions", value="2 fresh candles will be placed on your breakfast tray tomorrow at 9:00 AM.", inline=False)
            embed.set_footer(text="Sleep lightly, sir/madam. — Filarello, Estate Steward")
            await dm.send(embed=embed)
            delivered += 1
        except Exception as e:
            logger.error(f"Failed to deliver nightly summary to {p['discord_id']}: {e}")

    return delivered

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
