import discord
import json
import logging
from database import (
    get_player, create_or_get_player, update_player_interview, update_player_alibi,
    get_all_players, get_current_day, is_murder_active,
    add_dynamic_room_clue, clear_player_dynamic_clues,
    add_witness_sighting, clear_player_witness_sightings
)
from config import GUEST_ROLE_NAME, PARLOR_CHANNEL_NAME
from ollama_client import validate_and_respond_intake, generate_custom_player_dossier, generate_giles_dm_consultation

logger = logging.getLogger("IntakeView")

STEP_QUESTIONS = {
    1: "Pray tell: What is your name and profession, and what is your true, unvarnished history with Lord Julian Ravenscroft?",
    2: "And what distinct personal item or heirloom did you insist on carrying in your luggage tonight? (Please describe its materials, markings, or engravings).",
    3: "Every individual carries a trademark habit, scent, or personal accessory. What telltale signature do you carry? (e.g. cherry pipe tobacco, violet writing ink, silver-tipped cane, gold monocle, distinct perfume).",
    4: "Lastly, in strictest confidence between us... what urgent dispute, unpaid debt, stolen property, or grievance did you come to settle with Lord Julian before midnight?"
}

async def send_day2_alibi_prompts(bot: discord.Client) -> int:
    """
    Sends the Day 2 Morning-After Alibi & Corridor Sighting inquiry to all registered guests in DMs.
    Marks intake_data['awaiting_alibi'] = True so their next DM reply is recorded as their official 11:42 PM alibi.
    """
    players = [dict(r) for r in get_all_players()]
    sent_count = 0
    for p in players:
        if p.get("interview_step", 0) < 5:
            continue
        if p.get("alibi_claim"):
            continue
        try:
            intake_data = json.loads(p.get("intake_data") or "{}")
            intake_data["awaiting_alibi"] = True
            update_player_alibi(p["discord_id"], "", intake_dict=intake_data)

            user = await bot.fetch_user(p["discord_id"])
            if not user:
                continue
            dm = await user.create_dm()
            breadcrumb = intake_data.get("corridor_breadcrumb", "")
            breadcrumb_txt = f"\n\n👁️ **A Telltale Memory From the Blackout:**\n*\"{breadcrumb}\"*\n*(You alone noticed this in the darkness. You may choose to share or withhold this sighting when questioned).* " if breadcrumb else ""
            alibi_embed = discord.Embed(
                title="⚡ URGENT MORNING INQUIRY — THE 11:42 PM BLACKOUT",
                description=(
                    f"**Filarello:** *\"Pardon the intrusion, **{p.get('character_title') or p.get('display_name')}**—though I imagine sleep was elusive in any event. "
                    f"Lord Julian was discovered deceased at the foot of the Grand Staircase when the chandeliers failed at 11:42 PM. Highly inconvenient, and dreadfully untidy.\"*\n\n"
                    f"📋 **OFFICIAL ALIBI & SIGHTING RECORD:**\n"
                    f"**Where in the manor were you when the lights died at 11:42 PM, and what curious sound, shadow, or detail did you happen to glimpse in the dark?**"
                    f"{breadcrumb_txt}\n\n"
                    f"*(Reply directly to this DM to seal your official alibi into the estate investigation ledger).* "
                ),
                color=0x800000
            )
            alibi_embed.set_footer(text="Your stated alibi will be recorded in /my_dossier and known to the estate staff.")
            await dm.send(embed=alibi_embed)
            sent_count += 1
        except Exception as e:
            logger.warning(f"Failed to send Day 2 alibi prompt to {p.get('discord_id')}: {e}")
    return sent_count

async def finalize_guest_registration(user: discord.abc.User, bot: discord.Client) -> str:
    """
    Finalizes a guest's dossier (step = 4), grants the @Guest role across all guilds,
    and posts an atmospheric arrival announcement in #the-grand-parlor.
    """
    player = get_player(user.id)
    if not player:
        return "Player record not found."

    intake_data = json.loads(player["intake_data"] or "{}")
    already_announced = intake_data.get("announced_in_parlor", False)
    intake_data["announced_in_parlor"] = True

    # Seed the player's 2 dynamic clues into the estate rooms if not already seeded
    pending_clues = intake_data.get("pending_clues", [])
    if pending_clues and not intake_data.get("clues_seeded", False):
        clear_player_dynamic_clues(user.id)
        for clue in pending_clues:
            add_dynamic_room_clue(
                source_discord_id=user.id,
                room_id=clue.get("room_id", "study"),
                clue_title=clue.get("title", "Mysterious Trace"),
                clue_text=clue.get("text", "A curious physical trace left behind.")
            )
        intake_data["clues_seeded"] = True

    # Seed the NPC witness sighting if not already seeded
    witness_npc = intake_data.get("witness_npc")
    witness_sighting = intake_data.get("witness_sighting")
    if witness_npc and witness_sighting and not intake_data.get("sighting_seeded", False):
        clear_player_witness_sightings(user.id)
        add_witness_sighting(user.id, witness_npc, witness_sighting)
        intake_data["sighting_seeded"] = True

    update_player_interview(user.id, step=5, intake_dict=intake_data)

    for guild in bot.guilds:
        try:
            member = await guild.fetch_member(user.id)
        except Exception:
            member = guild.get_member(user.id)

        if member:
            guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
            if guest_role:
                try:
                    await member.add_roles(guest_role)
                except Exception as e:
                    logger.error(f"Failed to assign role to {member}: {e}")

            if not already_announced:
                parlor = discord.utils.get(guild.text_channels, name=PARLOR_CHANNEL_NAME)
                if parlor:
                    try:
                        await parlor.send(
                            f"🔔 *(Filarello smoothly opens the heavy oak doors of the Grand Parlor, bowing with dry elegance)*\n"
                            f"**Filarello:** *\"Pray welcome **{player['character_title']}** ({member.mention}), who has managed to cross the flooded causeway carrying **{player['item_brought']}**. Do make yourselves civil.\"*"
                        )
                    except Exception as e:
                        logger.warning(f"Could not post arrival in parlor: {e}")

    # If the murder has already occurred when this guest finishes registration, immediately prompt for their 11:42 PM Alibi!
    if is_murder_active():
        await send_day2_alibi_prompts(bot)

    return player["character_title"]

async def restart_guest_interview(user: discord.abc.User):
    """Resets a guest's interview back to Question 1 and sends the prompt in DMs."""
    create_or_get_player(user.id, user.name, user.display_name)
    clear_player_dynamic_clues(user.id)
    clear_player_witness_sightings(user.id)
    update_player_interview(
        user.id,
        step=1,
        intake_dict={},
        character_title=" ",
        dirty_secret=" ",
        secret_goal=" ",
        item_brought=" "
    )
    update_player_alibi(user.id, "", intake_dict={})
    dm_channel = await user.create_dm()
    greeting = (
        f"**🕯️ Ravenscroft Hall — Fresh Registry Page**\n\n"
        f"**Filarello:** *\"A clean sheet, then. We all deserve a second chance—some of us, several dozen. Let us begin anew, {user.display_name}.\"*\n\n"
        f"**Question 1:** {STEP_QUESTIONS[1]}\n\n"
        f"*(Please reply directly in this DM to answer).* "
    )
    await dm_channel.send(greeting)


class DossierConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Confirm & Enter Estate", style=discord.ButtonStyle.success, custom_id="btn_confirm_dossier")
    async def confirm_dossier(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        title = await finalize_guest_registration(interaction.user, interaction.client)
        await interaction.followup.send(
            f"🗝️ **Registry Confirmed!**\n"
            f"Your identity as **{title}** is now sealed in the Ravenscroft Hall ledger, and all estate staff have been briefed on your arrival.\n"
            f"The manor doors are now unlocked for you in the server—step into `#the-grand-parlor`!",
            ephemeral=False
        )

    @discord.ui.button(label="🔄 Redo Interview", style=discord.ButtonStyle.secondary, custom_id="btn_redo_dossier")
    async def redo_dossier(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await restart_guest_interview(interaction.user)


class BeginRegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🖋️ Begin Guest Registration", style=discord.ButtonStyle.primary, custom_id="btn_begin_registration")
    async def begin_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        player = create_or_get_player(user.id, user.name, user.display_name)
        
        if player["interview_step"] >= 5:
            await interaction.response.send_message(
                f"You are already registered as **{player['character_title']}**! Step inside the estate rooms, or click **Redo Interview** below if you wish to rewrite your backstory.",
                view=DossierConfirmationView(),
                ephemeral=True
            )
            return
        elif player["interview_step"] in (35, 45):
            await interaction.response.send_message(
                f"Your draft dossier is awaiting confirmation! Check your DMs with Filarello to confirm or redo.",
                view=DossierConfirmationView(),
                ephemeral=True
            )
            return

        update_player_interview(user.id, step=1, intake_dict={})

        try:
            dm_channel = await user.create_dm()
            greeting = (
                f"**🕯️ Ravenscroft Hall — Private Reception**\n\n"
                f"Good evening, {user.display_name}. I am **Filarello**, house steward of Ravenscroft Hall.\n"
                f"Before Lord Julian receives you tonight, I am obliged to record your arrival in the estate ledger.\n\n"
                f"**Question 1:** {STEP_QUESTIONS[1]}\n\n"
                f"*(Please reply directly in this DM to answer).* "
            )
            await dm_channel.send(greeting)
            await interaction.response.send_message(
                "📬 Filarello has sent your private registry invitation to your Direct Messages! Check your DMs to proceed.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ I could not send you a Direct Message. Please enable 'Allow direct messages from server members' in your Discord Privacy Settings and try again.",
                ephemeral=True
            )

async def handle_dm_intake(message: discord.Message, bot: discord.Client):
    """Processes DM messages from players completing their 3-question intake or consulting Giles."""
    if message.author.bot:
        return
    
    player = get_player(message.author.id)
    if not player or player["interview_step"] == 0:
        return

    content_clean = message.content.strip().lower()

    # Allow typing 'redo' or 'restart interview' at any time in DMs
    if content_clean in ("redo", "redo interview", "restart", "restart interview"):
        await restart_guest_interview(message.author)
        return

    step = player["interview_step"]

    # Step 45 (or legacy 35) = Waiting for Dossier Confirmation
    if step in (35, 45):
        if content_clean in ("yes", "confirm", "accept", "ok", "looks good"):
            title = await finalize_guest_registration(message.author, bot)
            await message.channel.send(
                f"🗝️ **Registry Confirmed!** Your identity as **{title}** is sealed. You now have full access to the estate rooms in the Discord server!"
            )
        else:
            await message.channel.send(
                "**Filarello:** *\"Patience, my dear guest. Pray press **✅ Confirm & Enter Estate** above if your dossier satisfies you, or **🔄 Redo Interview** if you wish to adjust your arrival story.\"*"
            )
        return

    # If already registered (step >= 5), check if they are answering the Day 2 Midnight Alibi prompt!
    if step >= 5:
        intake_data = json.loads(player["intake_data"] or "{}")
        is_alibi_reply = intake_data.get("awaiting_alibi", False) or content_clean.startswith("alibi:")
        if is_alibi_reply:
            alibi_text = message.content.strip()
            if alibi_text.lower().startswith("alibi:"):
                alibi_text = alibi_text[6:].strip()
            if len(alibi_text.split()) < 3:
                await message.channel.send(
                    "**Filarello:** *\"Come now, sir or madam—surely you can offer a slightly more persuasive alibi than that. Where were you at 11:42 PM, and what did you see?\"*"
                )
                return
            intake_data["awaiting_alibi"] = False
            update_player_alibi(message.author.id, alibi_text, intake_dict=intake_data)
            confirm_embed = discord.Embed(
                title="📋 11:42 PM Alibi & Sighting Sealed",
                description=(
                    f"**Filarello:** *\"Recorded with absolute discretion. Whether the constable believes it remains to be seen.\"*\n\n"
                    f"📍 **Your Recorded Alibi & Sighting:**\n*\"{alibi_text}\"*\n\n"
                    f"✅ **Added to your `/my_dossier`.** *(Tip: You may update it anytime by messaging `alibi: <your new statement>` here in DMs).*"
                ),
                color=0xD4AF37
            )
            await message.channel.send(embed=confirm_embed)
            return

        from data.prompts import evaluate_interrogation_state
        from cogs.search_view import send_testimony_unlock_dm
        async with message.channel.typing():
            current_day = get_current_day()
            murder_active = is_murder_active()
            directive, newly_unlocked = evaluate_interrogation_state(
                user_id=message.author.id,
                npc_id="giles",
                user_message=message.content,
                murder_active=murder_active
            )
            reply = await generate_giles_dm_consultation(
                dict(player),
                message.content,
                current_day,
                murder_active,
                interrogation_directive=directive
            )
        await message.channel.send(f"**Filarello (in confidence):** {reply}")
        if newly_unlocked:
            await send_testimony_unlock_dm(message.author, newly_unlocked)
        return

    intake_data = json.loads(player["intake_data"] or "{}")
    history = intake_data.get("conversation_history", [])

    # Typing indicator while local Hermes 3 validates
    async with message.channel.typing():
        is_accepted, reply_text = await validate_and_respond_intake(step, message.content, history)

    if not is_accepted:
        await message.channel.send(f"**Filarello:** {reply_text}")
        return

    # Accepted: store answer
    intake_data[f"question_{step}"] = message.content
    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": reply_text})
    intake_data["conversation_history"] = history

    if step < 4:
        next_step = step + 1
        update_player_interview(message.author.id, step=next_step, intake_dict=intake_data)
        next_prompt = f"**Filarello:** {reply_text}\n\n**Question {next_step}:** {STEP_QUESTIONS[next_step]}"
        await message.channel.send(next_prompt)
    else:
        # Step 4 accepted -> generate custom persona preview, dirty secret, objective & physical clues!
        q1_ans = intake_data.get("question_1", "Guest")
        q2_ans = intake_data.get("question_2", "A mysterious traveling case")
        q3_ans = intake_data.get("question_3", "A subtle distinctive scent")
        q4_ans = intake_data.get("question_4", "A confidential dispute")

        async with message.channel.typing():
            custom_dossier = await generate_custom_player_dossier(
                player_name=message.author.display_name,
                q1=q1_ans,
                q2=q2_ans,
                q3=q3_ans,
                q4=q4_ans
            )

        char_title = custom_dossier["title"]
        dirty_secret = custom_dossier["secret"]
        secret_goal = custom_dossier["goal"]
        item_brought = q2_ans
        pending_clues = custom_dossier.get("clues", [])
        intake_data["pending_clues"] = pending_clues
        intake_data["witness_npc"] = custom_dossier.get("witness_npc", "gable")
        intake_data["witness_sighting"] = custom_dossier.get("witness_sighting", "")
        intake_data["corridor_breadcrumb"] = custom_dossier.get("corridor_breadcrumb", "")

        # Set step=45 (Pending Confirmation) so they can review and Confirm or Redo!
        update_player_interview(
            message.author.id,
            step=45,
            intake_dict=intake_data,
            character_title=char_title,
            dirty_secret=dirty_secret,
            secret_goal=secret_goal,
            item_brought=item_brought
        )

        clues_preview = ""
        if pending_clues:
            clues_preview = (
                f"\n• **🔍 Evidence Web Seeded:** 2 physical clues and 1 staff eyewitness observation "
                f"have been seeded into the estate for other sleuths to investigate!\n"
            )

        final_packet = (
            f"**🕯️ Ravenscroft Hall — Draft Guest Dossier**\n\n"
            f"**Filarello:** {reply_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📜 **PLEASE REVIEW YOUR GENERATED DOSSIER**\n"
            f"• **Public Identity:** {char_title}\n"
            f"• **Declared Item:** {item_brought}\n"
            f"• **🤫 YOUR DIRTY SECRET:** {dirty_secret}\n"
            f"• **🎯 YOUR SECRET OBJECTIVE:** {secret_goal}"
            f"{clues_preview}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Does this accurately reflect your character? Click **✅ Confirm & Enter Estate** below to unlock the manor doors, or click **🔄 Redo Interview** if Filarello misrecorded any detail.*"
        )
        await message.channel.send(final_packet, view=DossierConfirmationView())
