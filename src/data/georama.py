"""Georama request data per area.

Each area has a list of (house_name, [request_descriptions], flag_index).
flag_index is the index into the CommonMenuAtoraInfo satisfaction array.

Content sourced from StrategyWiki (CC BY-SA 4.0), rephrased for compliance.
"""

# Area 0: Norune Village — flags 0-7 (contiguous)
NORUNE = [
    ("My House",        ["Must face east"],                                  0),
    ("Macho's House",   ["Near dungeon entrance corner"],                    1),
    ("Laura's House",   ["Not close to the Mayor"],                          2),
    ("Paige's House",   ["Close to the pond"],                               3),
    ("Claude's House",  ["Close to Alnet's House"],                          4),
    ("Hag's House",     ["In front of Dran's Windmill", "Dran must be rescued"], 5),
    ("Alnet's House",   ["Not close to Macho's House"],                      6),
    ("Gaffer's Buggy",  ["At least 2 houses nearby"],                        7),
]

# Area 1: Matataki Village — flag indices from MatatagiRequest disassembly
# Parts 0-7 contiguous, part 14 (Wise Owl) and river chain (16, Treant) non-contiguous
# Confirmed via entering houses: Kye&Momo=game ID 3, Couscous=game ID 5
# Part 3 checks proximity to part type 14 (Wise Owl) = "Close to Wise Owl Shop"
# Part 6 checks proximity to part 3 (Kye&Momo) = "Near Kye & Momo's House"
# Parts 5,7 use GetAlt_i (altitude) = "On top of Earth A or B"
# Part 14 counts surrounding water tiles ≥14 = "Surrounded by river"
MATATAKI = [
    ("Pao's House",       ["Close to Peanut Pond"],                          0),
    ("Cacao's House",     ["Surrounded by trees (4+)"],                      1),
    ("Bunbuku's House",   ["Close to a water mill"],                         2),
    ("Kye & Momo's House",["Close to Wise Owl Shop"],                        3),
    ("Baron's House",     ["Close to the waterfall"],                        4),
    ("Couscous' House",   ["On top of Earth A or B"],                        5),
    ("Gob's House",       ["Near Kye & Momo's House"],                       6),
    ("Mushroom House",    ["On top of Earth A or B"],                        7),
    ("Wise Owl Shop",     ["Surrounded by river"],                          14),
    ("Treant's River",    ["Connect waterfall to Treant's cave"],           16),
]

# Area 2: Queens — flag indices from QueensRequest disassembly
# Part 0=Ruty (ocean rect), Part 1=Suzy (near fountain/part10), Part 2=Lana (near part8=King)
# Part 3=Jack (near part1=Suzy), Part 4=Joker (not near part9=Sheriff) → flag 4
# Part 5=Divining (GetRotY snake facing) → flag 4 (shared with Joker)
# Part 6=Cathedral (GetRotY+near part11=Tower) → flag 5
# Part 7=Basker (high place) → flag 6
# Part 8=King (road a1=0xD around it) → flag 7
# Part 9=Sheriff (near part8=King) → flags 8+9
QUEENS = [
    ("Ruty's Store",      ["Close to the ocean"],                            0),
    ("Suzy's Store",      ["Near the fountain"],                             1),
    ("Lana's Store",      ["Near King's Hideout"],                           2),
    ("Jack's Store",      ["Near Suzy's Store"],                             3),
    ("Joker's House",     ["Not near Sheriff's Office"],                     4),
    ("Divining House",    ["Snake facing east (away from ocean)"],           5),
    ("Cathedral",         ["Close to Leaning Tower", "Facing the ocean"],    6),
    ("Basker's Store",    ["In a high place (SE section)"],                  7),
    ("King's Hideout",    ["Road around it"],                                8),
    ("Sheriff's Office",  ["Close to King's Hideout"],                       9),
]

# Area 3: Muska Lacka — flag indices from MuskaRequest disassembly
# All houses face a totem pole: Pole A=part8, Pole B=part9, Pole C=part10
# Part 0=Chief Bonka (Pole A + GetCompEvent=close to temple) → flag 0
# Part 1=Enga (Pole C) → flag 1, Part 2=Brooke (Pole B) → flag 2
# Part 3=3 Sisters (Pole B + near part11=Oasis) → flag 3
# Part 4=Zabo (Pole B) → flag 4, Part 5=Jibubu (Pole C) → flag 5
# Part 6=Prisoner Cabin (Pole A + GetRotY=facing East) → flag 6
# Part 7=Toto (Pole A) → flag 7
# Part 10=Ungaga fixed position check → flag 10
MUSKA_LACKA = [
    ("Chief Bonka's House",  ["Face Totem Pole A", "Close to the temple"],   0),
    ("Enga's House",         ["Face Totem Pole C"],                          1),
    ("Brooke's House",       ["Face Totem Pole B"],                          2),
    ("3 Sisters' House",     ["Face Totem Pole B", "Near the Oasis"],        3),
    ("Zabo's House",         ["Face Totem Pole B"],                          4),
    ("Jibubu's House",       ["Face Totem Pole C"],                          5),
    ("Prisoner Cabin",       ["Face Totem Pole A", "Must face east"],        6),
    ("Toto's House",         ["Face Totem Pole A"],                          7),
    ("Ungaga's House",       ["Face Totem Pole C"],                         10),
]

AREAS = [NORUNE, MATATAKI, QUEENS, MUSKA_LACKA]
AREA_NAMES = ["Norune Village", "Matataki Village", "Queens", "Muska Lacka"]
