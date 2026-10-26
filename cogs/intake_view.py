import discord
import json
import logging
from database import (
    get_player, create_or_get_player, update_player_interview, get_all_players,
    get_current_day, is_murder_active
)
from config import GUEST_ROLE_NAME
from ollama_client import validate_and_respond_intake, generate_custom_player_dossier, generate_giles_dm_consultation

logger = logging.getLogger("IntakeView")

STEP_QUESTIONS = {
    1: "Pray tell: What is your name and profession, and what is your true connection or relationship to Lord Julian Ravenscroft?",
    2: "And what distinct personal item, tool, or family heirloom of value did you insist on carrying in your luggage tonight?",
    3: "Lastly... what pressing dispute, unpaid debt, desperate loan, or private tension do you urgently need settled with Lord Julian before midnight?"
}

class BeginRegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🖋️ Begin Guest Registration", style=discord.ButtonStyle.primary, custom_id="btn_begin_registration")
    async def begin_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        player = create_or_get_player(user.id, user.name, user.display_name)
        
        if player["interview_step"] >= 4:
            await interaction.response.send_message(
                "You are already fully registered in the Ravenscroft guest registry. Step inside the estate rooms!", 
                ephemeral=True
            )
            return

        # Start or resume interview
        current_step = player["interview_step"]
        if current_step == 0:
            current_step = 1
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
    """Processes DM messages from players completing their 3-question intake."""
    if message.author.bot:
        return
    
    player = get_player(message.author.id)
    if not player or player["interview_step"] == 0:
        return

    # If already registered, this is a private confidential consultation with Giles!
    if player["interview_step"] >= 4:
        async with message.channel.typing():
            current_day = get_current_day()
            murder_active = is_murder_active()
            reply = await generate_giles_dm_consultation(player, message.content, current_day, murder_active)
        await message.channel.send(f"**Giles (in confidence):** {reply}")
        return

    step = player["interview_step"]
    intake_data = json.loads(player["intake_data"] or "{}")
    history = intake_data.get("conversation_history", [])

    # Typing indicator while local Hermes 3 validates
    async with message.channel.typing():
        is_accepted, reply_text = await validate_and_respond_intake(step, message.content, history)

    if not is_accepted:
        # Redirection
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
        # Step 3 accepted -> dynamically weave custom persona from their freely chosen answers!
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

        update_player_interview(
            message.author.id,
            step=4,
            intake_dict=intake_data,
            character_title=char_title,
            dirty_secret=dirty_secret,
            secret_goal=secret_goal,
            item_brought=item_brought
        )

        # Assign Guest Role across guilds
        for guild in bot.guilds:
            try:
                member = await guild.fetch_member(message.author.id)
            except Exception:
                member = guild.get_member(message.author.id)

            if member:
                guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
                if guest_role:
                    try:
                        await member.add_roles(guest_role)
                    except Exception as e:
                        logger.error(f"Failed to assign role to {member}: {e}")

        final_packet = (
            f"**🕯️ Ravenscroft Hall — Registry Complete**\n\n"
            f"**Giles:** {reply_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📜 **YOUR CONFIDENTIAL DOSSIER**\n"
            f"• **Public Identity:** {char_title}\n"
            f"• **Declared Item:** {item_brought}\n"
            f"• **🤫 YOUR DIRTY SECRET:** {dirty_secret}\n"
            f"• **🎯 YOUR SECRET OBJECTIVE:** {secret_goal}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*(The estate doors have unbolted. You now have access to the open rooms in the Discord server!)*"
        )
        await message.channel.send(final_packet)
