"""Georama request data per area.

Each area has a list of (house_name, [request_descriptions]).
House index matches the game's house ID for that area.
Completion base: 0x21D19C58 + house_id * 0xE8
Individual parts: base + 0x28 + part_index * 0x20

Content sourced from StrategyWiki (CC BY-SA 4.0), rephrased for compliance.
"""

# Area 0: Norune Village (8 houses, indices 0-7)
NORUNE = [
    ("My House",        ["Must face east"]),
    ("Macho's House",   ["Near dungeon entrance corner"]),
    ("Laura's House",   ["Not close to the Mayor"]),
    ("Paige's House",   ["Close to the pond"]),
    ("Claude's House",  ["Close to Alnet's House"]),
    ("Hag's House",     ["In front of Dran's Windmill", "Dran must be rescued"]),
    ("Alnet's House",   ["Not close to Macho's House"]),
    ("Gaffer's Buggy",  ["At least 2 houses nearby"]),
]

# Area 1: Matataki Village (10 houses, indices 0-9)
MATATAKI = [
    ("Wise Owl Shop",     ["Surrounded by river"]),
    ("Cacao's House",     ["Surrounded by trees (4+)"]),
    ("Baron's House",     ["Close to the waterfall"]),
    ("Pao's House",       ["Close to Peanut Pond"]),
    ("Bunbuku's House",   ["Close to a water mill"]),
    ("Kye & Momo's House",["Close to Wise Owl Shop"]),
    ("Couscous' House",   ["On top of Earth A or B"]),
    ("Gob's House",       ["Near Kye & Momo's House"]),
    ("Mushroom House",    ["On top of Earth A or B"]),
    ("Treant's River",    ["Connect waterfall to Treant's cave"]),
]

# Area 2: Queens (10 houses, indices 0-9)
QUEENS = [
    ("Jack's Store",      ["Near Suzy's Store"]),
    ("King's Hideout",    ["Road around it"]),
    ("Sheriff's Office",  ["Close to King's Hideout"]),
    ("Joker's House",     ["Not near Sheriff's Office"]),
    ("Basker's Store",    ["In a high place (SE section)"]),
    ("Divining House",    ["Snake facing east (away from ocean)"]),
    ("Cathedral",         ["Close to Leaning Tower, facing ocean"]),
    ("Suzy's Store",      ["Near the fountain"]),
    ("Ruty's Store",      ["Close to the ocean"]),
    ("Lana's Store",      ["Near King's Hideout"]),
]

# Area 3: Muska Lacka (8 houses, indices 0-7)
# Requests are totem pole alignments + 3 extra
MUSKA_LACKA = [
    ("Chief Bonka's House",  ["Face Totem Pole A front", "Close to the temple"]),
    ("Toto's House",         ["Face Totem Pole A left"]),
    ("Prisoner Cabin",       ["Face Totem Pole A right", "Must face east"]),
    ("Brooke's House",       ["Face Totem Pole B front"]),
    ("3 Sisters' House",     ["Face Totem Pole B left", "Near the Oasis"]),
    ("Zabo's House",         ["Face Totem Pole B right"]),
    ("Jibubu's House",       ["Face Totem Pole C front"]),
    ("Enga's House",         ["Face Totem Pole C right"]),
]

AREAS = [NORUNE, MATATAKI, QUEENS, MUSKA_LACKA]
AREA_NAMES = ["Norune Village", "Matataki Village", "Queens", "Muska Lacka"]
