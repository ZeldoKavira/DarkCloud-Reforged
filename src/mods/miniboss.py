"""Mini-boss spawn logic. Ported from MiniBoss.cs."""

import logging
import random
import time

from data import items, miniboss as mb
from data.enemies import Enemy, ENEMY_OFFSET, enemiesFlying
from data.customchests import (
    dbcFirstHalfWeapons, dbcSecondHalfWeapons,
    wiseowlFirstHalfWeapons, wiseowlSecondHalfWeapons,
    shipwreckFirstHalfWeapons, shipwreckSecondHalfWeapons,
    sunmoonFirstHalfWeapons, sunmoonSecondHalfWeapons,
    moonseaFirstHalfWeapons, moonseaSecondHalfWeapons,
    galleryWeapons, demonshaftWeapons,
)

log = logging.getLogger(__name__)

# Gate keys per dungeon (for key-holder detection)
GATE_KEYS = {
    0: [items.dranscrest],
    1: [items.shinystone, items.redberry, items.pointychestnut],
    2: [items.hook],
    3: [items.kingsslate],
    4: [items.gunpowder],
    5: [items.clockhands],
    6: [items.blackknightcrest],
}

# Backfloor keys per dungeon
BF_KEYS = {
    0: items.tramoil, 1: items.sundew, 2: items.flappingfish,
    3: items.secretpathkey, 4: items.braverylaunch,
    5: items.flappingduster, 6: items.crystaleyeball,
}

# Weapon tables per dungeon/floor
_HALF_THRESH = {0: 8, 1: 9, 2: 9, 3: 9, 4: 8}

def _get_weapon_table(dungeon, floor):
    tables = {
        (0, 0): dbcFirstHalfWeapons, (0, 1): dbcSecondHalfWeapons,
        (1, 0): wiseowlFirstHalfWeapons, (1, 1): wiseowlSecondHalfWeapons,
        (2, 0): shipwreckFirstHalfWeapons, (2, 1): shipwreckSecondHalfWeapons,
        (3, 0): sunmoonFirstHalfWeapons, (3, 1): sunmoonSecondHalfWeapons,
        (4, 0): moonseaFirstHalfWeapons, (4, 1): moonseaSecondHalfWeapons,
    }
    if dungeon == 5:
        return galleryWeapons
    if dungeon == 6:
        return demonshaftWeapons
    half = 0 if floor <= _HALF_THRESH.get(dungeon, 9) else 1
    return tables.get((dungeon, half), dbcFirstHalfWeapons)


def _get_floor_enemy_ids(mem):
    """Read name tags of all 15 floor enemies."""
    return [mem.read_short(Enemy.addr(i, 'nameTag')) for i in range(15)]


def _enemy_has_key(mem, enemy_num, dungeon):
    """Check if enemy holds a gate key."""
    drop = mem.read_byte(Enemy.addr(enemy_num, 'forceItemDrop'))
    return drop in GATE_KEYS.get(dungeon, [])


def miniboss_spawn(mem, skip_first_roll=False, dungeon=255, floor=255, _depth=0):
    """Pick and transform a floor enemy into a Champion (mini-boss).

    Returns (spawned: bool, enemy_num: int).
    """
    if _depth > 10:
        log.warning("Mini-boss retry limit reached")
        return False, -1

    # 30% chance (or forced)
    if not skip_first_roll and random.randint(0, 99) > 30:
        log.info("Failed to roll for Mini Boss!")
        return False, -1

    if not skip_first_roll:
        time.sleep(0.2)

    ids = _get_floor_enemy_ids(mem)
    valid = [i for i in range(len(ids)) if ids[i] > 0]
    if not valid:
        return False, -1

    enemy_num = random.choice(valid)
    eid = ids[enemy_num]

    # Skip flying enemies
    if eid in enemiesFlying:
        log.info("Miniboss landed on flying enemy, retrying")
        return miniboss_spawn(mem, True, dungeon, floor, _depth + 1)

    # If enemy holds the key, move key to another enemy
    if _enemy_has_key(mem, enemy_num, dungeon):
        log.info("Key landed on mini boss — relocating")
        key_id = mem.read_short(Enemy.addr(enemy_num, 'forceItemDrop'))
        candidates = [i for i in valid if i != enemy_num
                      and not _enemy_has_key(mem, i, dungeon)
                      and ids[i] not in enemiesFlying]
        if candidates:
            new_num = random.choice(candidates)
            mem.write_short(Enemy.addr(enemy_num, 'forceItemDrop'), 0)
            mem.write_short(Enemy.addr(new_num, 'forceItemDrop'), key_id)

    # Read base stats
    base_hp = mem.read_int(Enemy.addr(enemy_num, 'hp'))
    base_abs = mem.read_int(Enemy.addr(enemy_num, 'abs'))
    base_gold = mem.read_int(Enemy.addr(enemy_num, 'minGoldDrop'))

    # Scale size
    for field, off in [('width', 0), ('height', 4), ('depth', 8)]:
        a = mb.enemyZeroWidth + off + (mb.scaleOffset * enemy_num)
        mem.write_float(a, mb.scaleSize)

    # Scale stats
    mem.write_int(Enemy.addr(enemy_num, 'hp'), base_hp * mb.enemyHPMult)
    mem.write_int(Enemy.addr(enemy_num, 'maxHp'), base_hp * mb.enemyHPMult)
    mem.write_int(Enemy.addr(enemy_num, 'abs'), base_abs * mb.enemyABSMult)
    mem.write_int(Enemy.addr(enemy_num, 'itemResistance'), mb.enemyItemResistMulti)
    mem.write_int(Enemy.addr(enemy_num, 'minGoldDrop'), base_gold * mb.enemyGoldMult)
    mem.write_int(Enemy.addr(enemy_num, 'dropChance'), mb.enemyDropChance)
    mem.write_byte(Enemy.addr(enemy_num, 'staminaTimer') + 2, mb.staminaTimer)

    # Roll loot
    drop_addr = Enemy.addr(enemy_num, 'forceItemDrop')
    wpn_tbl = _get_weapon_table(dungeon, floor)

    if random.randint(0, 99) < 35:
        # Backfloor key
        mem.write_short(drop_addr, BF_KEYS.get(dungeon, 255))
        log.info("Miniboss rolled with backfloor key!")
    elif random.randint(0, 99) < 15:
        # Weapon
        mem.write_int(drop_addr, random.choice(wpn_tbl))
        log.info("Miniboss rolled with weapon!")
    elif random.randint(0, 99) < 50:
        # Attachment
        tbl = mb.attachmentsTableLucky if random.randint(0, 99) < 30 else mb.attachmentsTableUnlucky
        mem.write_short(drop_addr, random.choice(tbl))
        log.info("Miniboss rolled with attachment!")
    else:
        # Item
        tbl = mb.itemTableLucky if random.randint(0, 99) < 30 else mb.itemTableUnlucky
        mem.write_short(drop_addr, random.choice(tbl))
        log.info("Miniboss rolled with item!")

    return True, enemy_num
