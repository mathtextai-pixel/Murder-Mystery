import discord
from discord.ext import commands
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    DISCORD_TOKEN, ACT_1_ROOMS, ACT_2_ROOMS, ACT_3_ROOMS,
    BULLETIN_CHANNEL_NAME, ESTATE_CATEGORY_NAME, GUEST_ROLE_NAME
)
from database import (
    init_db, get_current_day, set_current_day, refill_all_tokens, set_npc_shift
)
from data.game_data import DISPATCHES
from cogs.intake_view import BeginRegistrationView, handle_dm_intake
from cogs.search_view import RoomSearchView
from cogs.inquest_view import InquestView

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RavenscroftBot")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()

# Scheduled Daily Dispatch at 9:00 AM
async def scheduled_morning_dispatch():
    day = get_current_day() + 1
    if day > 14:
        return
    
    set_current_day(day)
    refill_all_tokens()
    logger.info(f"Fired scheduled morning dispatch for Day {day}")

    for guild in bot.guilds:
        bulletin = discord.utils.get(guild.text_channels, name=BULLETIN_CHANNEL_NAME)
        category = discord.utils.get(guild.categories, name=ESTATE_CATEGORY_NAME)
        guest_role = discord.utils.get(guild.roles, name=GUEST_ROLE_NAME)
        
        dispatch_info = DISPATCHES.get(day, DISPATCHES[1])
        if bulletin:
            embed = discord.Embed(
                title=f"📜 DAY {day}: {dispatch_info['headline']}",
                description=dispatch_info["body"],
                color=0xD4AF37
            )
            embed.set_footer(text="🕯️ All guests have had their 2 candles replenished.")
            await bulletin.send(embed=embed)

        # Unlock rooms
        if day >= 5 and category and guest_role:
            for room in ACT_2_ROOMS:
                chan = discord.utils.get(category.text_channels, name=room["channel"])
                if chan:
                    await chan.set_permissions(guest_role, view_channel=True, send_messages=True)

        if day >= 9 and category and guest_role:
            for room in ACT_3_ROOMS:
                chan = discord.utils.get(category.text_channels, name=room["channel"])
                if chan:
                    await chan.set_permissions(guest_role, view_channel=True, send_messages=True)

# Scheduled NPC Evening Shifts
async def shift_evening_start():
    """5:00 PM: Mrs. Gable arrives in Kitchen"""
    set_npc_shift("gable", True)
    logger.info("Mrs. Gable is now ON SHIFT in the Kitchen.")

async def shift_angus_start():
    """7:00 PM: Angus arrives in Furnace / Cellar"""
    set_npc_shift("angus", True)
    logger.info("Angus is now ON SHIFT in the Cellar.")

async def shift_night_sleep():
    """10:30 PM: Staff goes to sleep (all rooms unattended)"""
    set_npc_shift("gable", False)
    set_npc_shift("angus", False)
    logger.info("Estate staff is now asleep. Rooms are unattended.")

@bot.event
async def on_ready():
    logger.info(f"🕯️ Logged in as {bot.user.name} ({bot.user.id})")
    
    # 1. Initialize DB
    init_db()

    # 2. Register Persistent Views (Buttons work even after bot restarts)
    bot.add_view(BeginRegistrationView())
    bot.add_view(InquestView())
    all_rooms = ACT_1_ROOMS + ACT_2_ROOMS + ACT_3_ROOMS
    for room in all_rooms:
        bot.add_view(RoomSearchView(room["id"]))

    # 3. Load Cogs
    await bot.load_extension("cogs.admin_cog")
    await bot.load_extension("cogs.npc_cog")

    # 4. Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    # 5. Start Scheduler
    if not scheduler.running:
        # 9:00 AM Daily Dispatch
        scheduler.add_job(scheduled_morning_dispatch, "cron", hour=9, minute=0)
        # 5:00 PM Gable Shift
        scheduler.add_job(shift_evening_start, "cron", hour=17, minute=0)
        # 7:00 PM Angus Shift
        scheduler.add_job(shift_angus_start, "cron", hour=19, minute=0)
        # 10:30 PM Staff Sleep
        scheduler.add_job(shift_night_sleep, "cron", hour=22, minute=30)
        scheduler.start()
        logger.info("Automated game scheduler started.")

@bot.event
async def on_message(message: discord.Message):
    # Handle DMs for intake interview
    if message.guild is None and not message.author.bot:
        await handle_dm_intake(message, bot)
        return

    await bot.process_commands(message)

def main():
    if not DISCORD_TOKEN:
        print("\n" + "="*60)
        print("⚠️ ERROR: DISCORD_TOKEN is missing!")
        print("Please create a .env file and set DISCORD_TOKEN=your_token_here")
        print("See README.md for instructions.")
        print("="*60 + "\n")
        return

    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
