import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hermes3:8b")
TEST_MODE = os.getenv("TEST_MODE", "True").lower() in ("true", "1", "yes")

# Game Configuration
DB_PATH = "ravenscroft.db"
DEFAULT_TOKENS_PER_DAY = 2

# Role & Category Names
GUEST_ROLE_NAME = "Guest"
ESTATE_CATEGORY_NAME = "🏰 RAVENSCROFT HALL"
GATES_CHANNEL_NAME = "reception-gates"
BULLETIN_CHANNEL_NAME = "the-morning-post"
PARLOR_CHANNEL_NAME = "the-grand-parlor"

# Act 1 Channels (Open from Day 1)
ACT_1_ROOMS = [
    {"id": "study", "channel": "the-study", "name": "The Grand Study", "cap": 2},
    {"id": "library", "channel": "the-library", "name": "The Victorian Library", "cap": 3},
    {"id": "conservatory", "channel": "the-conservatory", "name": "The Conservatory", "cap": 3},
    {"id": "dining", "channel": "the-dining-hall", "name": "The Dining Hall", "cap": None},
]

# Act 2 Channels (Unlock Day 5)
ACT_2_ROOMS = [
    {"id": "cellar", "channel": "the-wine-cellar", "name": "The Wine Cellar & Furnace", "cap": 2},
    {"id": "bedroom", "channel": "julians-bedroom", "name": "Lord Julian's Bedroom", "cap": 2},
    {"id": "kitchen", "channel": "the-kitchen-and-pantry", "name": "The Kitchen & Pantry", "cap": 2},
]

# Act 3 Channels (Unlock Day 9)
ACT_3_ROOMS = [
    {"id": "attic", "channel": "the-clocktower-attic", "name": "The Clocktower Attic", "cap": 1},
    {"id": "carriage", "channel": "the-carriage-house", "name": "The Carriage House", "cap": 2},
    {"id": "crypt", "channel": "the-family-crypt", "name": "The Ravenscroft Crypt", "cap": 2},
    {"id": "radio", "channel": "the-radio-room", "name": "The Telegraph & Radio Room", "cap": 1},
]
