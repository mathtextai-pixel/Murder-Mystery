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
    get_player, get_player_clues, is_murder_active, set_murder_active
)
from data.game_data import DISPATCHES, PARLOR_POLLS, CANON_SOLUTION
from cogs.intake_view import BeginRegistrationView
from cogs.search_view import RoomSearchView, build_room_embed
from cogs.inquest_view import InquestView
from cogs.poll_view import ParlorPollView
from ollama_client import generate_grand_reveal_speech

logger = logging.getLogger("AdminCog")

NPC_CHANNELS = {
    "gable": "the-kitchen-and-pantry",
    "angus": "the-carriage-house",
    "higgins": "the-radio-room",
    "giles": "the-grand-parlor"
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
        "on": "*(Giles steps into the Grand Parlor with an impeccable bow, setting out fresh glasses on the silver tray).* ",
        "off": "*(Giles excuses himself to tend to estate records in the West Wing).* "
    }
}

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _build_or_refresh_estate(self, guild: discord.Guild):
        # 1. Create or get Guest Role
        guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
        if not guest_role:
            guest_role = await guild.create_role(name=GUEST_ROLE_NAME, color=discord.Color.dark_gold(), mentionable=True)
        
        everyone_role = guild.default_role

        # 2. Create Category
        category = discord.utils.get(guild.categories, name=ESTATE_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(ESTATE_CATEGORY_NAME)

        # 3. Create or Refresh Reception Gates
        gates_channel = discord.utils.get(category.text_channels, name=GATES_CHANNEL_NAME)
        if not gates_channel:
            overwrites = {
                everyone_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            }
            gates_channel = await category.create_text_channel(
                GATES_CHANNEL_NAME, 
                overwrites=overwrites,
                topic="Register your arrival with Giles the Butler before entering the estate."
            )
        else:
            await gates_channel.edit(topic="Register your arrival with Giles the Butler before entering the estate.")
            try:
                await gates_channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
            except Exception:
                pass

        embed = discord.Embed(
            title="🏰 Welcome to Ravenscroft Hall",
            description=(
                "The Solstice storm has severed all contact with the mainland.\n"
                "Before Lord Julian Ravenscroft receives you tonight, all guests must register.\n\n"
                "Click the button below to begin your private registration with **Giles the Butler** in your DMs."
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
            try:
                await parlor_channel.purge(limit=5, check=lambda m: m.author.id == self.bot.user.id)
            except Exception:
                pass

        await parlor_channel.send(
            "🔥 **The Grand Parlor Hearth is lit.** Guests may converse, dispute alibis, and interrogate Giles here."
        )
        p1 = PARLOR_POLLS.get(1)
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

    @app_commands.command(name="my_dossier", description="Review your secret character dossier and found clues privately.")
    async def my_dossier(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        player = get_player(user_id)
        if not player or player["interview_step"] < 4:
            await interaction.response.send_message(
                "You haven't completed your intake registration with Giles yet! Visit `#reception-gates`.", 
                ephemeral=True
            )
            return

        clues = get_player_clues(user_id)
        clue_summary = "\n".join([f"• **{c['clue_title']}** ({c['room_id']}): {c['clue_text']}" for c in clues]) if clues else "No clues found yet. Use your daily candles to search rooms!"

        embed = discord.Embed(
            title=f"📜 Dossier: {player['character_title']}",
            color=0x4A0E4E
        )
        embed.add_field(name="🎒 Personal Item", value=player["item_brought"] or "None declared", inline=False)
        embed.add_field(name="🤫 Dirty Secret", value=player["dirty_secret"], inline=False)
        embed.add_field(name="🎯 Secret Objective", value=player["secret_goal"], inline=False)
        embed.add_field(name=f"🕯️ Candles Remaining", value=f"{player['tokens_remaining']} candles", inline=True)
        embed.add_field(name=f"🔍 Clues In Your Pocket ({len(clues)})", value=clue_summary[:1000], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        if day >= 2:
            set_murder_active(True)
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
            p_data = PARLOR_POLLS.get(day)
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

        # 4. Day 14 Inquest button
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

        await interaction.followup.send(f"✅ Advanced to Day {day}. Dispatches, Daily Poll, and candle refills complete.", ephemeral=True)

    @app_commands.command(name="test_refill", description="Test Mode: Refill 2 candles for all guests immediately.")
    @app_commands.default_permissions(administrator=True)
    async def test_refill(self, interaction: discord.Interaction):
        refill_all_tokens()
        await interaction.response.send_message("🕯️ All player candles have been refilled to 2!", ephemeral=True)

    @app_commands.command(name="test_npc_shift", description="Test Mode: Set an NPC on or off shift.")
    @app_commands.default_permissions(administrator=True)
    async def test_npc_shift_cmd(self, interaction: discord.Interaction, npc: str, on_shift: bool):
        npc = npc.lower()
        if npc not in ("giles", "gable", "angus", "higgins"):
            await interaction.response.send_message("NPC must be one of: giles, gable, angus, higgins.", ephemeral=True)
            return

        set_npc_shift(npc, on_shift)
        status_text = "ON SHIFT (Available)" if on_shift else "OFF SHIFT (Away message)"

        # Post in-character movement announcement
        guild = interaction.guild
        chan_name = NPC_CHANNELS.get(npc)
        if chan_name:
            chan = discord.utils.get(guild.text_channels, name=chan_name)
            if chan:
                notice_text = NPC_MOVEMENT_NOTICES.get(npc, {}).get("on" if on_shift else "off", "")
                if notice_text:
                    await chan.send(notice_text)
                topic_status = "🟢 PRESENT & ACTIVE" if on_shift else "🔴 AWAY ON DUTIES"
                await chan.edit(topic=f"🏰 {chan_name.replace('-', ' ').title()} | Status: {topic_status}")

        await interaction.response.send_message(f"✅ Set {npc.capitalize()} to {status_text}.", ephemeral=True)

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
                    "**Giles:** *'Great heavens above! Remain where you are, ladies and gentlemen! Lord Julian... the master has fallen at the base of the stairs! "
                    "He is gone! The estate gates are locked from the outside! No one leaves Ravenscroft Hall!'*"
                ),
                color=0x800000
            )
            blackout_embed.set_footer(text="🕯️ The crime scene is now active. All guests have received 2 search candles.")
            await parlor.send(embed=blackout_embed)

            # Day 2 Poll
            p2 = PARLOR_POLLS.get(2)
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

        await interaction.followup.send("⚡ The murder event has been triggered! Searches are now unlocked and NPCs are in crime-scene mode.", ephemeral=True)

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

    @app_commands.command(name="test_reset_game", description="Test Mode: Reset database and start completely fresh at Day 1 Pre-Murder.")
    @app_commands.default_permissions(administrator=True)
    async def test_reset_game(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        reset_entire_game()
        await self._build_or_refresh_estate(interaction.guild)
        await interaction.followup.send("🔄 Ravenscroft Hall has been completely reset to Day 1 Pre-Murder. All records cleared and rooms refreshed.", ephemeral=True)

    @app_commands.command(name="test_nightly_summary", description="Test Mode: Send the 10:30 PM personalized nightly briefing to all registered guests' DMs.")
    @app_commands.default_permissions(administrator=True)
    async def test_nightly_summary(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = await send_nightly_summaries_to_all(self.bot)
        await interaction.followup.send(f"📬 Delivered personalized Nightly Dispatches to {count} registered guest(s) in DMs!", ephemeral=True)

    @app_commands.command(name="test_send_rumor", description="Test Mode: Slip a secret folded note from Giles under a specific player's door.")
    @app_commands.default_permissions(administrator=True)
    async def test_send_rumor(self, interaction: discord.Interaction, guest: discord.Member, rumor_text: str):
        try:
            dm = await guest.create_dm()
            rumor_embed = discord.Embed(
                title="✉️ DISCREET NOTE FROM GILES",
                description=f"*(A sealed parchment slip was slid beneath your bedchamber door)*:\n\n*\"{rumor_text}\"*\n\n— *Giles, in strictest confidence*",
                color=0xD4AF37
            )
            await dm.send(embed=rumor_embed)
            await interaction.response.send_message(f"✉️ Secret rumor successfully slipped to {guest.display_name}'s DMs!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Failed to deliver DM to {guest.display_name}: {e}", ephemeral=True)

async def send_nightly_summaries_to_all(bot: commands.Bot) -> int:
    players = get_all_players()
    day = get_current_day()
    murder = is_murder_active()
    status_headline = "Lord Julian was discovered dead at 11:42 PM; the house is on high alert." if murder else "Lord Julian is resting upstairs; dinner concluded peacefully."

    delivered = 0
    for p in players:
        if p["interview_step"] < 4:
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
            embed.set_footer(text="Sleep lightly, sir/madam. — Giles, Estate Steward")
            await dm.send(embed=embed)
            delivered += 1
        except Exception as e:
            logger.error(f"Failed to deliver nightly summary to {p['discord_id']}: {e}")

    return delivered

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
