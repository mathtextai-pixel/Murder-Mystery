import discord
from collections import Counter

# In-memory store mapping poll_id -> {user_id: chosen_label}
POLL_VOTES: dict[int, dict[int, str]] = {}

class ParlorPollView(discord.ui.View):
    def __init__(self, poll_id: int, options: list):
        super().__init__(timeout=None)
        self.poll_id = poll_id

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
        select_item = self.children[0]
        chosen_label = "your selection"
        for opt in select_item.options:
            if opt.value == selected_value:
                chosen_label = opt.label
                break

        poll_votes = POLL_VOTES.setdefault(self.poll_id, {})
        poll_votes[interaction.user.id] = chosen_label

        # Update the poll embed with a live anonymous tally
        try:
            if interaction.message and interaction.message.embeds:
                old_embed = interaction.message.embeds[0]
                counts = Counter(poll_votes.values())
                tally_lines = [f"• **{label}**: {cnt} vote(s)" for label, cnt in counts.most_common()]
                tally_block = "\n".join(tally_lines)

                new_embed = discord.Embed(
                    title=old_embed.title,
                    description=old_embed.description,
                    color=old_embed.color
                )
                new_embed.add_field(
                    name=f"📊 Live Parlor Tally ({len(poll_votes)} cast)",
                    value=tally_block[:1024],
                    inline=False
                )
                await interaction.message.edit(embed=new_embed, view=self)
        except Exception:
            pass

        await interaction.response.send_message(
            f"🗳️ **Your vote has been cast:** '{chosen_label}'. The room murmurs in quiet agreement or disdain.",
            ephemeral=True
        )
