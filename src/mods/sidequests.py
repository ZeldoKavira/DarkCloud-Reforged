"""Side quest manager. Ported from SideQuestManager.cs."""

import logging

log = logging.getLogger(__name__)

# Quest active flag addresses
QUEST_FLAGS = {
    'macho': 0x21CE4402,
    'gob': 0x21CE4407,
    'jake': 0x21CE440C,
    'chief': 0x21CE4411,
}

# Inventory/storage scan addresses
FIRST_INV_SLOT = 0x21CDD8BA
FIRST_STORAGE_SLOT = 0x21CE21E8
FIRST_WEAPON_SLOT = 0x21CDDA58
FIRST_STORAGE_WEAPON = 0x21CE22D8


def check_item_quest_reward(mem, item_id, check_inv=True, check_storage=True):
    """Check if player has item_id in inventory and/or storage."""
    if check_inv:
        a = FIRST_INV_SLOT
        for _ in range(100):
            if mem.read_short(a) == item_id:
                return True
            a += 2
    if check_storage:
        a = FIRST_STORAGE_SLOT
        for _ in range(60):
            if mem.read_short(a) == item_id:
                return True
            a += 2
    return False


def check_weapon(mem, weapon_id, check_inv=True, check_storage=True):
    """Check if player has weapon_id in weapon slots and/or storage."""
    if check_inv:
        a = FIRST_WEAPON_SLOT
        for _ in range(10):
            if mem.read_short(a) == weapon_id:
                return True
            a += 0xF8
    if check_storage:
        a = FIRST_STORAGE_WEAPON
        for _ in range(30):
            if mem.read_short(a) == weapon_id:
                return True
            a += 0xF8
    return False


def check_current_dungeon_quests(mem):
    """Check which monster quests are active. Returns dict of quest→bool."""
    active = {}
    any_active = False
    for name, flag_addr in QUEST_FLAGS.items():
        val = mem.read_byte(flag_addr) == 1
        active[name] = val
        if val:
            any_active = True
    return active, any_active


def monster_quest_reward(mem):
    """Place feather (178) in first empty-ish inventory slot as quest reward."""
    a = FIRST_INV_SLOT
    for _ in range(102):
        if mem.read_short(a) > 60000:
            mem.write_short(a, 178)
            break
        a += 2
    # Mark reward given
    if mem.read_byte(0x21CE448C) == 0:
        mem.write_byte(0x21CE448C, 1)


def check_items_for_mc_quest(mem):
    """Check if player has the 4 specific items in order for MC quest."""
    a = FIRST_INV_SLOT
    expected = [167, 175, 150, 159]
    for item_id in expected:
        if mem.read_short(a) != item_id:
            return False
        a += 2
    return True


# ── Monster Quest Generation ──────────────────────────────────

DUNGEON_NAMES = ["Divine Beast Cave", "Wise Owl Forest", "Shipwreck",
                 "Sun & Moon Temple", "Moon Sea", "Gallery of Time", "Demon Shaft"]

_ENEMY_TABLES = {
    0: (["Master Jackets", "Dashers", "Mimics", "Dragons"], [1, 6, 35, 59]),
    1: (["Fliflis", "Earth Diggers", "Mimics", "Werewolves"], [8, 12, 79, 7]),
    2: (["Gunnys", "Gyons", "Mimics", "Pirate's Chariots"], [23, 24, 81, 25]),
    3: (["Golems", "Dunes", "Mimics", "Blue Dragons"], [30, 32, 37, 73]),
    4: (["Moon Diggers", "Space Gyons", "Mimics", "Crescent Barons"], [66, 72, 39, 76]),
    5: (["Rash Dashers", "Jokers", "Mimics", "Alexanders"], [63, 48, 83, 43]),
}

# Quest NPC → save addresses
QUEST_ADDRS = {
    12592: {'dng': 0x21CE4403, 'enemy_name': 0x21CE4404, 'counter': 0x21CE4405, 'enemy_id': 0x21CE4406},  # Macho
    13618: {'dng': 0x21CE4408, 'enemy_name': 0x21CE4409, 'counter': 0x21CE440A, 'enemy_id': 0x21CE440B},  # Gob
    13108: {'dng': 0x21CE440D, 'enemy_name': 0x21CE440E, 'counter': 0x21CE440F, 'enemy_id': 0x21CE4410},  # Jake
    14388: {'dng': 0x21CE4412, 'enemy_name': 0x21CE4413, 'counter': 0x21CE4414, 'enemy_id': 0x21CE4415},  # Chief Bonka
}

# Fishing quest NPC → save addresses
FISH_QUEST_ADDRS = {
    13872: {'type': 0x21CE4417, 'name': 0x21CE4418, 'id': 0x21CE4419, 'counter': 0x21CE441A,
            'min_size': 0x21CE441B, 'max_size': 0x21CE441C, 'orig_counter': 0x21CE441D},  # Pike
    13362: {'type': 0x21CE441F, 'name': 0x21CE4420, 'id': 0x21CE4421, 'counter': 0x21CE4422,
            'min_size': 0x21CE4423, 'max_size': 0x21CE4424, 'orig_counter': 0x21CE4425,
            'location': 0x21CE4426},  # Pao
    13363: {'type': 0x21CE4428, 'name': 0x21CE4429, 'id': 0x21CE442A, 'counter': 0x21CE442B,
            'min_size': 0x21CE442C, 'max_size': 0x21CE442D, 'orig_counter': 0x21CE442E,
            'complete_count': 0x21CE442F},  # Sam
    13109: {'type': 0x21CE4432, 'name': 0x21CE4433, 'id': 0x21CE4434, 'counter': 0x21CE4435,
            'min_size': 0x21CE4436, 'max_size': 0x21CE4437, 'orig_counter': 0x21CE4438},  # Devia
}

# Existing quest enemy IDs (to avoid duplicates)
_EXISTING_QUEST_ADDRS = [0x21CE4406, 0x21CE440B, 0x21CE4410, 0x21CE4415]


def generate_monster_quest(mem, npc_id):
    """Generate a random monster hunt quest for the given NPC."""
    import random

    addrs = QUEST_ADDRS.get(npc_id)
    if not addrs:
        return None

    # Count unlocked dungeons
    dngs = 0
    a = 0x21CDD80B
    for i in range(6):
        if mem.read_byte(a + i) != 255:
            dngs += 1
        else:
            break
    if dngs == 0:
        dngs = 1

    # Roll dungeon + enemy, avoiding duplicates
    for _ in range(60):
        dng = random.randint(0, dngs - 1)
        tbl = _ENEMY_TABLES.get(dng, _ENEMY_TABLES[0])
        names, ids = tbl
        idx = random.randint(0, len(names) - 1)

        # First quest is always Dashers
        if mem.read_byte(0x21CE448C) == 0 and npc_id == 12592:
            dng, idx = 0, 1

        eid = ids[idx]

        # Check for duplicate
        dup = any(mem.read_byte(ea) == eid for ea in _EXISTING_QUEST_ADDRS)
        if not dup:
            break

    kills = random.randint(8, 18)

    mem.write_byte(addrs['dng'], dng)
    mem.write_byte(addrs['enemy_name'], idx)
    mem.write_byte(addrs['counter'], kills)
    mem.write_byte(addrs['enemy_id'], eid)

    log.info("Generated quest: kill %d %s in %s", kills, names[idx], DUNGEON_NAMES[dng])
    return {'dungeon': DUNGEON_NAMES[dng], 'enemy': names[idx], 'kills': kills, 'enemy_id': eid}


def get_monster_quest_values(mem, npc_id):
    """Read current quest state for a monster quest NPC."""
    addrs = QUEST_ADDRS.get(npc_id)
    if not addrs:
        return None
    return {
        'dng_id': mem.read_byte(addrs['dng']),
        'enemy_idx': mem.read_byte(addrs['enemy_name']),
        'counter': mem.read_byte(addrs['counter']),
        'enemy_id': mem.read_byte(addrs['enemy_id']),
    }


# ── Fishing Quest Generation ─────────────────────────────────

_FISH_NAMES = {
    0: ["Nilers", "Gummies", "Nonkies", "Gobblers"],
    1: ["Baku Bakus", "Gobblers", "Tartons", "Umadakaras"],  # pond
    11: ["Baku Bakus", "Nonkies", "Gummies", "Mardan Garayan", "Baron Garayan"],  # waterfall
    2: ["Bobos", "Kajis", "Piccolys", "Bons", "Hamahamas"],
    3: ["Negies", "Dens", "Heelas", "Mardan Garayans", "Baron Garayan"],
}
_FISH_IDS = {
    0: [7, 6, 2, 1],
    1: [4, 1, 10, 9],
    11: [4, 2, 6, 5, 17],
    2: [0, 3, 11, 12, 13],
    3: [14, 15, 16, 5, 17],
}

LOCATION_ADDR = 0x202A2518

ALL_FISH = ["Bobo", "Gobbler", "Nonky", "Kaiji", "Baku Baku", "Mardan Garayan",
            "Gummy", "Niler", "null", "Umadakara", "Tarton", "Piccoly", "Bon",
            "Hamahama", "Negie", "Den", "Heela", "Baron Garayan"]


def generate_fishing_quest_one(mem, npc_id):
    """Generate a 'catch N fish' quest. Writes to NPC's quest addresses."""
    import random
    addrs = FISH_QUEST_ADDRS.get(npc_id)
    if not addrs:
        return
    loc = mem.read_byte(LOCATION_ADDR)

    if loc == 1:
        # Matataki: pond vs waterfall based on sub-location
        mat_loc = mem.read_byte(addrs.get('location', 0x21CE4426)) if 'location' in addrs else 0
        tbl = 11 if mat_loc >= 50 else 1
        names, ids = _FISH_NAMES[tbl], _FISH_IDS[tbl]
        idx = random.randint(0, len(names) - 1)
        if tbl == 11 and idx in (3, 4):
            idx = random.randint(0, len(names) - 1)
        count = 1 if (tbl == 11 and idx in (3, 4)) else random.randint(2, 3)
        mat_loc_id = 2 if idx == 0 else (1 if tbl == 11 else 0)
        if 'location' in addrs:
            mem.write_byte(addrs['location'], mat_loc_id)
    else:
        tbl = loc if loc in _FISH_NAMES else 0
        names, ids = _FISH_NAMES[tbl], _FISH_IDS[tbl]
        idx = random.randint(0, len(names) - 1)
        if tbl == 3 and idx in (3, 4):
            idx = random.randint(0, len(names) - 1)
        if tbl == 3 and idx == 4:
            count = 1
        elif tbl == 3 and idx == 3:
            count = random.randint(1, 3)
        else:
            count = random.randint(2, 3)

    mem.write_byte(addrs['name'], idx)
    mem.write_byte(addrs['id'], ids[idx])
    mem.write_byte(addrs['counter'], count)
    mem.write_byte(addrs['orig_counter'], count)
    log.info("Fishing quest: catch %d %s", count, names[idx])


def generate_fishing_quest_two(mem, npc_id):
    """Generate a 'catch fish of size X' quest."""
    import random
    addrs = FISH_QUEST_ADDRS.get(npc_id)
    if not addrs:
        return
    loc = mem.read_byte(LOCATION_ADDR)
    ranges = {0: (80, 141, 5), 1: (80, 141, 5), 2: (90, 161, 10), 3: (100, 181, 5)}
    lo, hi, margin = ranges.get(loc, (80, 141, 5))
    size = random.randint(lo, hi)
    mem.write_byte(addrs['min_size'], size)
    mem.write_byte(addrs['max_size'], size + margin)
    log.info("Fishing quest: catch fish size %d-%d", size, size + margin)


_LOCATION_NAMES = {0: "Norune Pond", 1: "Matataki", 2: "Queens", 3: "Muska Lacka"}

# Fishing quest NPC config: unlock flag, progress flag, location name
_FISH_NPC_CONFIG = {
    13872: {'unlock': 0x21CE4475, 'progress': 0x21CE4416, 'loc': "Norune Pond"},
    13362: {'unlock': 0x21CE4477, 'progress': 0x21CE441E, 'loc': "Matataki"},
    13363: {'unlock': 0x21CE4479, 'progress': 0x21CE4427, 'loc': "Queens"},
    13109: {'unlock': 0x21CE447B, 'progress': 0x21CE4431, 'loc': "Muska Lacka"},
}

def get_fishing_quest_dialogue(mem, npc_id):
    """Return dialogue for fishing quest NPC. Only generates quest data + returns text.
    State advancement (unlock/progress) is handled by _check_sidequest_dialogue."""
    import random
    cfg = _FISH_NPC_CONFIG.get(npc_id)
    if not cfg:
        return None
    addrs = FISH_QUEST_ADDRS.get(npc_id)
    if not addrs:
        return None

    if mem.read_byte(cfg['unlock']) != 1:
        return ("Oh, I bet you can already guess what^I have in store for you."
                "\xa4That's right, Fishing Quests!"
                "\xa4There are 2 types of fishing quests,^and whenever you talk to me,"
                "^I can assign you one of them."
                "\xa4I hope you like fishing!")

    progress = mem.read_byte(cfg['progress'])
    loc = cfg['loc']

    if progress == 0:
        # Generate new quest data (don't advance progress — CheckSideQuestDialogue does that)
        qtype = random.randint(0, 1)
        mem.write_byte(addrs['type'], qtype)
        if qtype == 0:
            generate_fishing_quest_one(mem, npc_id)
            name_idx = mem.read_byte(addrs['name'])
            area = mem.read_byte(LOCATION_ADDR)
            tbl = area if area in _FISH_NAMES else 0
            if area == 1 and 'location' in addrs:
                ml = mem.read_byte(addrs['location'])
                tbl = 11 if ml >= 50 else 1
            names = _FISH_NAMES.get(tbl, _FISH_NAMES[0])
            fname = names[name_idx] if name_idx < len(names) else "fish"
            count = mem.read_byte(addrs['counter'])
            return f"Your quest is to catch^{count} {fname} at the {loc}.^Good luck!"
        else:
            generate_fishing_quest_two(mem, npc_id)
            lo = mem.read_byte(addrs['min_size'])
            hi = mem.read_byte(addrs['max_size'])
            return f"Your quest is to catch any fish^of a size from {lo} cm to {hi} cm^at the {loc}.^Good luck!"

    elif progress == 1:
        qtype = mem.read_byte(addrs['type'])
        if qtype == 0:
            name_idx = mem.read_byte(addrs['name'])
            area = mem.read_byte(LOCATION_ADDR)
            tbl = area if area in _FISH_NAMES else 0
            if area == 1 and 'location' in addrs:
                ml = mem.read_byte(addrs['location'])
                tbl = 11 if ml >= 50 else 1
            names = _FISH_NAMES.get(tbl, _FISH_NAMES[0])
            fname = names[name_idx] if name_idx < len(names) else "fish"
            left = mem.read_byte(addrs['counter'])
            return f"You're still on the quest to catch^{fname} at the {loc},^just {left} left!"
        else:
            lo = mem.read_byte(addrs['min_size'])
            hi = mem.read_byte(addrs['max_size'])
            return f"You're still on the quest to catch any^fish of a size from {lo} cm to {hi} cm^at the {loc}.^Good luck!"

    elif progress == 2:
        return "Nicely done!^Here's your reward: Fishing Points!"

    return None


def check_fish_collection(mem):
    """Check master fish quest progress. Returns (complete, missing_names)."""
    a = 0x21CE4439
    count = 0
    missing = []
    for i in range(len(ALL_FISH)):
        if i != 8:  # skip null
            if mem.read_byte(a) == 1:
                count += 1
            else:
                missing.append(ALL_FISH[i])
        a += 1
    complete = count == 17
    if complete:
        mem.write_byte(0x21CE444F, 1)
    return complete, missing


def give_master_fish_reward(mem):
    """Give Fishing Rod (191) as master fish quest reward."""
    a = FIRST_INV_SLOT
    for _ in range(102):
        if mem.read_short(a) > 60000:
            mem.write_short(a, 191)
            break
        a += 2
    mem.write_byte(0x21CE4450, 1)
