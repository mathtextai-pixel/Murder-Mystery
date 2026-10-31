import discord
from database import submit_ballot, get_player
from data.game_data import CANON_SOLUTION

class AccusationModal(discord.ui.Modal, title="⚖️ The Ravenscroft Inquest Ballot"):
    killer = discord.ui.TextInput(
        label="1. WHO DELIVERED THE FATAL BLOW?",
        placeholder="Name the specific person who murdered Lord Julian...",
        required=True,
        max_length=100
    )
    weapon = discord.ui.TextInput(
        label="2. WHAT WAS THE TRUE FATAL WEAPON?",
        placeholder="Name the exact murder weapon or cause of death...",
        required=True,
        max_length=100
    )
    passage = discord.ui.TextInput(
        label="3. HOW DID THE KILLER ENTER & ESCAPE?",
        placeholder="Describe the route or passage used by the killer...",
        required=True,
        max_length=100
    )
    statement = discord.ui.TextInput(
        label="4. YOUR FINAL DEDUCTION (Summary)",
        style=discord.TextStyle.paragraph,
        placeholder="Provide your deduction explaining how the crime occurred...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        player = get_player(user_id)
        
        if not player or player["interview_step"] < 4:
            await interaction.response.send_message(
                "You must be an active registered guest to submit an accusation.", 
                ephemeral=True
            )
            return

        submit_ballot(
            user_id,
            self.killer.value.strip(),
            self.weapon.value.strip(),
            self.passage.value.strip(),
            self.statement.value.strip()
        )

        confirm_embed = discord.Embed(
            title="⚖️ Inquest Ballot Sealed",
            description=(
                f"Your formal accusation has been recorded in the estate archives.\n\n"
                f"• **Accused Killer:** {self.killer.value}\n"
                f"• **Alleged Weapon:** {self.weapon.value}\n"
                f"• **Suspected Passage:** {self.passage.value}\n\n"
                f"Once all guests have submitted their findings, Filarello will present the final truth!"
            ),
            color=0x800000 # Burgundy
        )
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

class InquestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚖️ Submit Final Accusation", style=discord.ButtonStyle.danger, custom_id="btn_submit_accusation")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AccusationModal())
