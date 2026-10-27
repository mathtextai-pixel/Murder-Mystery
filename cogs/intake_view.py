import discord
import json
import logging
from database import (
    get_player, create_or_get_player, update_player_interview, get_all_players,
    get_current_day, is_murder_active
)
from config import GUEST_ROLE_NAME, PARLOR_CHANNEL_NAME
from ollama_client import validate_and_respond_intake, generate_custom_player_dossier, generate_giles_dm_consultation

logger = logging.getLogger("IntakeView")

STEP_QUESTIONS = {
    1: "Pray tell: What is your name and profession, and what is your true connection or relationship to Lord Julian Ravenscroft?",
    2: "And what distinct personal item, tool, or family heirloom of value did you insist on carrying in your luggage tonight?",
    3: "Lastly... what pressing dispute, unpaid debt, desperate loan, or private tension do you urgently need settled with Lord Julian before midnight?"
}

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

    update_player_interview(user.id, step=4, intake_dict=intake_data)

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
                            f"🔔 *(Giles swings open the heavy oak doors of the Grand Parlor)*\n"
                            f"**Giles:** *\"Pray welcome **{player['character_title']}** ({member.mention}), who has just stepped in from the Solstice squall carrying **{player['item_brought']}**.\"*"
                        )
                    except Exception as e:
                        logger.warning(f"Could not post arrival in parlor: {e}")

    return player["character_title"]

async def restart_guest_interview(user: discord.abc.User):
    """Resets a guest's interview back to Question 1 and sends the prompt in DMs."""
    create_or_get_player(user.id, user.name, user.display_name)
    update_player_interview(
        user.id,
        step=1,
        intake_dict={},
        character_title=" ",
        dirty_secret=" ",
        secret_goal=" ",
        item_brought=" "
    )
    dm_channel = await user.create_dm()
    greeting = (
        f"**🕯️ Ravenscroft Hall — Fresh Registry Page**\n\n"
        f"**Giles:** *\"My apologies for any clerical misunderstanding, {user.display_name}. Let us strike that page from the ledger and begin anew.\"*\n\n"
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
        
        if player["interview_step"] >= 4:
            await interaction.response.send_message(
                f"You are already registered as **{player['character_title']}**! Step inside the estate rooms, or click **Redo Interview** below if you wish to rewrite your backstory.",
                view=DossierConfirmationView(),
                ephemeral=True
            )
            return

        update_player_interview(user.id, step=1, intake_dict={})

        try:
            dm_channel = await user.create_dm()
            greeting = (
                f"**🕯️ Ravenscroft Hall — Private Reception**\n\n"
                f"Good evening, {user.display_name}. I am **Giles**, steward of Ravenscroft Hall.\n"
                f"Before Lord Julian receives you tonight, I must record your arrival in the estate guest registry.\n\n"
                f"**Question 1:** {STEP_QUESTIONS[1]}\n\n"
                f"*(Please reply directly in this DM to answer).* "
            )
            await dm_channel.send(greeting)
            await interaction.response.send_message(
                "📬 Giles has sent your private registry invitation to your Direct Messages! Check your DMs to proceed.",
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

    # Step 35 = Waiting for Dossier Confirmation
    if step == 35:
        if content_clean in ("yes", "confirm", "accept", "ok", "looks good"):
            title = await finalize_guest_registration(message.author, bot)
            await message.channel.send(
                f"🗝️ **Registry Confirmed!** Your identity as **{title}** is sealed. You now have full access to the estate rooms in the Discord server!"
            )
        else:
            await message.channel.send(
                "**Giles:** *\"Pray forgive me—please press **✅ Confirm & Enter Estate** on the dossier above if the details are satisfactory, or press **🔄 Redo Interview** if you wish to revise your entry.\"*"
            )
        return

    # If already registered (step >= 4), this is a private 1-on-1 consultation with Giles!
    if step >= 4:
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
        await message.channel.send(f"**Giles (in confidence):** {reply}")
        if newly_unlocked:
            await send_testimony_unlock_dm(message.author, newly_unlocked)
        return

    intake_data = json.loads(player["intake_data"] or "{}")
    history = intake_data.get("conversation_history", [])

    # Typing indicator while local Hermes 3 validates
    async with message.channel.typing():
        is_accepted, reply_text = await validate_and_respond_intake(step, message.content, history)

    if not is_accepted:
        await message.channel.send(f"**Giles:** {reply_text}")
        return

    # Accepted: store answer
    intake_data[f"question_{step}"] = message.content
    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": reply_text})
    intake_data["conversation_history"] = history

    if step < 3:
        next_step = step + 1
        update_player_interview(message.author.id, step=next_step, intake_dict=intake_data)
        next_prompt = f"**Giles:** {reply_text}\n\n**Question {next_step}:** {STEP_QUESTIONS[next_step]}"
        await message.channel.send(next_prompt)
    else:
        # Step 3 accepted -> generate custom persona preview and ask for confirmation!
        q1_ans = intake_data.get("question_1", "Guest")
        q2_ans = intake_data.get("question_2", "A mysterious traveling case")
        q3_ans = intake_data.get("question_3", "A personal disagreement")

        async with message.channel.typing():
            custom_dossier = await generate_custom_player_dossier(
                player_name=message.author.display_name,
                q1=q1_ans,
                q2=q2_ans,
                q3=q3_ans
            )

        char_title = custom_dossier["title"]
        dirty_secret = custom_dossier["secret"]
        secret_goal = custom_dossier["goal"]
        item_brought = q2_ans

        # Set step=35 (Pending Confirmation) so they can review and Confirm or Redo!
        update_player_interview(
            message.author.id,
            step=35,
            intake_dict=intake_data,
            character_title=char_title,
            dirty_secret=dirty_secret,
            secret_goal=secret_goal,
            item_brought=item_brought
        )

        final_packet = (
            f"**🕯️ Ravenscroft Hall — Draft Guest Dossier**\n\n"
            f"**Giles:** {reply_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📜 **PLEASE REVIEW YOUR GENERATED DOSSIER**\n"
            f"• **Public Identity:** {char_title}\n"
            f"• **Declared Item:** {item_brought}\n"
            f"• **🤫 YOUR DIRTY SECRET:** {dirty_secret}\n"
            f"• **🎯 YOUR SECRET OBJECTIVE:** {secret_goal}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Does this accurately reflect your character? Click **✅ Confirm & Enter Estate** below to unlock the manor doors, or click **🔄 Redo Interview** if Giles misrecorded any detail.*"
        )
        await message.channel.send(final_packet, view=DossierConfirmationView())
