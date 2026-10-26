import sqlite3
import json
from config import DB_PATH, DEFAULT_TOKENS_PER_DAY

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Game State
    c.execute("""
    CREATE TABLE IF NOT EXISTS game_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # 2. Players
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        discord_id INTEGER PRIMARY KEY,
        username TEXT,
        display_name TEXT,
        character_title TEXT DEFAULT '',
        dirty_secret TEXT DEFAULT '',
        secret_goal TEXT DEFAULT '',
        item_brought TEXT DEFAULT '',
        tokens_remaining INTEGER DEFAULT 2,
        consecutive_empty INTEGER DEFAULT 0,
        interview_step INTEGER DEFAULT 0,
        intake_data TEXT DEFAULT '{}',
        daily_bonus_day INTEGER DEFAULT 0
    )
    """)
    try:
        c.execute("ALTER TABLE players ADD COLUMN daily_bonus_day INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # 3. Discovered Clues (Per-player discovery history)
    c.execute("""
    CREATE TABLE IF NOT EXISTS player_clues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id INTEGER,
        room_id TEXT,
        clue_title TEXT,
        clue_text TEXT,
        is_major INTEGER DEFAULT 0,
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 4. Final Accusation Ballots
    c.execute("""
    CREATE TABLE IF NOT EXISTS ballots (
        discord_id INTEGER PRIMARY KEY,
        killer_guess TEXT,
        weapon_guess TEXT,
        passage_guess TEXT,
        statement TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 5. NPC Shift Status
    c.execute("""
    CREATE TABLE IF NOT EXISTS npc_state (
        npc_id TEXT PRIMARY KEY,
        name TEXT,
        is_on_shift INTEGER DEFAULT 1,
        channel_name TEXT,
        away_message TEXT
    )
    """)
    
    # Default State
    c.execute("INSERT OR IGNORE INTO game_state (key, value) VALUES ('current_day', '1')")
    c.execute("INSERT OR IGNORE INTO game_state (key, value) VALUES ('game_active', '1')")
    c.execute("INSERT OR IGNORE INTO game_state (key, value) VALUES ('murder_active', '0')")
    
    # Default NPCs
    default_npcs = [
        ("giles", "Giles", 1, "the-grand-parlor", "Attending to estate matters in the West Wing. Returns for evening tea at 5:00 PM."),
        ("gable", "Mrs. Gable", 1, "the-kitchen-and-pantry", "Tending to the linens in the East Wing. Back to bake evening scones at 5:00 PM."),
        ("angus", "Old Angus", 1, "the-carriage-house", "Out securing the perimeter fence against the squall. Returns to warm by the furnace at 7:00 PM."),
        ("higgins", "Constable Higgins", 1, "the-radio-room", "Mainland frequency is choked with static. Radio window re-opens at 8:30 PM.")
    ]
    for npc in default_npcs:
        c.execute("""
        INSERT OR IGNORE INTO npc_state (npc_id, name, is_on_shift, channel_name, away_message)
        VALUES (?, ?, ?, ?, ?)
        """, npc)
        
    conn.commit()
    conn.close()

# --- Game State Helpers ---

def get_current_day() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM game_state WHERE key = 'current_day'")
    row = c.fetchone()
    conn.close()
    return int(row["value"]) if row else 1

def set_current_day(day: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('current_day', ?)", (str(day),))
    conn.commit()
    conn.close()

def is_murder_active() -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM game_state WHERE key = 'murder_active'")
    row = c.fetchone()
    conn.close()
    return (row["value"] == "1") if row else False

def set_murder_active(active: bool):
    conn = get_connection()
    c = conn.cursor()
    val = "1" if active else "0"
    c.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('murder_active', ?)", (val,))
    conn.commit()
    conn.close()

# --- Player Helpers ---

def get_player(discord_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_or_get_player(discord_id: int, username: str, display_name: str):
    player = get_player(discord_id)
    if player is None:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
        INSERT INTO players (discord_id, username, display_name, tokens_remaining, interview_step)
        VALUES (?, ?, ?, ?, 0)
        """, (discord_id, username, display_name, DEFAULT_TOKENS_PER_DAY))
        conn.commit()
        conn.close()
        return get_player(discord_id)
    return player

def update_player_interview(discord_id: int, step: int, intake_dict: dict, character_title="", dirty_secret="", secret_goal="", item_brought=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE players 
    SET interview_step = ?,
        intake_data = ?,
        character_title = CASE WHEN ? != '' THEN ? ELSE character_title END,
        dirty_secret = CASE WHEN ? != '' THEN ? ELSE dirty_secret END,
        secret_goal = CASE WHEN ? != '' THEN ? ELSE secret_goal END,
        item_brought = CASE WHEN ? != '' THEN ? ELSE item_brought END
    WHERE discord_id = ?
    """, (step, json.dumps(intake_dict), character_title, character_title, dirty_secret, dirty_secret, secret_goal, secret_goal, item_brought, item_brought, discord_id))
    conn.commit()
    conn.close()

def consume_token(discord_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT tokens_remaining FROM players WHERE discord_id = ?", (discord_id,))
    row = c.fetchone()
    if not row or row["tokens_remaining"] <= 0:
        conn.close()
        return False
    c.execute("UPDATE players SET tokens_remaining = tokens_remaining - 1 WHERE discord_id = ?", (discord_id,))
    conn.commit()
    conn.close()
    return True

def refill_all_tokens():
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE players SET tokens_remaining = ?", (DEFAULT_TOKENS_PER_DAY,))
    conn.commit()
    conn.close()

def refill_player_tokens(discord_id: int, count=DEFAULT_TOKENS_PER_DAY):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE players SET tokens_remaining = ? WHERE discord_id = ?", (count, discord_id))
    conn.commit()
    conn.close()

def check_and_award_interrogation_bonus(discord_id: int, current_day: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT tokens_remaining, daily_bonus_day FROM players WHERE discord_id = ?", (discord_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
    
    last_bonus_day = row["daily_bonus_day"] or 0
    if last_bonus_day < current_day:
        c.execute("""
        UPDATE players 
        SET tokens_remaining = tokens_remaining + 1,
            daily_bonus_day = ?
        WHERE discord_id = ?
        """, (current_day, discord_id))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def record_player_clue(discord_id: int, room_id: str, title: str, text: str, is_major: bool):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO player_clues (discord_id, room_id, clue_title, clue_text, is_major)
    VALUES (?, ?, ?, ?, ?)
    """, (discord_id, room_id, title, text, 1 if is_major else 0))
    if is_major:
        c.execute("UPDATE players SET consecutive_empty = 0 WHERE discord_id = ?", (discord_id,))
    else:
        c.execute("UPDATE players SET consecutive_empty = consecutive_empty + 1 WHERE discord_id = ?", (discord_id,))
    conn.commit()
    conn.close()

def get_player_clues(discord_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM player_clues WHERE discord_id = ? ORDER BY discovered_at DESC", (discord_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_players():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM players")
    rows = c.fetchall()
    conn.close()
    return rows

# --- Ballots Helpers ---

def submit_ballot(discord_id: int, killer: str, weapon: str, passage: str, statement: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO ballots (discord_id, killer_guess, weapon_guess, passage_guess, statement)
    VALUES (?, ?, ?, ?, ?)
    """, (discord_id, killer, weapon, passage, statement))
    conn.commit()
    conn.close()

def get_all_ballots():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT b.*, p.display_name, p.character_title FROM ballots b JOIN players p ON b.discord_id = p.discord_id")
    rows = c.fetchall()
    conn.close()
    return rows

# --- NPC Helpers ---

def get_npc_status(npc_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM npc_state WHERE npc_id = ?", (npc_id,))
    row = c.fetchone()
    conn.close()
    return row

def set_npc_shift(npc_id: str, is_on_shift: bool):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE npc_state SET is_on_shift = ? WHERE npc_id = ?", (1 if is_on_shift else 0, npc_id))
    conn.commit()
    conn.close()

# --- Reset Helper (Test Mode) ---

def reset_entire_game():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM players")
    c.execute("DELETE FROM player_clues")
    c.execute("DELETE FROM ballots")
    c.execute("UPDATE game_state SET value = '1' WHERE key = 'current_day'")
    c.execute("UPDATE game_state SET value = '0' WHERE key = 'murder_active'")
    c.execute("UPDATE npc_state SET is_on_shift = 1")
    conn.commit()
    conn.close()
