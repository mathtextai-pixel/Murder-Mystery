import discord

class ParlorPollView(discord.ui.View):
    def __init__(self, poll_id: int, options: list):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.votes = {}

        # Add select menu for the poll options
        select_options = [
            discord.SelectOption(label=opt[:100], value=f"opt_{i}")
            for i, opt in enumerate(options[:25])
        ]
        
        select = discord.ui.Select(
            placeholder="🗳️ Cast your vote on this matter...",
            options=select_options,
            custom_id=f"poll_select_{poll_id}"
        )
        select.callback = self.on_select_vote
        self.add_item(select)

    async def on_select_vote(self, interaction: discord.Interaction):
        selected_value = interaction.data["values"][0]
        # Find label
        select_item = self.children[0]
        chosen_label = "your selection"
        for opt in select_item.options:
            if opt.value == selected_value:
                chosen_label = opt.label
                break

        self.votes[interaction.user.id] = chosen_label
        await interaction.response.send_message(
            f"🗳️ **Your vote has been cast:** '{chosen_label}'. The room murmurs in quiet agreement or disdain.",
            ephemeral=True
        )
