# Master Game Data: Clues, Archetypes, and Dispatches

CANON_SOLUTION = {
    "killer": "Barnaby Finch",
    "weapon": "Heavy Iron Fireplace Poker",
    "passage": "Secret corridor behind the grandfather clock in the gallery",
    "motive": "Fired without a pension five years ago; living in the service passages and struck Julian after being confronted over stolen heirlooms."
}

# The 8 Dynamic Secret Archetypes to attach to player backstories
SECRET_ARCHETYPES = [
    {
        "id": "will_tamperer",
        "title_suffix": "The Estranged Heir",
        "secret": "Julian informed you earlier that he was cutting you from his will. At 10:15 PM, you slipped into his desk and swapped his fountain pen with one filled with invisible ink.",
        "goal": "Ensure no one accepts the validity of any document signed on the night of his death.",
        "incriminating_hint": "Gloves stained with dark indigo ink."
    },
    {
        "id": "physician_sedative",
        "title_suffix": "The Family Physician",
        "secret": "Julian discovered you had been falsifying medical ledgers. Desperate to keep him from talking, you slipped a heavy dose of laudanum sedative into his midnight tea tray.",
        "goal": "Ensure no one inspects the tea service before the cups are cleared.",
        "incriminating_hint": "An empty medicinal glass vial found in the hallway wastebasket."
    },
    {
        "id": "trust_skimmer",
        "title_suffix": "The Estate Trustee",
        "secret": "You have been skimming money from the family trusts. You brought a forged amendment granting yourself a £50,000 administration fee.",
        "goal": "Convince the other guests that the will found in your briefcase is the legitimate one.",
        "incriminating_hint": "Seen holding the official estate wax seal with sweating hands at 11:20 PM."
    },
    {
        "id": "art_dealer",
        "title_suffix": "The Relic Appraiser",
        "secret": "Julian stiffed you on a massive appraisal fee. At 10:45 PM, you picked the display cabinet lock in the drawing room to reclaim a priceless gilded Byzantine dagger.",
        "goal": "Keep anyone from searching your traveling trunk where the dagger is hidden.",
        "incriminating_hint": "Glass shards from the display cabinet stuck in your sleeve."
    },
    {
        "id": "archivist_fire",
        "title_suffix": "The Private Archivist",
        "secret": "Julian possessed black-ledger records proving you sold private family secrets. At 11:00 PM, you threw those ledger pages into the study hearth.",
        "goal": "Prevent anyone from inspecting the charred ashes inside the study fireplace.",
        "incriminating_hint": "Smelling strongly of woodsmoke and ash; singed paper in your cuffs."
    },
    {
        "id": "socialite_threat",
        "title_suffix": "The High-Society Ward",
        "secret": "You owe thousands in debt to Julian. You had a screaming argument with him on the terrace at 11:25 PM, ending with you shouting that you wished he would drop dead.",
        "goal": "Fabricate an alibi that keeps you far away from the terrace between 11:20 and 11:40 PM.",
        "incriminating_hint": "A torn silk thread matching your evening scarf caught on the broken staircase railing."
    },
    {
        "id": "botanist_digitalis",
        "title_suffix": "The Botanical Scholar",
        "secret": "You slipped powdered foxglove into the port wine decanter, hoping Julian would fall ill and cancel his speech before announcing your research patent as his own.",
        "goal": "Deflect suspicion onto the Physician when poison symptoms are discussed.",
        "incriminating_hint": "Gardening gloves with dried purple foxglove petals in your coat pocket."
    },
    {
        "id": "chauffeur_wires",
        "title_suffix": "The Veteran Chauffeur",
        "secret": "You planned to steal the vintage Rolls-Royce to flee the country from old debts. You cut the landline telephone wires in the cellar at 11:10 PM so the estate gates couldn't be locked remotely.",
        "goal": "Hide the fact that the telephone lines are severed and the cars are immobilized.",
        "incriminating_hint": "Heavy wire cutters coated in copper shavings tucked in your boots."
    }
]

# Room Pools: Major Clues, Lore Details, and Empty Atmospheres
ROOM_POOLS = {
    "study": {
        "major": [
            ("Scorched Document Scrap", "In the grate of the hearth lies a burned scrap of paper bearing the signature '...forever disinherit my...'."),
            ("Indigo Ink Splatter", "Under the desk blotter, you discover a fresh splatter of indigo disappearing ink."),
            ("Torn Ledger Page", "Tucked inside a hollow legal volume is an accounting sheet showing an unauthorized £50,000 withdrawal.")
        ],
        "lore": [
            ("Portrait of Julian", "Julian's oil portrait scowls down at the room. Behind the canvas is only stone wall and spiderwebs."),
            ("Ticking Brass Clock", "The heavy mantel clock reads 11:42, stopped by a broken pendulum spring."),
            ("Crystal Decanter", "An empty crystal decanter smelling of aged sherry and pipe tobacco.")
        ],
        "empty": [
            "You sift through dry legal receipts and stationery. Nothing of interest catches your eye.",
            "Cold drafts seep through the heavy drapes. The desk drawers hold only blank parchment."
        ]
    },
    "library": {
        "major": [
            ("Dropped Estate Seal", "Wedged behind a row of leather-bound encyclopedias is the heavy brass seal of Ravenscroft Hall."),
            ("Anonymous Threat Letter", "Folded inside a book on criminal jurisprudence: 'Sign the papers tonight, or your sins will be laid bare in London.'"),
            ("Cut Telephone Cord", "Behind the reading desk, the auxiliary telephone wire has been cleanly snipped.")
        ],
        "lore": [
            ("Old Estate Map", "An architectural sketch of Ravenscroft Hall from 1888. Several domestic service passages are marked in faded red ink."),
            ("Pressed Black Rose", "Inside a volume of romantic poetry rests a dried black rose labeled 'September 1921'."),
            ("Rolling Ladder", "The wooden library ladder stands slightly ajar near the upper history shelves.")
        ],
        "empty": [
            "Miles of dusty theological treatises. You find only dust motes floating in the candle glow.",
            "You check behind several rows of Shakespeare folios. Nothing hidden here."
        ]
    },
    "conservatory": {
        "major": [
            ("Muddy Boot Impression", "Near the glass terrace doors, a distinct boot print tracking coastal mud and dried foxglove leaves."),
            ("Torn Silk Thread", "Snagged on the thorny stem of a Victorian orchid is a delicate strand of fine silk."),
            ("Broken Window Latch", "The iron latch on the storm door has been forced from the outside with a blunt metal pry bar.")
        ],
        "lore": [
            ("Rare Digitalis Pots", "A shelf of medicinal purple foxglove, carefully cultivated in terracotta planters."),
            ("Rain Against Glass", "Torrential rain beats fiercely against the domed glass ceiling, threatening to drown out all sound."),
            ("Forgotten Watering Can", "An old brass watering can, half full of stagnant rainwater.")
        ],
        "empty": [
            "Dense ferns and wet soil. You find nothing unusual among the potting benches.",
            "You search beneath the iron wicker benches. Just cobwebs and dry leaves."
        ]
    },
    "dining": {
        "major": [
            ("Tainted Port Decanter", "The crystal decanter of vintage port has a strange, bitter almond residue clinging to its silver stopper."),
            ("Discarded Tea Saucer", "Under the sideboard lies a teacup with dark sediment settled at the bottom."),
            ("Shattered Relic Stand", "On the credenza, a velvet-lined display stand sits empty, surrounded by minute shards of glass.")
        ],
        "lore": [
            ("Seating Cards", "Eight formal calligraphy place cards arranged around the 20-foot mahogany table."),
            ("Cold Roast Beef", "A silver platter of roast beef has been picked over, with several slices missing."),
            ("Extinguished Chandelier", "The grand chandelier above the table has two candles burned completely down to the iron cup.")
        ],
        "empty": [
            "Silverware, fine porcelain, and embroidered linen. Nothing suspicious here.",
            "You check under the long damask tablecloth. Only polished floorboards."
        ]
    },
    "cellar": {
        "major": [
            ("Snipped Master Line", "The main copper telephone conduit entering the estate has been sheared with heavy wire cutters."),
            ("Empty Laudanum Bottle", "Tucked into an empty vintage champagne bin is a brown apothecary bottle labeled 'Concentrated Tincture'."),
            ("Heavy Muddy Footwear", "Hidden beneath a coal sack is an old pair of size 11 work boots caked in fresh graveyard mud.")
        ],
        "lore": [
            ("Roaring Furnace", "The coal furnace radiates a low, oppressive heat through the stone cellar."),
            ("Wine Racks of 1890", "Dozens of dusty bottles untouched for half a century."),
            ("Draft Near the Wall", "A persistent cold breeze whispers from a stone seam behind the north cask.")
        ],
        "empty": [
            "Damp stone, cobwebs, and the smell of sulfur from the coal chute. Nothing found.",
            "You tap along the brick cellar arches. Solid stone everywhere."
        ]
    },
    "bedroom": {
        "major": [
            ("Missing Emerald Box", "On Julian's mahogany dresser sits an empty velvet jewel box labeled 'The Blackwood Emerald'."),
            ("Cracked Wall Safe", "The concealed wall safe behind the vanity mirror hangs slightly open, empty of cash."),
            ("Stained Nightshirt", "A linen nightshirt draped across the chaise lounge with a distinct smudge of soot across the collar.")
        ],
        "lore": [
            ("Prescription Pills", "A small bottle of heart medicine prescribed by the family doctor, dated three weeks ago."),
            ("Four-Poster Canopy", "Heavy velvet bed curtains drawn tight against the storm."),
            ("Open Window Shutter", "The rain-slicked window overlooks the sheer drop toward the Atlantic breakers.")
        ],
        "empty": [
            "Lavender-scented linen and polished mahogany. You find nothing out of place.",
            "You look under the heavy bedstead. Only clean carpet."
        ]
    },
    "kitchen": {
        "major": [
            ("Dumbwaiter Scratches", "Inside the wooden dumbwaiter hoist, fresh fingernail scratches and scraped mortar indicate recent human passage."),
            ("Missing Carving Poker", "The iron carving set by the spit is missing its long, heavy poker."),
            ("Torn Service Apron", "Stuffed into the laundry hamper is a vintage servant's vest bearing the faded monogram 'B.F.'")
        ],
        "lore": [
            ("Boiling Tea Kettle", "A cast-iron kettle purring quietly over the banked embers of the range."),
            ("Freshly Baked Scones", "A basket of scones covered with a clean linen cloth, warm to the touch."),
            ("Chalkboard Chore Slate", "A list of estate duties written in Mrs. Gable's hurried, rounded handwriting.")
        ],
        "empty": [
            "Pots, copper pans, and jars of pickled plums. Nothing suspicious in the pantry.",
            "You inspect the spice rack and flour bins. All undisturbed."
        ]
    },
    "attic": {
        "major": [
            ("Makeshift Straw Bed", "Behind the water cistern is a concealed straw mattress with an old wool blanket and empty tins of food."),
            ("Antique Portrait of Barnaby", "A framed staff photo from 1920: Barnaby Finch, Head Steward, standing beside a youthful Julian."),
            ("Master Skeleton Key", "Lying beside the cot is an iron key marked 'All Domestic Corridors'.")
        ],
        "lore": [
            ("Whirring Clockwork", "The massive iron gears of the estate tower clock click and groan with every passing minute."),
            ("Discarded Steamer Trunks", "Cobwebbed luggage containing Victorian clothes smelling of mothballs."),
            ("Dust Motes in Moonlight", "A beam of storm light piercing through the cracked louvers.")
        ],
        "empty": [
            "Decades of dust, broken furniture, and forgotten crates. Nothing useful here.",
            "You sift through old newspaper stacks from 1910. Just yellowed paper."
        ]
    },
    "carriage": {
        "major": [
            ("Fresh Tire Ruts", "In the soft gravel outside the coach door, deep tire marks show a vehicle left in haste during the early evening."),
            ("Cut Ignition Cables", "Under the hood of the estate motorcar, the distributor cap has been pulled loose."),
            ("Toolbox Shaved Lead", "On the workbench, metal filings and wire shavings surround an open mechanic's tool kit.")
        ],
        "lore": [
            ("Smell of Kerosene", "Racks of motor fuel, motor oil, and storm lanterns."),
            ("Rain on Tin Roof", "The deafening roar of water cascading off the corrugated iron roof."),
            ("Old Horse Carriage", "An antique black brougham carriage covered in dust sheets.")
        ],
        "empty": [
            "Tire irons, greasy rags, and oil drums. Nothing remarkable.",
            "You search the back of the carriage. Only dry leather upholstery."
        ]
    },
    "crypt": {
        "major": [
            ("Bloodied Iron Poker", "Concealed inside an open stone niche lies the heavy iron fireplace poker, its tip dark with dried matter."),
            ("The Blackwood Emerald", "Wrapped in a greasy handkerchief inside an empty sarcophagus is Julian's stolen emerald ring!"),
            ("Hidden Wall Lever", "Behind the central stone tomb, a rusty iron bar unlatches a subterranean staircase leading upward into the manor!")
        ],
        "lore": [
            ("Chilled Tomb Air", "The freezing damp of subterranean stone. Your breath mists in the gloom."),
            ("Ravenscroft Ancestors", "Carved stone effigies of knights and ladies resting in eternal silence."),
            ("Flickering Candle Stump", "A tallow candle that burned out only hours ago.")
        ],
        "empty": [
            "Ancient stone, wet moss, and silence. No clues uncovered here.",
            "You inspect the stone memorials. All inscriptions are weathered and undisturbed."
        ]
    },
    "radio": {
        "major": [
            ("Coroner's Telegram Transcript", "A decoded radio wire: 'Autopsy reveals skull fracture prior to fall. Fatal trauma caused by blunt iron rod. Sedatives non-lethal.'"),
            ("Police Dispatch Notice", "Mainland record: 'Barnaby Finch, former convict, reported absconded from county asylum three months ago.'"),
            ("Severed Aerial Cable", "The external radio antenna shows signs of manual tampering before being temporarily jury-rigged.")
        ],
        "lore": [
            ("Static Hiss", "A wall-mounted vacuum-tube receiver emitting constant maritime squall static."),
            ("Telegraph Key", "A polished brass telegraph paddle with spare battery jars."),
            ("Weather Map", "A hand-drawn coastal barometer chart showing pressure bottoming out.")
        ],
        "empty": [
            "Vacuum tubes glow warm amber. The airwaves are silent for now.",
            "You search the operator logbook. Only standard maritime weather reports."
        ]
    }
}

# 14-Day Morning Dispatches
DISPATCHES = {
    1: {
        "headline": "THE ARRIVAL AT RAVENSCROFT HALL",
        "body": "Welcome, esteemed guests. The Solstice storm has arrived, washing out the coastal bridge to the mainland. Lord Julian Ravenscroft bids you make yourselves at home in the public rooms. Please register your arrival with Giles at the front gates.",
        "unlocks": []
    },
    2: {
        "headline": "TRAGEDY ON THE GRAND STAIRCASE",
        "body": "At 11:42 PM last night, Lord Julian was discovered deceased at the foot of the Grand Staircase. The front gates are locked. The estate is now an active crime scene. All guests are implored to begin searching for the truth.",
        "unlocks": []
    },
    3: {
        "headline": "THE SCENT OF INK & ASH",
        "body": "Giles notes that several documents in the Grand Study were disturbed overnight. Ink stains and scorched paper fragments suggest not all guests spent their evening sleeping.",
        "unlocks": []
    },
    4: {
        "headline": "MURMURS IN THE CONSERVATORY",
        "body": "A broken window latch was discovered in the conservatory. Was someone attempting to flee the manor in the middle of the tempest, or sneaking back inside?",
        "unlocks": []
    },
    5: {
        "headline": "THE DOMESTIC WING UNSEALED",
        "body": "By order of the estate steward, the private domestic quarters are now opened for inquiry. Guests may now enter #the-wine-cellar, #julians-bedroom, and #the-kitchen-and-pantry.",
        "unlocks": ["the-wine-cellar", "julians-bedroom", "the-kitchen-and-pantry"]
    },
    6: {
        "headline": "THE SEDATIVE MYSTERY",
        "body": "Mrs. Gable discovered an empty medicine vial discarded in the corridor. Whispers are circulating: was Lord Julian poisoned before his fatal tumble down the stairs?",
        "unlocks": []
    },
    7: {
        "headline": "THE WEEKEND FIRESIDE DEBATE",
        "body": "The storm shows no sign of abating. Guests are encouraged to gather in the Grand Parlor tonight to challenge one another's alibis and compare notes.",
        "unlocks": []
    },
    8: {
        "headline": "THE MAINLAND RADIO CRACKLES",
        "body": "Constable Higgins reports through static that preliminary medical analysis shows the fall down the stairs was NOT the cause of death. Julian was struck on the head beforehand!",
        "unlocks": []
    },
    9: {
        "headline": "THE RESTRICTED GROUNDS UNLOCKED",
        "body": "A set of iron keys has been located. The outer and restricted grounds are now accessible: #the-clocktower-attic, #the-carriage-house, #the-family-crypt, and #the-radio-room are OPEN.",
        "unlocks": ["the-clocktower-attic", "the-carriage-house", "the-family-crypt", "the-radio-room"]
    },
    10: {
        "headline": "THE PHANTOM IN THE PANTRY",
        "body": "Mrs. Gable is in hysterics. Tins of beef, salt pork, and bread have been vanishing from the locked larder for weeks. Someone has been living in the shadows of this house.",
        "unlocks": []
    },
    11: {
        "headline": "THE NAME IN THE ARCHIVES",
        "body": "Mainland records transmitted via shortwave radio identify an estranged individual: Barnaby Finch, disgraced head steward cast out by Julian five years ago. He was never found dead.",
        "unlocks": []
    },
    12: {
        "headline": "THE DUMBWAITER PASSAGES",
        "body": "Scuff marks inside the walls indicate secret service tunnels connect the attic, kitchen, and crypt directly to the grandfather clock in the gallery where Julian fell.",
        "unlocks": []
    },
    13: {
        "headline": "THE FINAL EVIDENCE COLLECTED",
        "body": "Tomorrow night at 8:00 PM, the formal inquest begins. Review your clues, settle your alibis, and prepare your final accusations.",
        "unlocks": []
    },
    14: {
        "headline": "THE GRAND INQUEST (TONIGHT AT 8:00 PM)",
        "body": "Tonight in the Grand Parlor voice channel, all guests will submit their formal ballots. The true killer will be unmasked!",
        "unlocks": []
    }
}

# Pre-Murder Room Atmospheres (Day 1 - Julian is still alive upstairs before dinner)
PRE_MURDER_ROOM_ATMOSPHERES = {
    "study": (
        "A warm cedar fire crackles steadily in the black marble hearth, filling Lord Julian's study with the rich scent of calfskin ledgers and fine Turkish tobacco. "
        "Outside, the Solstice squall is just beginning to lash the coastal cliffs, rattling the tall diamond-paned bay windows. "
        "Julian's colossal mahogany desk is stacked with freshly drafted legal folios awaiting tonight's dinner announcement. "
        "By the hearth armchair, Dr. Abernathy warms his hands and reviews a set of medical charts while an antique grandfather clock ticks with a steady, tranquil resonance."
    ),
    "library": (
        "Towering floor-to-ceiling oak bookshelves swallow the howling wind outside, creating a warm, scholarly refuge from the Equinox storm. "
        "A rolling brass ladder leans against the upper gallery, and a green-shaded banker's lamp casts an inviting emerald glow over a reading table where evening newspapers and estate histories have been laid out for arriving guests."
    ),
    "conservatory": (
        "A humid, lush sanctuary under vaulted Victorian iron and glass. Rare orchids and ferns glisten with mist as the rising Atlantic storm drums against the glass dome above. "
        "Lanterns hang from the wrought-iron arches, illuminating the stone pathways and terracotta planters while the outer terrace doors remain securely latched against the gale."
    ),
    "dining": (
        "The twenty-foot banquet table of polished black walnut is immaculate, set with gleaming silver candelabras, crystal decanters of vintage port, and eight calligraphy place cards for tonight's Solstice dinner. "
        "Warm savory aromas of roast beef and rosemary waft from the service doors. Above the mantelpiece, the grand oil portrait of Lord Julian Ravenscroft presides over the hall in expectant silence."
    )
}

# Rich Evocative Atmospheric Descriptions for Room Headers (Post-Murder Crime Scene State)
ROOM_ATMOSPHERES = {
    "study": (
        "The air in the study is thick with the scent of calfskin ledgers, cold woodsmoke, and shattered crystal. "
        "At the foot of the stairs leading into the study, a splintered oak banister and a dark stain on the Persian rug mark where Lord Julian fell at 11:42 PM. "
        "A dying fire smolders in the black marble hearth, casting long, wavering shadows across Julian’s colossal mahogany desk. "
        "The high-backed leather chair sits pushed askew in haste, while the antique grandfather clock stands frozen at the exact minute of the blackout."
    ),
    "library": (
        "Towering floor-to-ceiling oak bookshelves swallow nearly all sound, creating a cavernous, scholarly hush. "
        "A rolling brass ladder leans against the upper balcony, where hundreds of leather-bound folios recline under centuries of dust. "
        "The scent of dry parchment, melted beeswax, and old leather hangs heavy. Rain lashes against the leaded stained-glass skylight far above, "
        "and a green-shaded banker's lamp casts an uneasy emerald glow over a sprawling reading table covered in open estate blueprints."
    ),
    "conservatory": (
        "A humid, overgrown jungle under vaulted Victorian iron and glass. Overgrown ferns and rare night-blooming orchids drape over rusted benches. "
        "Condensation drips steadily from the high glass dome, echoing like solitary footsteps among the terracotta planters. "
        "The smell of damp soil and crushed vegetation is overwhelming. Near the far glass terrace door, a cold draft cuts through the moisture—the bolt has been forced, and wet leaves lie scattered across the tile."
    ),
    "dining": (
        "A twenty-foot banquet table of polished black walnut dominates the hall, surrounded by eight high-backed chairs standing like silent sentinels. "
        "Silver candelabras hold guttering tapers, shedding pools of amber light across half-empty crystal goblets and picked-over silver platters of cold roast beef. "
        "A faint aroma of spiced port and bitter almonds lingers over the sideboard. The grand portrait of Lord Julian looms at the head of the room, his painted eyes catching every flicker of candle flame."
    ),
    "cellar": (
        "Subterranean chill immediately seeps through your clothing. Massive brick arches support the estate's foundations, flanked by iron racks of dust-coated vintage wines. "
        "In the far alcove, the coal furnace glows a dull, threatening red, breathing hot iron air and low mechanical groans into the gloom. "
        "Water drips rhythmically from a corroded copper pipe into a stone drain. Near the north wall, behind an empty vintage bin, a strange, persistent draft breathes from a seam in the masonry."
    ),
    "bedroom": (
        "A heavy four-poster mahogany bed with deep burgundy velvet drapes dominates Julian's private sanctum. "
        "One rain-slicked window shutter has been left unlatched, banging rhythmically against the stone sill as freezing coastal spray mists the oriental rug. "
        "On the bedside nightstand, pill vials and a cold cup of chamomile tea sit beside an open drawer. The large ornate vanity mirror hangs slightly crooked, revealing the dark rectangular void of an open wall safe behind it."
    ),
    "kitchen": (
        "A sprawling flagstone chamber bathed in the warm, flickering radiance of a roaring cast-iron cooking range. "
        "Rows of polished copper saucepans gleam against the whitewashed walls, alongside bundles of drying rosemary, thyme, and lavender. "
        "The comforting aroma of fresh milk bread and simmering broth cannot entirely conceal a subtle underlying tension: by the service larder, the heavy wooden dumbwaiter shaft creaks faintly inside the stone chimney breast, as if carrying weight."
    ),
    "attic": (
        "Sprawling directly beneath the manor's slate roof, this forgotten labyrinth is choked with decades of cobwebbed steamer trunks, discarded portrait frames, and shrouded furniture. "
        "The deafening, hypnotic grinding and clicking of the estate clockwork mechanism echoes from the wooden tower shaft above. "
        "Storm wind howls through cracked wooden louvers, stirring thick dust motes. In the far shadows behind the water cistern, a makeshift cot of fresh straw and empty food tins suggests an uninvited guest."
    ),
    "carriage": (
        "A cavernous workshop smelling sharply of motor spirit, grease, and rain-soaked cedar. "
        "Rain hammers on the corrugated tin roof like machine-gun fire. Lord Julian's pristine black Rolls-Royce sits in the center of the gravel floor, its hood unlatched and engine cables hanging loose. "
        "On the heavy timber workbench, oily mechanic tools lie scattered beside an open lantern, surrounded by fresh copper wire shavings."
    ),
    "crypt": (
        "Ancient, freezing stone walls carved directly into the seaside cliffside beneath Ravenscroft Hall. "
        "Your breath blooms in thick white clouds against the pitch-black subterranean chill. Elaborate stone sarcophagi of the Ravenscroft lineage rest in solemn tiers, their sculpted effigies watching with eroded limestone eyes. "
        "The scent of ancient dust, salt sea air, and fresh candle wax fills the vault. Propped against an empty stone burial niche rests a heavy iron bar."
    ),
    "radio": (
        "A cramped, wood-paneled room tucked inside the highest eaves of the estate tower. "
        "A high-frequency maritime radio receiver hums with amber vacuum-tube warmth, filling the room with the dry static hiss of Atlantic storm frequencies. "
        "A brass telegraph key sits beside stacks of signal logbooks and weather barometer maps. Every few minutes, through the sea noise, a voice crackles faintly across the airwaves: 'Constable Higgins here... do you read me...?'"
    )
}

# The 14 Daily Parlor Polls (Debate Igniters)
PARLOR_POLLS = {
    1: {
        "question": "⛈️ SOLSTICE ARRIVAL POLL: The coastal bridge has washed out and Lord Julian has secluded himself upstairs before dinner. What troubles you most about Ravenscroft Hall tonight?",
        "options": [
            "The violent Atlantic squall severing the telegraph wires",
            "Lord Julian's sudden, secretive summons to amend his Will",
            "The eerie drafts and scratching noises behind the wainscoting",
            "The heavy iron locks bolted across the outer estate gates"
        ]
    },
    2: {
        "question": "⚖️ ESTATE POLL: Whose whereabouts between 10:00 PM and midnight appear the most suspicious?",
        "options": [
            "Those claiming to have been asleep in their bedchambers",
            "Those seen near the rain-swept terrace doors",
            "Those lingering alone in the library",
            "Those wandering near the domestic service corridors"
        ]
    },
    3: {
        "question": "📜 ESTATE POLL: A will document was tampered with. What motive seems most plausible?",
        "options": [
            "A guest burdened by desperate, ruinous personal debts",
            "A guest whose secret past Julian threatened to expose",
            "A guest seeking to reclaim a family heirloom or patent",
            "An outside confederate aided by an accomplice inside"
        ]
    },
    4: {
        "question": "🧳 ESTATE POLL: Should the guests consent to an immediate mutual search of all traveling luggage?",
        "options": [
            "Yes — Complete transparency now!",
            "No — An outrageous violation of personal privacy!",
            "Only under Giles's strict personal supervision",
            "Only once the estate grounds are secured from the squall"
        ]
    },
    5: {
        "question": "🚪 ESTATE POLL: The Wine Cellar & Domestic Wing are now unlocked. Where should our inquiry focus first?",
        "options": [
            "The Coal Furnace in the Cellar",
            "Julian's Bedside Safe",
            "The Kitchen Dumbwaiter",
            "The Telephone Wires"
        ]
    },
    6: {
        "question": "🧪 ESTATE POLL: Traces of sedative and toxin have been found. Which explanation do you believe?",
        "options": [
            "Someone quietly dosed the dinner port wine carafe",
            "Someone laced the bedtime chamomile tea service",
            "Julian was medicating himself in secret before the fall",
            "An intruder slipped poison into the kitchen larder"
        ]
    },
    7: {
        "question": "🔥 MIDWAY POLL: If you had to name a prime suspect right now, who would you lock in the cellar?",
        "options": [
            "The guest whose story has changed twice",
            "The guest who has spent the most candles searching alone",
            "The guest who keeps whispering to the estate staff",
            "Nobody — There is an uninvited squatter living in the walls!"
        ]
    },
    8: {
        "question": "🩸 ESTATE POLL: Autopsy reveals Julian died of blunt head trauma, not the fall. Was this premeditated murder?",
        "options": [
            "Cold premeditated murder planned well in advance",
            "A panicked crime of passion or sudden rage",
            "An accidental struggle over stolen property gone wrong",
            "The work of a ruthless outside intruder"
        ]
    },
    9: {
        "question": "🗝️ ESTATE POLL: The Crypt and Clocktower are open. What secret will prove most damning?",
        "options": [
            "The signs of squatter habitation in the Attic",
            "The Missing Iron Fireplace Poker",
            "The Stolen Blackwood Emerald",
            "The Secret Subterranean Passages"
        ]
    },
    10: {
        "question": "🍞 ESTATE POLL: Tins of food have been stolen from the larder for weeks. Does someone live in the walls?",
        "options": [
            "Yes — An uninvited squatter lives in the crawlspaces!",
            "No — One of the guests is hoarding provisions in their room",
            "Mrs. Gable is miscounting her stores",
            "It is an elaborate diversion staged by the killer"
        ]
    },
    11: {
        "question": "👤 ESTATE POLL: Mainland records name Barnaby Finch. Is the disgraced former steward among us?",
        "options": [
            "He is hiding in the secret service passages",
            "He has an accomplice among the guests",
            "He already fled the island by boat",
            "He is seeking total vengeance on the family"
        ]
    },
    12: {
        "question": "🕰️ ESTATE POLL: The grandfather clock conceals a hidden panel. Who discovered it first?",
        "options": [
            "One of the guests during their candle searches",
            "Barnaby Finch during his years as steward",
            "Giles the Butler during his evening rounds",
            "Lord Julian before his death"
        ]
    },
    13: {
        "question": "📋 INQUEST PREP: With the inquest tomorrow, how confident are you in your final theory?",
        "options": [
            "100% — I know killer, weapon, and motive",
            "Fairly confident — A few minor details hazy",
            "Suspicious of two people still",
            "Completely baffled!"
        ]
    },
    14: {
        "question": "🏆 FINAL CONSENSUS: Who will be crowned Master Sleuth of Ravenscroft tonight?",
        "options": [
            "The sharpest detective among us",
            "The guest who guarded their secrets best",
            "Nobody — Barnaby Finch outsmarted everyone!",
            "Giles the Butler"
        ]
    }
}

def get_parlor_poll(day: int) -> dict:
    """
    Returns the daily parlor poll. For the Midway Prime Suspect poll (Day 7),
    if players have registered in the database, their custom character titles
    and display names are injected dynamically into the voting options!
    """
    poll_data = PARLOR_POLLS.get(day, PARLOR_POLLS[1]).copy()
    
    if day == 7:
        try:
            from database import get_all_players
            players = [dict(row) for row in get_all_players()]
            registered = [p for p in players if p.get("interview_step", 0) >= 4]
            if registered:
                custom_options = []
                for p in registered:
                    title = p.get("character_title") or "Mysterious Guest"
                    name = p.get("display_name") or p.get("username") or "Guest"
                    label = f"{title} ({name})"
                    if len(label) > 95:
                        label = label[:92] + "..."
                    custom_options.append(label)
                if custom_options:
                    poll_data["options"] = custom_options[:25]
        except Exception:
            pass
            
    return poll_data
