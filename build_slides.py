import json
import subprocess
import sys

PRES_ID = "1OclilvO1y0gsYFCEpELHJUOGjLjOCFpa0lfoAcca45c"

# Read current elements to cleanly wipe old textboxes
res = subprocess.run(["gslides", "readonly", "read", PRES_ID, "--json"], capture_output=True, text=True)
data = json.loads(res.stdout)
slides_data = data.get("slides", [])

slide_ids = [s["objectId"] for s in slides_data]
print("Found slides:", slide_ids)

ops = []

# 1. Delete all old elements
for s in slides_data:
    for el in s.get("pageElements", []):
        ops.append({"op": "delete-element", "element": el["objectId"]})

# 2. Set background on all existing 8 slides
BG_COLOR = "#0D0F17"
CARD_BG = "#161926"
CARD_ACCENT_BG = "#1E2235"
GOLD = "#D4AF37"
GOLD_LIGHT = "#EAD07C"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#9CA3AF"
TEXT_BODY = "#EDEDF2"

for sid in slide_ids:
    ops.append({"op": "set-background", "slide": sid, "color": BG_COLOR})

# 3. Add Slide 9
NEW_SLIDE_ID = "SLIDE_9"
ops.append({"op": "add-slide", "layout": "BLANK", "id": NEW_SLIDE_ID})
ops.append({"op": "set-background", "slide": NEW_SLIDE_ID, "color": BG_COLOR})

# Helper functions for clean layout
def add_card(slide, x, y, width, height, text, font_size=11, bold=False, color=TEXT_BODY, bg=CARD_BG, align="left"):
    ops.append({
        "op": "add-textbox",
        "slide": slide,
        "text": text,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "font_size": font_size,
        "bold": bold,
        "color": color,
        "background_color": bg,
        "alignment": align
    })

def add_header(slide, title, subtitle):
    ops.append({
        "op": "add-textbox",
        "slide": slide,
        "text": title,
        "x": 40,
        "y": 20,
        "width": 640,
        "height": 32,
        "font_size": 20,
        "bold": True,
        "color": GOLD,
        "alignment": "left"
    })
    ops.append({
        "op": "add-textbox",
        "slide": slide,
        "text": subtitle,
        "x": 40,
        "y": 50,
        "width": 640,
        "height": 20,
        "font_size": 11,
        "bold": False,
        "color": TEXT_MUTED,
        "alignment": "left"
    })

# ==========================================
# SLIDE 1 (ID: p) - Title Slide
# ==========================================
s1 = slide_ids[0]
ops.append({"op": "add-shape", "slide": s1, "shape_type": "RECTANGLE", "x": 310, "y": 45, "width": 100, "height": 3, "background_color": GOLD})
add_card(s1, 40, 60, 640, 25, "🏰 AN INTERACTIVE 1920s GOTHIC MYSTERY", font_size=11, bold=True, color=GOLD, bg="transparent", align="center")
add_card(s1, 40, 85, 640, 55, "RAVENSCROFT HALL", font_size=38, bold=True, color=TEXT_WHITE, bg="transparent", align="center")
add_card(s1, 40, 145, 640, 30, "Guest Orientation & Detective Playbook", font_size=16, bold=True, color=GOLD_LIGHT, bg="transparent", align="center")
add_card(s1, 40, 180, 640, 25, "Autumn Equinox, 1920 • 8 Guests • 14 Days • 1 Murder", font_size=12, bold=False, color=TEXT_MUTED, bg="transparent", align="center")

add_card(s1, 45, 225, 300, 130, 
    "🎭 THE GATHERING\n"
    "• Hosted entirely on Discord\n"
    "• Paced across 14 real-world days\n"
    "• Search chambers, find physical clues & interrogate staff\n"
    "• Midnight alibis, secret alliances & social deduction\n"
    "• No pre-scripted lines: your choices shape the outcome!",
    font_size=10.5, bg=CARD_BG)

add_card(s1, 375, 225, 300, 130, 
    "🤵 BUTLER FILARELLO\n"
    "\"Welcome to the Hall. I have prepared your bedchambers and registered your luggage. Mind the floorboards after dark, and do try to keep the parlor cordial... despite whatever brought you here.\"\n"
    "— Butler Filarello (Early 40s, dry deadpan wit & cad)",
    font_size=10.5, bg=CARD_BG)

add_card(s1, 40, 368, 640, 22, "A local AI murder mystery • All clues are discoverable • Zero pre-assigned culprits", font_size=10, color=TEXT_MUTED, bg="transparent", align="center")
ops.append({"op": "set-notes", "slide": s1, "text": "Welcome the players to Ravenscroft Hall. Butler Filarello is their steward and host throughout the game."})

# ==========================================
# SLIDE 2 (ID: slide_ids[1]) - The Premise
# ==========================================
s2 = slide_ids[1]
add_header(s2, "🏰 The Premise: Autumn Equinox, 1920", "Perched on the windswept Atlantic cliffs of Cornwall")

# Image of gothic manor
ops.append({
    "op": "add-image",
    "slide": s2,
    "url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80",
    "x": 40, "y": 78, "width": 240, "height": 245
})
add_card(s2, 40, 328, 240, 40, "📍 Ravenscroft Hall, Cornwall Coast\nCut off by high tide and gale-force squalls.", font_size=9.5, bg=CARD_BG, align="center")

# Right column cards
add_card(s2, 300, 78, 380, 80, 
    "🌊 THE ISOLATION\n"
    "A violent Solstice gale has washed out the river bridge and downed telephone wires. No one can arrive, and no one can leave until the storm abates.",
    font_size=10.5, bg=CARD_BG)

add_card(s2, 300, 166, 380, 80, 
    "🕯️ THE INVITATION\n"
    "Lord Julian Ravenscroft—eccentric, wealthy, and deeply paranoid—has summoned eight acquaintances for an urgent announcement regarding his revised estate will.",
    font_size=10.5, bg=CARD_BG)

add_card(s2, 300, 254, 380, 80, 
    "🎭 THE 8 GUESTS (YOU)\n"
    "You each carry a distinct 1920s profession, a personal luggage heirloom, and an urgent reason to confront Julian before midnight. Lean into the melodrama!",
    font_size=10.5, bg=CARD_BG)

add_card(s2, 40, 375, 640, 20, "💡 Day 1 Status: Lord Julian is alive upstairs resting before dinner. Searches begin only when tragedy strikes!", font_size=10, bold=True, color=GOLD, bg="transparent", align="center")
ops.append({"op": "set-notes", "slide": s2, "text": "Set the scene: gothic Cornwall, isolated cliffside manor, raging storm."})

# ==========================================
# SLIDE 3 (ID: slide_ids[2]) - 14-Day Timeline
# ==========================================
s3 = slide_ids[2]
add_header(s3, "⏳ The 14-Day Investigation Timeline", "1 Real-World Day = 1 In-Game Day • Paced for casual daily drop-in play")

col_w = 152
gap = 10
start_x = 40
y_pos = 78
card_h = 270

add_card(s3, start_x, y_pos, col_w, card_h,
    "DAY 1\nARRIVAL & INTAKE\n\n"
    "• Register in private DMs with Butler Filarello\n"
    "• Declare identity, profession & luggage prop\n"
    "• Mingle by the hearth in #the-grand-parlor\n"
    "• Solstice arrival poll\n"
    "• Julian rests upstairs",
    font_size=10, bg=CARD_BG)

add_card(s3, start_x + (col_w+gap), y_pos, col_w, card_h,
    "DAY 2\nTHE MIDNIGHT CRIME\n\n"
    "• 11:42 PM: Lights die; Julian found dead on stairs!\n"
    "• Ground floor chambers unlock for inspection\n"
    "• 2 Daily search candles delivered at breakfast\n"
    "• Filarello demands your sworn 11:42 PM alibi in DMs",
    font_size=10, bg=CARD_BG)

add_card(s3, start_x + (col_w+gap)*2, y_pos, col_w, card_h,
    "DAYS 3–13\nTHE INQUIRY\n\n"
    "• Day 5: Domestic Wing unlocks (Kitchen, Cellar)\n"
    "• Day 9: Restricted Towers & Radio Room unlock\n"
    "• Question 5 live NPCs & cross-examine clues\n"
    "• Daily Morning Post dispatches & hearth polls",
    font_size=10, bg=CARD_BG)

add_card(s3, start_x + (col_w+gap)*3, y_pos, col_w, card_h,
    "DAY 14\nGRAND INQUEST\n\n"
    "• All chambers unlocked\n"
    "• Official Accusation Ballot: Killer, Weapon, Route\n"
    "• Final parlor debate & group voice call\n"
    "• Epilogue monologue & Master Sleuth crowned!",
    font_size=10, bg=CARD_BG)

add_card(s3, 40, 358, 640, 32, "🔔 Estate Shift Schedule: 9:00 AM (Dispatches & Candles) • 12:00 PM (Polls) • 5:00 PM (Kitchen) • 7:00 PM (Cellar) • 10:30 PM (Bedtime Briefings)", font_size=9.5, color=GOLD_LIGHT, bg=CARD_ACCENT_BG, align="center")
ops.append({"op": "set-notes", "slide": s3, "text": "Explain the 14-day timeline. Players do not need to be online 24/7."})

# ==========================================
# SLIDE 4 (ID: slide_ids[3]) - Check-in at the Gates
# ==========================================
s4 = slide_ids[3]
add_header(s4, "📜 Step 1: Check-in at the Gates (Character Creation)", "Butler Filarello greets you in private DMs to log your identity before you enter the Hall")

# Left Column (Questions)
add_card(s4, 40, 78, 385, 78,
    "Q1: IDENTITY & PROFESSION\n"
    "Your name, authentic 1920s occupation (e.g. physician, tutor, antiquarian, card sharp, socialite, soldier, artist, scholar), and your relationship to Lord Julian.",
    font_size=10, bg=CARD_BG)

add_card(s4, 40, 162, 385, 78,
    "Q2: LUGGAGE HEIRLOOM (PUBLIC)\n"
    "A tangible personal item you brought (silver flask, antique spyglass, deck of marked cards, journal, lockpicks). Filarello announces it publicly upon your arrival!",
    font_size=10, bg=CARD_BG)

add_card(s4, 40, 246, 385, 78,
    "Q3: CONFIDENTIAL DISPUTE (SECRET)\n"
    "The urgent debt, stolen property, or secret grievance you came to settle before midnight. Strictly confidential between you and Butler Filarello!",
    font_size=10, bg=CARD_BG)

add_card(s4, 40, 330, 385, 45,
    "✅ DOSSIER REVIEW SCREEN: Filarello generates your character summary in DMs.\n"
    "Click [✅ Confirm & Enter Estate] to seal, or [🔄 Redo Interview] to edit!",
    font_size=9.5, color=GOLD_LIGHT, bg=CARD_ACCENT_BG)

# Right Column (Image + Dossier Box)
ops.append({
    "op": "add-image",
    "slide": s4,
    "url": "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?auto=format&fit=crop&w=800&q=80",
    "x": 445, "y": 78, "width": 235, "height": 215
})

add_card(s4, 445, 300, 235, 75,
    "📂 /my_dossier\n"
    "Your private dossier records your identity, secret objective, sworn midnight alibi, physical clues, and inventory at all times.",
    font_size=9.5, bg=CARD_BG, align="center")

ops.append({"op": "set-notes", "slide": s4, "text": "Describe the 3 check-in questions asked by Butler Filarello."})

# ==========================================
# SLIDE 5 (ID: slide_ids[4]) - The Candle Economy & Searching
# ==========================================
s5 = slide_ids[4]
add_header(s5, "🕯️ The Estate Economy: Candles & Searching", "How to explore dark chambers and discover forensic evidence")

# Left Column (Candle image)
ops.append({
    "op": "add-image",
    "slide": s5,
    "url": "https://images.unsplash.com/photo-1603575448878-868a20723f5d?auto=format&fit=crop&w=800&q=80",
    "x": 40, "y": 78, "width": 235, "height": 220
})
add_card(s5, 40, 305, 235, 70,
    "🕯️ Shadows of the Hall\n"
    "Candles illuminate unsealed rooms to reveal vital physical clues and forensic traces.",
    font_size=9.5, bg=CARD_BG, align="center")

# Right Column (Candle mechanics)
add_card(s5, 295, 78, 385, 115,
    "🕯️ DAILY SEARCH CANDLES (9:00 AM)\n"
    "• Filarello delivers 2 fresh search candles on your breakfast tray every morning.\n"
    "• Click '🕯️ Search the Room' on any unsealed room embed to search.\n"
    "• Finds Physical Clues, forensic traces, or estate lore recorded in '/my_dossier'.\n"
    "• Bad-Luck Protection: An empty roll guarantees major evidence on your next try!\n"
    "• Searches activate immediately after the murder on Day 2.",
    font_size=10, bg=CARD_BG)

add_card(s5, 295, 201, 385, 100,
    "🔥 +1 BONUS INTERROGATION CANDLE\n"
    "• Earn 1 bonus candle daily through investigative diligence!\n"
    "• Interrogate an on-duty staff member with a substantive inquiry (6+ words with a clue keyword or '?').\n"
    "• If the staff member appreciates your question, they hand you +1 bonus candle for your rounds.",
    font_size=10, bg=CARD_BG)

add_card(s5, 295, 308, 385, 67,
    "💡 Detective Tip: Coordinate room searches with other guests! Sharing search targets ensures the party never wastes candles duplicating rooms.",
    font_size=9.5, color=GOLD_LIGHT, bg=CARD_ACCENT_BG)

ops.append({"op": "set-notes", "slide": s5, "text": "Explain the 2 daily candles, bad luck protection, and +1 bonus candle."})

# ==========================================
# SLIDE 6 (ID: slide_ids[5]) - Interrogating Staff & Evidence
# ==========================================
s6 = slide_ids[5]
add_header(s6, "🗣️ Interrogating Staff & Cross-Examination", "Uncover hidden testimonies by questioning the 5 estate residents")

# Left Column (NPCs & Mechanics)
add_card(s6, 40, 78, 385, 125,
    "👤 THE 5 RESIDENTS OF RAVENSCROFT HALL\n"
    "• Butler Filarello: #the-grand-parlor & private DMs (dashing, deadpan wit)\n"
    "• Dr. Abernathy (Physician): #the-study (forensics & autopsy results)\n"
    "• Mrs. Gable (Head Cook): #the-kitchen-and-pantry (5:00 PM shift, estate gossip)\n"
    "• Old Angus (Groundskeeper): #the-carriage-house & #the-wine-cellar (7:00 PM shift)\n"
    "• Constable Higgins (Police): #the-radio-room (shortwave dispatches)",
    font_size=9.5, bg=CARD_BG)

add_card(s6, 40, 210, 385, 75,
    "💬 ACTIVE CONVERSATION MEMORY\n"
    "In an NPC's room, you do NOT need to repeat their name or type '?'. Once you address them, they stay in active dialogue with you for 3 minutes.",
    font_size=10, bg=CARD_BG)

add_card(s6, 40, 292, 385, 83,
    "🗂️ PRESENT EVIDENCE BUTTON\n"
    "Click '🗂️ Present Evidence' on any room embed to confront an NPC with a physical clue. Triggers exclusive forensic Testimonies sent straight to your DMs!",
    font_size=10, color=GOLD_LIGHT, bg=CARD_ACCENT_BG)

# Right Column (Image + Explanation)
ops.append({
    "op": "add-image",
    "slide": s6,
    "url": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=800&q=80",
    "x": 445, "y": 78, "width": 235, "height": 205
})

add_card(s6, 445, 290, 235, 85,
    "🔍 Two Evidence Types:\n"
    "• Physical Evidence: Found by burning candles in rooms.\n"
    "• Testimony Evidence: Earned by cross-examining witnesses.",
    font_size=9.5, bg=CARD_BG, align="center")

ops.append({"op": "set-notes", "slide": s6, "text": "Explain staff roles, 3-minute conversation memory, and the Present Evidence button."})

# ==========================================
# SLIDE 7 (ID: slide_ids[6]) - DEDICATED ALIBI SLIDE (ZERO SPOILERS)
# ==========================================
s7 = slide_ids[6]
add_header(s7, "🕰️ The 11:42 PM Midnight Alibi: How It Works & Catching Liars", "The central social deduction mechanic of Ravenscroft Hall • Zero Spoilers")

# Left Column (Clock Image)
ops.append({
    "op": "add-image",
    "slide": s7,
    "url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=800&q=80",
    "x": 40, "y": 78, "width": 220, "height": 195
})
add_card(s7, 40, 280, 220, 95,
    "⚡ 11:42 PM Blackout\n"
    "The chandeliers die. A scream echoes from the grand stairs. When candles are lit, Lord Julian lies dead.\nWhere were you?",
    font_size=9.5, bg=CARD_BG, align="center")

# Right Column (Alibi Breakdown)
add_card(s7, 275, 78, 405, 85,
    "📨 THE DAY 2 DM DISPATCH FROM FILARELLO\n"
    "The moment murder strikes on Day 2, Filarello privately DMs each guest demanding two sworn statements:\n"
    "1. Exact Location: Where were you when the lights died? (e.g. bedchamber, library, terrace)\n"
    "2. Sighting / Sound: What shadow, footsteps, voice, or draft did you encounter in the dark?\n"
    "Sealed permanently in your '/my_dossier' under '📍 Stated 11:42 PM Alibi'.",
    font_size=9.5, bg=CARD_BG)

add_card(s7, 275, 170, 405, 120,
    "🔍 HOW DETECTIVES CATCH LIARS (SOCIAL DEDUCTION)\n"
    "Cross-examine everyone's stated alibis in #the-grand-parlor to expose deceptions:\n"
    "• Timeline Clashes: Did two guests claim they were alone in the billiard room at 11:42 PM?\n"
    "• Impossible Routes: Could someone reasonably sprint from the cellar to the stairs in seconds?\n"
    "• Conflicting Sightings: Guest A saw a figure in a coat heading east; Guest B swears that corridor was completely empty!\n"
    "• Physical Clue Ties: Does someone's stated path pass where a fresh footprint was found?",
    font_size=9.5, bg=CARD_BG)

add_card(s7, 275, 297, 405, 78,
    "🛡️ STAFF CONFIDENTIALITY & STRATEGY\n"
    "• Filarello and staff will NEVER leak your private secret dispute in public.\n"
    "• But your sworn 11:42 PM alibi is on the public estate record for all guests to inspect!\n"
    "• You may bluff or bend the truth to protect yourself—just don't get caught in an impossible contradiction!",
    font_size=9.5, color=GOLD_LIGHT, bg=CARD_ACCENT_BG)

ops.append({"op": "set-notes", "slide": s7, "text": "Detailed alibi breakdown: Filarello DM dispatch on Day 2, what players must answer, how timeline clashes expose liars."})

# ==========================================
# SLIDE 8 (ID: slide_ids[7]) - Secrets & Social Deception
# ==========================================
s8 = slide_ids[7]
add_header(s8, "🤫 Secrets, Suspicions & Social Deception", "How to navigate suspicion, form alliances, and protect your character's reputation")

# Left Column (Scales Image)
ops.append({
    "op": "add-image",
    "slide": s8,
    "url": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80",
    "x": 40, "y": 78, "width": 235, "height": 220
})
add_card(s8, 40, 305, 235, 70,
    "⚖️ Motive ≠ Murder\n"
    "Every guest has something to hide, but only one is a cold-blooded killer.",
    font_size=9.5, bg=CARD_BG, align="center")

# Right Column (Cards)
add_card(s8, 295, 78, 385, 90,
    "EVERYONE LOOKS GUILTY\n"
    "• Every guest carries a private secret and an incriminating trace generated from intake.\n"
    "• You WILL feel suspicious! But rest assured: none of you wanted murder.\n"
    "• Your goal is to unmask the true culprit while deflecting attention from your own past.",
    font_size=10, bg=CARD_BG)

add_card(s8, 295, 175, 385, 95,
    "BLUFFING & DEFLECTION\n"
    "• When an incriminating clue points toward your luggage or past, don't panic!\n"
    "• Bluff, misdirect, or trade information with trusted allies to clear your name.\n"
    "• Cross-examining NPCs can yield testimonies that corroborate your innocence.",
    font_size=10, bg=CARD_BG)

add_card(s8, 295, 277, 385, 98,
    "SECRET ALLIANCES (BACKROOM DMS)\n"
    "• The parlor is public, but private DMs between guests are fully encouraged!\n"
    "• Form secret coalitions, cross-compare clue notes, and agree on voting blocs.\n"
    "• Just remember: anyone in your alliance could be the culprit playing dumb!",
    font_size=10, color=GOLD_LIGHT, bg=CARD_ACCENT_BG)

ops.append({"op": "set-notes", "slide": s8, "text": "Reassure players that having a dark secret does not make them the murderer."})

# ==========================================
# SLIDE 9 (ID: NEW_SLIDE_ID) - Daily Routine & Golden Rules
# ==========================================
s9 = NEW_SLIDE_ID
add_header(s9, "👑 Daily Routine & Golden Rules for Maximum Fun", "Essential schedule, player slash commands, and the code of the estate")

add_card(s9, 40, 78, 640, 80,
    "⏰ THE DAILY ESTATE SCHEDULE\n"
    "• 9:00 AM: The Morning Post dispatch published; 2 fresh search candles added to your tray\n"
    "• 12:00 PM: Daily Parlor Inquiry suspect poll opens in #the-grand-parlor\n"
    "• 5:00 PM: Mrs. Gable arrives on shift in #the-kitchen-and-pantry\n"
    "• 7:00 PM: Old Angus arrives on shift in #the-carriage-house & #the-wine-cellar\n"
    "• 10:30 PM: Staff retires; Butler Filarello delivers personal Bedtime Briefings in DMs",
    font_size=9.5, bg=CARD_BG)

add_card(s9, 40, 166, 640, 60,
    "⌨️ ESSENTIAL SLASH COMMANDS\n"
    "• /my_dossier — View your character profile, secrets, sworn alibi, clues, and inventory\n"
    "• /present_evidence — Confront an on-duty NPC with a physical clue to unlock forensic testimony\n"
    "• /redo_interview — Restart your character intake with Filarello if you wish to adjust your identity",
    font_size=9.5, color=GOLD_LIGHT, bg=CARD_ACCENT_BG)

add_card(s9, 40, 234, 640, 115,
    "🎭 4 GOLDEN RULES FOR PLAYERS\n"
    "1. Commit to the Bit: Lean into 1920s vintage flair, dramatic reactions, and parlor melodrama!\n"
    "2. Form Secret Alliances: Private DMs are where the real detective deals and trades are struck.\n"
    "3. Challenge Alibis at the Hearth: Dissect the 11:42 PM timeline in #the-grand-parlor.\n"
    "4. Mistakes & Clumsy Lies Are Fun: You don't have to play 'optimally'—wild theories and botched bluffs make the game memorable!",
    font_size=10, bg=CARD_BG)

add_card(s9, 40, 357, 640, 25, "🏰 The gates of Ravenscroft Hall are opening... Welcome, guests, and happy sleuthing!", font_size=12, bold=True, color=GOLD, bg="transparent", align="center")
ops.append({"op": "set-notes", "slide": s9, "text": "Final rules of engagement, slash commands, and encouraging casual social fun."})

# Write batch file
batch_path = "/tmp/ravenscroft_batch_update.json"
with open(batch_path, "w") as f:
    json.dump(ops, f, indent=2)

print(f"Generated {len(ops)} operations in {batch_path}")
