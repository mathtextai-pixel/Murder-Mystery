# 🏰 Ravenscroft Hall: Discord Murder Mystery Engine

A full-fledged, local AI-powered Gothic Murder Mystery game engine built for Discord. Powered by **Python (`discord.py`)** for deterministic game logic and **Ollama (`hermes3:8b`)** running locally on your Apple Silicon Mac for rich, private Victorian roleplay.

---

## 🌟 System Features

* **3-Question DM Intake & Role Assignment:** Players initiate their registration with Giles the Butler in private DMs. Hermes 3 validates their answers and binds them to a secret persona.
* **Interactive Room Exploration:** 10 estate rooms featuring `[ 🕯️ Search the Room ]` buttons, weighted random clue pools, bad-luck protection, and 2 daily search candles.
* **4 Living AI Staff NPCs:** Giles, Mrs. Gable, Old Angus, and Constable Higgins respond to `@mentions` with distinct dialects and dynamic shift schedules.
* **Automated 14-Day Progression:** Scheduled 9:00 AM morning dispatches, phased 3-act room unlocks, and the narrative pivot from guest suspicion to hunting the intruder (**Barnaby Finch**).
* **Live Inquest Accusation Modal & Finale:** Confidential Discord modal ballots on Day 14, automated scoring, player superlatives, and a cinematic grand reveal monologue.
* **Test Mode & Solo Sandbox:** Instant time travel, candle refills, and shift toggles so you can test the entire experience with 1–2 players before inviting your 8 friends.

---

## 🚀 Quick Setup Guide

### 1. Configure Your Discord Bot (3 Minutes)
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and log in.
2. Click **"New Application"** in the top right. Name it: `Ravenscroft Hall`.
3. Go to the **"Bot"** tab on the left:
   * Click **"Reset Token"** and copy your bot token.
   * Scroll down to **"Privileged Gateway Intents"** and **enable all three**:
     * ✅ **Presence Intent**
     * ✅ **Server Members Intent**
     * ✅ **Message Content Intent** *(Critical for DM intake and NPC @mentions)*
   * Click **Save Changes**.
4. Go to **"OAuth2" -> "URL Generator"**:
   * Under **Scopes**, check: `bot` and `applications.commands`.
   * Under **Bot Permissions**, check: `Administrator` (or *Manage Roles*, *Manage Channels*, *Send Messages*, *Read Message History*).
   * Copy the generated URL at the bottom, paste it into your browser, and invite the bot to your Discord server.

---

### 2. Configure Your `.env` File
In this project directory, create a `.env` file (you can copy `.env.example`):
```bash
cp .env.example .env
```
Open `.env` and paste your bot token:
```ini
DISCORD_TOKEN=your_actual_discord_bot_token_here
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=hermes3:8b
TEST_MODE=True
```

---

### 3. Ensure Ollama is Running
Ollama is already installed on your Mac Mini. If you ever need to verify it:
```bash
curl http://localhost:11434/
```
*(Should return "Ollama is running").*

---

### 4. Launch the Bot
Activate the virtual environment and start the bot:
```bash
./venv/bin/python bot.py
```
You will see:
```text
🕯️ Logged in as Ravenscroft Hall (Bot ID)
Synced 6 slash commands.
Automated game scheduler started.
```

---

## 🧪 Testing with 1–2 Players (Test Mode)

Once your bot is inside your Discord server, you can test the entire game from scratch:

### Step 1: Auto-Build the Estate
In any channel on your server, type the slash command:
```text
/setup_estate
```
* **What happens:** The bot automatically creates the `🏰 RAVENSCROFT HALL` category, the `@Guest` role, all 10 estate channels, and the voice breakout rooms!

### Step 2: Test Guest Registration
1. Head to `#reception-gates`.
2. Tap the button: **`[ 🖋️ Begin Guest Registration ]`**.
3. Check your Discord DMs! Giles will greet you and ask Question 1. Answer in character.
4. Complete all 3 questions. Giles will validate your answers, hand you your secret dossier, and grant you the `@Guest` role, unbolting the mansion!

### Step 3: Test Room Searching
1. Walk into `#the-study` or `#the-library`.
2. Tap **`[ 🕯️ Search the Room ]`**.
3. You will receive an ephemeral discovery (visible only to you) and your candle count will decrement.

### Step 4: Test NPC Interrogation
In `#the-kitchen-and-pantry`, type:
```text
@Ravenscroft Hall Mrs. Gable, what did you hear in the dumbwaiter last night?
```
Mrs. Gable will reply in character right in the channel!

### Step 5: Test Time Travel & The Finale
* `/test_advance_day day:5` — Instantly unlocks the Wine Cellar and Master Bedroom and refills your candles!
* `/test_advance_day day:9` — Instantly unlocks the Attic, Crypt, and Radio room!
* `/test_advance_day day:14` — Triggers the Grand Inquest button in `#the-grand-parlor`!
* In `#the-grand-parlor`, click **`[ ⚖️ Submit Final Accusation ]`**, fill out the ballot modal, and hit submit.
* Then type: `/test_trigger_reveal` — Hermes 3 will deliver the dramatic Grand Reveal monologue unmasking **Barnaby Finch**!

### Step 6: Reset for the Real Game
When you are ready to play for real with your 8 friends:
```text
/test_reset_game
```
This wipes all test clues, clears the database, and puts the mansion right back to Day 1.

---

## 📁 Project Architecture

```
kind-goodall/
├── .env.example          # Environment template
├── config.py             # Room configs, channel names, role definitions
├── database.py           # SQLite database engine & state persistence
├── ollama_client.py      # Async HTTP client for local Hermes 3 on M1
├── data/
│   ├── game_data.py      # Clue pools, 8 secret archetypes, 14 dispatches
│   └── prompts.py        # System prompts for Giles, Gable, Angus, Higgins
├── cogs/
│   ├── intake_view.py    # DM intake button, 3-question state machine
│   ├── search_view.py    # Room search button, weighted probabilities
│   ├── inquest_view.py   # Native Discord accusation modal & ballots
│   ├── npc_cog.py        # @mention NPC dialogue handler & shift logic
│   └── admin_cog.py      # Slash commands: /setup_estate, /test_advance_day
├── bot.py                # Main bot entry point & APScheduler clock
└── requirements.txt      # Python dependencies
```
