"""Chest & Clown randomizer. Ported from CustomChests.cs."""

import logging
import random
import struct
import time

from game import addresses as addr
from data import customchests as cc

log = logging.getLogger(__name__)

# Floor threshold for first/second half per dungeon
_HALF_THRESH = {0: 8, 1: 9, 2: 9, 3: 9, 4: 8, 5: 11, 6: 49}

# Dungeon-specific common small table override (index 23)
_SMALL_TABLE_OVERRIDE = {1: 225, 2: 226, 3: 228, 4: 229, 5: 230}

# Loot table lookup: (dungeon, half) → (item_table_name, weapon_table_name,
#   clown_big_name, clown_small_name)
_TABLE_NAMES = {
    (0, 0): ('dbcFirstHalfItems', 'dbcFirstHalfWeapons',
             'dbcFirstHalfClownBigWeapons', None),
    (0, 1): ('dbcSecondfHalfItems', 'dbcSecondHalfWeapons',
             'dbcSecondHalfClownBigWeapons', 'dbcSecondHalfClownSmallWeapons'),
    (1, 0): ('wiseowlFirstHalfItems', 'wiseowlFirstHalfWeapons',
             'wiseowlFirstHalfClownBigWeapons', 'wiseowlFirstHalfClownSmallWeapons'),
    (1, 1): ('wiseowlSecondHalfItems', 'wiseowlSecondHalfWeapons',
             'wiseowlSecondHalfClownBigWeapons', 'wiseowlSecondHalfClownSmallWeapons'),
    (2, 0): ('shipwreckFirstHalfItems', 'shipwreckFirstHalfWeapons',
             'shipwreckFirstHalfClownBigWeapons', 'shipwreckFirstHalfClownSmallWeapons'),
    (2, 1): ('shipwreckSecondHalfItems', 'shipwreckSecondHalfWeapons',
             'shipwreckSecondHalfClownBigWeapons', 'shipwreckSecondHalfClownSmallWeapons'),
    (3, 0): ('sunmoonFirstHalfItems', 'sunmoonFirstHalfWeapons',
             'sunmoonFirstHalfClownBigWeapons', 'sunmoonFirstHalfClownSmallWeapons'),
    (3, 1): ('sunmoonSecondHalfItems', 'sunmoonSecondHalfWeapons',
             'sunmoonSecondHalfClownBigWeapons', 'sunmoonSecondHalfClownSmallWeapons'),
    (4, 0): ('moonseaFirstHalfItems', 'moonseaFirstHalfWeapons',
             'moonseaFirstHalfClownBigWeapons', 'moonseaFirstHalfClownSmallWeapons'),
    (4, 1): ('moonseaSecondHalfItems', 'moonseaSecondHalfWeapons',
             'moonseaSecondHalfClownBigWeapons', 'moonseaSecondHalfClownSmallWeapons'),
    (5, 0): ('galleryItems', 'galleryWeapons',
             'galleryClownBigWeapons', 'galleryClownSmallWeapons'),
    (5, 1): ('galleryItems', 'galleryWeapons',
             'galleryClownBigWeapons', 'galleryClownSmallWeapons'),
    (6, 0): ('demonshaftItems', 'demonshaftWeapons',
             'demonshaftClownBigWeapons', 'demonshaftClownSmallWeapons'),
    (6, 1): ('demonshaftItems', 'demonshaftWeapons',
             'demonshaftClownBigWeapons', 'demonshaftClownSmallWeapons'),
}


def _get_tables(dungeon, floor):
    """Resolve loot tables and box addresses for dungeon/floor."""
    half = 0 if floor <= _HALF_THRESH.get(dungeon, 9) else 1
    names = _TABLE_NAMES.get((dungeon, half))
    if not names:
        return None
    item_tbl = getattr(cc, names[0])
    wpn_tbl = getattr(cc, names[1])
    clown_big = getattr(cc, names[2])
    clown_small = getattr(cc, names[3]) if names[3] else list(cc.clownCommonSmallTable)
    box_addrs = cc.BOX_ADDRS.get((dungeon, half))

    # Demon shaft special: index 5 changes based on floor
    if dungeon == 6:
        item_tbl = list(item_tbl)
        item_tbl[5] = 231 if floor <= 49 else 181

    # Override clownCommonSmallTable[23] for dungeons 1-5
    if dungeon in _SMALL_TABLE_OVERRIDE:
        cc.clownCommonSmallTable[23] = _SMALL_TABLE_OVERRIDE[dungeon]

    return item_tbl, wpn_tbl, clown_big, clown_small, box_addrs


def _check_item_quest_reward(mem, item_id, inventory_only=True, _active_only=False):
    """Check if player has item_id in inventory (and optionally storage)."""
    from mods.sidequests import check_item_quest_reward
    return check_item_quest_reward(mem, item_id, check_inv=True, check_storage=not inventory_only)


def _roll_item_quest(dungeon):
    """Roll for quest item spawn. Returns (spawn, item_id) or (False, 0)."""
    if dungeon not in cc.QUEST_ITEM_IDS:
        return False, 0
    chance = cc.QUEST_ITEM_CHANCES.get(dungeon, 66)
    if random.randint(0, 99) > chance:
        return True, cc.QUEST_ITEM_IDS[dungeon]
    return False, 0


def chest_randomizer(mem, dungeon, floor, chronicle2):
    """Randomize chest contents for current floor. Ported from CustomChests.ChestRandomizer()."""
    log.info("Custom chests activated")
    time.sleep(0.1)

    tables = _get_tables(dungeon, floor)
    if not tables:
        return
    item_tbl, wpn_tbl, clown_big, clown_small, box_addrs = tables

    # Quest item check
    quest_spawn = False
    quest_item_id = 0
    if dungeon in cc.QUEST_CHECK_ADDRS:
        if mem.read_byte(cc.QUEST_CHECK_ADDRS[dungeon]) == 1:
            quest_spawn, quest_item_id = _roll_item_quest(dungeon)
            if quest_spawn:
                already_has = _check_item_quest_reward(mem, quest_item_id)
                if already_has:
                    quest_spawn = False
                else:
                    log.info("Rolled sidequest secret item for this floor")

    # Big chest chance
    big_mod = 15 * dungeon
    big_chance = 880 + big_mod
    if chronicle2:
        big_chance -= (1000 - big_chance)
    log.info("Big chest chance: %d", big_chance)

    # Check map/MC ownership
    has_map = _check_item_quest_reward(mem, 233)
    has_mc = _check_item_quest_reward(mem, 234)

    # Save setting override: always grant map/MC
    if mem.read_byte(addr.OPTION_SAVE_START_MAP) == 1:
        has_map = True
    if mem.read_byte(addr.OPTION_SAVE_START_MC) == 1:
        has_mc = True

    # Determine offset from first chest
    first_item = mem.read_byte(addr.FIRST_CHEST)
    if first_item == 233:
        offset = 0x00 if (has_map or has_mc) else 0x80
    else:
        offset = 0x40 if (has_map or has_mc) else 0xC0

    cur = addr.FIRST_CHEST + offset

    # Main floor chests (8 slots)
    for i in range(8):
        spawn = True
        if i < 2 and (has_map or has_mc):
            if i == 0 and not has_map:
                spawn = False
            elif i == 1 and not has_mc:
                spawn = False

        if not spawn:
            cur += 0x40
            continue

        mimic = mem.read_short(cur)
        if mimic <= 40:  # Mimic — skip
            cur += 0x40
            continue

        roll = random.randint(0, 999)
        if roll < big_chance:  # Item
            val = random.choice(item_tbl)
            # Reroll 178 (Abs) 80% of the time unless chronicle2
            if val == 178 and not chronicle2 and random.randint(0, 99) < 80:
                val = random.choice(item_tbl)
            mem.write_int(cur, val)
            cur += 8
            mem.write_byte(cur, 1)
            cur += 0x38
            log.info("Spawned item: %d", val)
        else:  # Weapon
            val = random.choice(wpn_tbl)
            mem.write_int(cur, val)
            cur += 8
            mem.write_byte(cur, 0)
            cur += 8
            trap = random.randint(0, 5)
            mem.write_int(cur, trap)
            cur += 0x30
            log.info("Spawned weapon: %d", val)

    # Backfloor chests (7 slots)
    cur = addr.BF_FIRST_CHEST
    quest_spawned = False

    for _ in range(7):
        mimic = mem.read_short(cur)
        if mimic <= 40:
            cur += 0x40
            continue

        roll = random.randint(0, 999)
        if roll < big_chance:  # Item
            val = random.choice(cc.BackfloorItems)
            if val == 178 and random.randint(0, 99) < 80:
                val = random.choice(cc.BackfloorItems)
            if quest_spawn and not quest_spawned:
                val = quest_item_id
                quest_spawned = True
            mem.write_int(cur, val)
            cur += 8
            mem.write_byte(cur, 1)
            cur += 0x38
            log.info("Spawned backfloor item: %d", val)
        else:  # Weapon
            val = random.choice(wpn_tbl)
            mem.write_int(cur, val)
            cur += 8
            mem.write_byte(cur, 0)
            cur += 8
            trap = random.randint(0, 5)
            mem.write_int(cur, trap)
            cur += 0x30
            log.info("Spawned backfloor weapon: %d", val)

    # Grant map/MC flags
    if has_map:
        mem.write_byte(addr.MAP, 1)
        log.info("Player has Map item")
    if has_mc:
        mem.write_byte(addr.MAGIC_CRYSTAL, 1)
        log.info("Player has Magical Crystal item")

    # Store state for clown randomizer
    chest_randomizer._tables = (item_tbl, wpn_tbl, clown_big, clown_small, box_addrs)

# Initialize stored state
chest_randomizer._tables = None


def clown_randomizer(mem, chronicle2):
    """Randomize clown loot. Ported from CustomChests.ClownRandomizer()."""
    log.info("Clown spawned!")
    tables = getattr(chest_randomizer, '_tables', None)
    if not tables:
        return
    _, _, clown_big, clown_small, box_addrs = tables
    if not box_addrs:
        return

    big_addr, small_addr, bf_big_addr, bf_small_addr = box_addrs
    lucky_chance = 0 if chronicle2 else 50
    is_backfloor = mem.read_byte(cc.BACKFLOOR_CHECK) != 0

    def _fill_box(base_addr, item_val):
        a = base_addr
        while mem.read_byte(a) != 255:
            mem.write_int(a, item_val)
            a += 4

    # Big box
    if random.randint(0, 99) >= lucky_chance:
        val = random.choice(clown_big)
    else:
        val = random.choice(cc.clownCommonBigTable)
    _fill_box(bf_big_addr if is_backfloor else big_addr, val)
    log.info("Big box item: %d", val)

    # Small box
    if random.randint(0, 99) >= lucky_chance:
        val = random.choice(clown_small)
    else:
        val = random.choice(cc.clownCommonSmallTable)
    _fill_box(bf_small_addr if is_backfloor else small_addr, val)
    log.info("Small box item: %d", val)
