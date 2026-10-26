import discord
from discord.ext import commands
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    DISCORD_TOKEN, ACT_1_ROOMS, ACT_2_ROOMS, ACT_3_ROOMS,
    BULLETIN_CHANNEL_NAME, PARLOR_CHANNEL_NAME, ESTATE_CATEGORY_NAME, GUEST_ROLE_NAME
)
from database import (
    init_db, get_current_day, set_current_day, refill_all_tokens, set_npc_shift, set_murder_active
)
from data.game_data import DISPATCHES, PARLOR_POLLS
from cogs.intake_view import BeginRegistrationView, handle_dm_intake
from cogs.search_view import RoomSearchView
from cogs.inquest_view import InquestView
from cogs.poll_view import ParlorPollView

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RavenscroftBot")

scheduler = AsyncIOScheduler()

def create_bot(enable_message_content: bool = True) -> commands.Bot:
    intents = discord.Intents.default()
    if enable_message_content:
        intents.message_content = True
    return commands.Bot(command_prefix="!", intents=intents)

bot = create_bot(enable_message_content=True)

# Scheduled Daily Dispatch at 9:00 AM
async def scheduled_morning_dispatch():
    day = get_current_day() + 1
    if day > 14:
        return
    
    set_current_day(day)
    if day >= 2:
        set_murder_active(True)
    refill_all_tokens()
    logger.info(f"Fired scheduled morning dispatch for Day {day}")

    for guild in bot.guilds:
        bulletin = discord.utils.get(guild.text_channels, name=BULLETIN_CHANNEL_NAME)
        parlor = discord.utils.get(guild.text_channels, name=PARLOR_CHANNEL_NAME)
        category = discord.utils.get(guild.categories, name=ESTATE_CATEGORY_NAME)
        guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
        
        # 1. Post Dispatch in Bulletin
        dispatch_info = DISPATCHES.get(day, DISPATCHES[1])
        if bulletin:
            embed = discord.Embed(
                title=f"📜 DAY {day}: {dispatch_info['headline']}",
                description=dispatch_info["body"],
                color=0xD4AF37
            )
            embed.set_footer(text="🕯️ All guests have had their 2 candles replenished.")
            await bulletin.send(embed=embed)

        # 2. Post Daily Parlor Poll
        if parlor:
            p_data = PARLOR_POLLS.get(day)
            if p_data:
                poll_embed = discord.Embed(
                    title=f"🗳️ DAY {day} PARLOR INQUIRY",
                    description=f"**{p_data['question']}**\n\n*Cast your vote below:*",
                    color=0x800000
                )
                await parlor.send(embed=poll_embed, view=ParlorPollView(day, p_data["options"]))

        # 3. Unlock rooms
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

# Scheduled NPC Evening Shifts
async def shift_evening_start():
    """5:00 PM: Mrs. Gable arrives in Kitchen"""
    set_npc_shift("gable", True)
    logger.info("Mrs. Gable is now ON SHIFT in the Kitchen.")
    for guild in bot.guilds:
        chan = discord.utils.get(guild.text_channels, name="the-kitchen-and-pantry")
        if chan:
            await chan.send("*(The pantry door creaks open. Mrs. Gable bustles inside, lighting the range stove. She is now present in the kitchen).*")
            await chan.edit(topic="🏰 The Kitchen & Pantry | Status: 🟢 Mrs. Gable is present by the range.")

async def shift_angus_start():
    """7:00 PM: Angus arrives in Furnace / Cellar"""
    set_npc_shift("angus", True)
    logger.info("Angus is now ON SHIFT in the Cellar.")
    for guild in bot.guilds:
        chan = discord.utils.get(guild.text_channels, name="the-carriage-house")
        if chan:
            await chan.send("*(Heavy muddy boots stomp inside. Old Angus enters, drying his coat by the fire. He is now present).*")
            await chan.edit(topic="🏰 The Carriage House | Status: 🟢 Old Angus is present at the workbench.")

async def shift_night_sleep():
    """10:30 PM: Staff goes to sleep (all rooms unattended)"""
    set_npc_shift("gable", False)
    set_npc_shift("angus", False)
    logger.info("Estate staff is now asleep. Rooms are unattended.")
    for guild in bot.guilds:
        k_chan = discord.utils.get(guild.text_channels, name="the-kitchen-and-pantry")
        if k_chan:
            await k_chan.send("*(Mrs. Gable banks the range fire and heads up to bed. The kitchen is now quiet and unattended).*")
            await k_chan.edit(topic="🏰 The Kitchen & Pantry | Status: 🔴 VACANT (Staff is asleep).")
        c_chan = discord.utils.get(guild.text_channels, name="the-carriage-house")
        if c_chan:
            await c_chan.send("*(Old Angus puts out his lantern and locks up. The workshop is now quiet and unattended).*")
            await c_chan.edit(topic="🏰 The Carriage House | Status: 🔴 VACANT (Staff is asleep).")

@bot.event
async def on_ready():
    logger.info(f"🕯️ Logged in as {bot.user.name} ({bot.user.id})")
    
    init_db()

    # Register Persistent Views
    bot.add_view(BeginRegistrationView())
    bot.add_view(InquestView())
    all_rooms = ACT_1_ROOMS + ACT_2_ROOMS + ACT_3_ROOMS
    for room in all_rooms:
        bot.add_view(RoomSearchView(room["id"]))

    # Load Cogs
    try:
        await bot.load_extension("cogs.admin_cog")
        await bot.load_extension("cogs.npc_cog")
    except Exception as e:
        logger.error(f"Error loading cogs: {e}")

    # Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    # Start Scheduler
    if not scheduler.running:
        scheduler.add_job(scheduled_morning_dispatch, "cron", hour=9, minute=0)
        scheduler.add_job(shift_evening_start, "cron", hour=17, minute=0)
        scheduler.add_job(shift_angus_start, "cron", hour=19, minute=0)
        scheduler.add_job(shift_night_sleep, "cron", hour=22, minute=30)
        scheduler.start()
        logger.info("Automated game scheduler started.")

@bot.event
async def on_message(message: discord.Message):
    if message.guild is None and not message.author.bot:
        await handle_dm_intake(message, bot)
        return

    await bot.process_commands(message)

def run_bot_resilient():
    global bot
    try:
        logger.info("Attempting login with Message Content Intent...")
        bot = create_bot(enable_message_content=True)
        # Re-attach events
        bot.event(on_ready)
        bot.event(on_message)
        bot.run(DISCORD_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        logger.warning("Message Content Intent not enabled in Developer Portal. Falling back to default intents...")
        bot = create_bot(enable_message_content=False)
        bot.event(on_ready)
        bot.event(on_message)
        bot.run(DISCORD_TOKEN)

def main():
    if not DISCORD_TOKEN:
        print("⚠️ ERROR: DISCORD_TOKEN is missing in .env!")
        return
    run_bot_resilient()

if __name__ == "__main__":
    main()
