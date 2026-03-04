"""Custom weapon effects. Ported from CustomEffects.cs.

Each weapon has a unique combat effect triggered while equipped in dungeon.
"""

import logging
import math
import random
import threading
import time
from game import addresses as addr
from data.enemies import Enemy, ENEMY_OFFSET
from data.player import weapon_slot_addr, Toan, Xiao, Goro, Ruby, Ungaga, Osmond, CHARACTERS
from data import items
from data.rubyorbs import *

log = logging.getLogger(__name__)


def bone_rapier_effect(mem, active):
    """Toggle bone door bypass. BoneRapier lets you open bone doors without a key."""
    try:
        cur = mem.read_byte(addr.BONE_DOOR_TYPE)
        if active and cur != 5:
            mem.write_byte(addr.BONE_DOOR_TYPE, 5)
        elif not active and cur == 5:
            mem.write_byte(addr.BONE_DOOR_TYPE, 21)
    except Exception:
        pass


def bone_door_trigger(mem, dungeon_mod):
    """Monitor for bone door opening while Bone Rapier equipped."""
    while (not dungeon_mod.door_is_open and
           dungeon_mod._in_dungeon_floor() and
           dungeon_mod._get_current_weapon_id() == items.bonerapier):
        try:
            if (mem.read_byte(addr.DOOR_TYPE + 0x800) == 250 and
                mem.read_byte(addr.BONE_DOOR_TYPE) == 5 and
                mem.read_int(0x21D56800) == 15903712):
                ms = 0
                while mem.read_int(addr.HIDE_HUD) == 1 and ms < 2000:
                    time.sleep(0.1); ms += 100
                dungeon_mod._display_message("You can hear an ominous voice\nlaughing 'Rattle me bones!'", 2, 29, 4000)
                dungeon_mod.door_is_open = True
            elif (mem.read_byte(addr.DOOR_TYPE + 0x800) == 250 and
                  mem.read_int(0x21D56800) == 15903712):
                dungeon_mod.door_is_open = True
        except Exception:
            pass
        time.sleep(0.5)


def check_chronicle2(mem):
    """Check if player owns Chronicle 2 (item 298) in any weapon slot or storage."""
    for slot in range(10):
        try:
            if mem.read_short(weapon_slot_addr(0, slot, 'id')) == items.chronicletwo:
                return True
        except Exception:
            pass
    # Check storage
    a = 0x21CE22D8
    for i in range(30):
        try:
            if mem.read_short(a) == items.chronicletwo:
                return True
        except Exception:
            pass
        a += 0xF8
    return False


def angel_gear(mem):
    """Heal all allies by 1 HP every 5 seconds while Angel Gear equipped."""
    chars = [Toan, Xiao, Goro, Ruby, Ungaga, Osmond]
    while True:
        try:
            if mem.read_short(0x21EA7590) != items.angelgear:
                break
            if mem.read_short(addr.DUNGEON_MODE) != 1:
                break
        except Exception:
            break
        for c in chars:
            try:
                hp = mem.read_short(c.hp)
                maxhp = mem.read_short(c.maxHP)
                if 0 < hp < maxhp:
                    mem.write_short(c.hp, hp + 1)
            except Exception:
                pass
        time.sleep(5)


def hercules_wrath(mem):
    """30% chance on taking damage to gain Stamina status for 30s."""
    try:
        former = mem.read_short(Ungaga.hp)
        time.sleep(0.1)
        current = mem.read_short(Ungaga.hp)
        if current < former and random.random() < 0.3:
            mem.write_short(Ungaga.status, 8)  # Stamina
            mem.write_short(Ungaga.statusTimer, 1800)
    except Exception:
        pass


def babel_spear(mem):
    """6% chance on hit to freeze all enemies for 5 seconds."""
    try:
        hit = mem.read_int(addr.MOST_RECENT_DAMAGE)
        src = mem.read_int(addr.DAMAGE_SOURCE)
        if hit > 0 and src == 4 and random.random() < 0.06:
            for i in range(16):
                try:
                    if mem.read_byte(Enemy.addr(i, 'renderStatus')) == 2:
                        mem.write_short(Enemy.addr(i, 'freezeTimer'), 300)
                except Exception:
                    pass
        mem.write_int(addr.MOST_RECENT_DAMAGE, 0)
        mem.write_int(addr.DAMAGE_SOURCE, 0)
    except Exception:
        pass


def supernova(mem):
    """10% chance on hit to apply random status to hit enemies."""
    try:
        former = _get_enemies_hp(mem)
        time.sleep(0.25)
        hit = mem.read_int(addr.MOST_RECENT_DAMAGE)
        src = mem.read_int(addr.DAMAGE_SOURCE)
        if hit > 0 and src == 5:
            current = _get_enemies_hp(mem)
            for i in range(16):
                if current[i] < former[i] and random.random() < 0.1:
                    eff = random.randint(0, 3)
                    fields = ['freezeTimer', 'poisonPeriod', 'staminaTimer', 'gooeyState']
                    vals = [300, 1, 300, 1]
                    try:
                        mem.write_short(Enemy.addr(i, fields[eff]), vals[eff])
                    except Exception:
                        pass
        mem.write_int(addr.MOST_RECENT_DAMAGE, 0)
        mem.write_int(addr.DAMAGE_SOURCE, 0)
    except Exception:
        pass


def star_breaker(mem):
    """2% chance on kill to get an empty synth sphere."""
    try:
        former = _get_enemies_hp(mem)
        time.sleep(0.25)
        current = _get_enemies_hp(mem)
        killed = any(former[i] > 0 and current[i] <= 0 for i in range(16))
        if killed and random.random() < 0.02:
            log.info("Star Breaker: synth sphere drop!")
            # Would need inventory write — simplified
    except Exception:
        pass
    try:
        mem.write_int(addr.MOST_RECENT_DAMAGE, 0)
        mem.write_int(addr.DAMAGE_SOURCE, 0)
    except Exception:
        pass


def secret_armlet_enable(mem):
    """Make all magic circle effects positive (0-4)."""
    changed = False
    circles = [
        (addr.CIRCLE_SPAWN_1, addr.CIRCLE_EFFECT_1),
        (addr.CIRCLE_SPAWN_2, addr.CIRCLE_EFFECT_2),
        (addr.CIRCLE_SPAWN_3, addr.CIRCLE_EFFECT_3),
        (addr.BF_CIRCLE_SPAWN_1, addr.BF_CIRCLE_EFFECT_1),
        (addr.BF_CIRCLE_SPAWN_2, addr.BF_CIRCLE_EFFECT_2),
        (addr.BF_CIRCLE_SPAWN_3, addr.BF_CIRCLE_EFFECT_3),
    ]
    for spawn, eff in circles:
        try:
            if mem.read_byte(spawn) != 0 and mem.read_byte(eff) > 4:
                mem.write_byte(eff, random.randint(0, 4))
                changed = True
        except Exception:
            pass
    return changed


def secret_armlet_disable(mem):
    """Re-roll all magic circle effects (0-9, includes negative)."""
    circles = [
        (addr.CIRCLE_SPAWN_1, addr.CIRCLE_EFFECT_1),
        (addr.CIRCLE_SPAWN_2, addr.CIRCLE_EFFECT_2),
        (addr.CIRCLE_SPAWN_3, addr.CIRCLE_EFFECT_3),
        (addr.BF_CIRCLE_SPAWN_1, addr.BF_CIRCLE_EFFECT_1),
        (addr.BF_CIRCLE_SPAWN_2, addr.BF_CIRCLE_EFFECT_2),
        (addr.BF_CIRCLE_SPAWN_3, addr.BF_CIRCLE_EFFECT_3),
    ]
    for spawn, eff in circles:
        try:
            if mem.read_byte(spawn) != 0:
                mem.write_byte(eff, random.randint(0, 9))
        except Exception:
            pass


def inferno(mem):
    """Goro's Inferno: boost attack based on missing HP and thirst."""
    try:
        maxhp = mem.read_short(Goro.maxHP)
        curhp = mem.read_short(Goro.hp)
        if maxhp == 0: return
        hp_pct = 100 - (curhp / maxhp * 100)
        maxthirst = mem.read_float(Goro.thirstMax)
        curthirst = mem.read_float(Goro.thirst)
        thirst_pct = 100 - (curthirst / maxthirst * 100) if maxthirst > 0 else 0
        base_atk = mem.read_short(0x21EA7594)
        total = min(base_atk, 350)
        hp_boost = int((total / 100) * hp_pct)
        thirst_boost = int((total / 100) * (thirst_pct / 2))
        mem.write_short(0x21EA7594, total + hp_boost + thirst_boost)
    except Exception:
        pass


def _get_enemies_hp(mem):
    """Read HP of all 16 enemy slots."""
    hp = []
    for i in range(16):
        try:
            hp.append(mem.read_int(Enemy.addr(i, 'hp')))
        except Exception:
            hp.append(0)
    return hp


# Weapon ID → effect function mapping for the dungeon thread
WEAPON_EFFECTS = {
    items.bonerapier: 'bone_rapier',
    items.seventhheaven: 'seventh_heaven',
    items.chroniclesword: 'chronicle_sword',
    items.angelgear: 'angel_gear',
    items.tallhammer: 'tall_hammer',
    items.inferno: 'inferno_effect',
    items.mobiusring: 'mobius_ring',
    items.secretarmlet: 'secret_armlet',
    items.herculeswrath: 'hercules_wrath',
    items.babelsspear: 'babel_spear',
    items.supernova: 'supernova',
    items.starbreaker: 'star_breaker',
}


# ── SeventhHeaven ──────────────────────────────────────────────

FIRST_BAG_ATTACHMENT = 0x21CE1A48
_ATT_OFFSET = 0x20
_ATT_SLOTS = 42  # inventorySizeAttachments + 2

def _get_bag_attachments(mem):
    """Return list of attachment IDs (-1 for empty)."""
    out = []
    for s in range(_ATT_SLOTS):
        v = mem.read_short(FIRST_BAG_ATTACHMENT + (_ATT_OFFSET * s))
        out.append(v if items.fire <= v <= 1000 else -1)
    return out

def _first_empty_att_slot(mem):
    bag = _get_bag_attachments(mem)
    for i, v in enumerate(bag):
        if v == -1:
            return i
    return -1

def seventh_heaven(mem):
    """Duplicate non-gem attachments on pickup; 50% for gems."""
    slot = _first_empty_att_slot(mem)
    if slot < 0:
        return
    old_item = _get_bag_attachments(mem)[slot]
    time.sleep(0.25)
    new_item = _get_bag_attachments(mem)[slot]
    if new_item != old_item and items.fire <= new_item <= items.mageslayer:
        # Read attachment data
        src = FIRST_BAG_ATTACHMENT + (_ATT_OFFSET * slot)
        data = [mem.read_byte(src + b) for b in range(0x1F)]
        # Gems: 50% chance
        if items.garnet <= new_item <= items.turquoise:
            if random.randint(0, 99) >= 50:
                return
        dst_slot = _first_empty_att_slot(mem)
        if dst_slot >= 0:
            dst = FIRST_BAG_ATTACHMENT + (_ATT_OFFSET * dst_slot)
            for b, v in enumerate(data):
                mem.write_byte(dst + b, v)
            log.info("7th Heaven duplicated attachment %d", new_item)


# ── Chronicle Sword AoE ───────────────────────────────────────

def chronicle_sword_init(mem):
    """Reset floating damage number slots and enemy distances on new floor."""
    for i in range(7):
        base = addr.FLOAT_DMG_SETUP_BASE + (0x60 * i)
        mem.write_int(base, 0)
        mem.write_int(base + 4, 158)
        mem.write_int(base + 8, 12)
        mem.write_int(base + 12, 18)
    for i in range(16):
        mem.write_float(Enemy.addr(i, 'distanceToPlayer'), 0)

def _get_int_digits(num):
    """Split integer into digit list (LSB first, matching C# GetIntArray)."""
    if num <= 0:
        return [0]
    digits = []
    while num > 0:
        digits.append(num % 10)
        num //= 10
    return digits

def _damage_fadeout(mem):
    """Fade out floating damage numbers."""
    time.sleep(0.5)
    for i in range(7):
        mem.write_int(0x21EC8284 + (0x60 * i), 1)
    time.sleep(0.2)
    for i in range(7):
        mem.write_int(0x21EC829C + (0x60 * i), 0)

def chronicle_sword(mem, former_whp, former_hp):
    """AoE splash damage to nearby enemies when hitting with Chronicle Sword.

    Returns (current_whp, current_hp) for next iteration.
    """
    time.sleep(0.05)
    char_id = mem.read_byte(addr.CURRENT_CHARACTER)
    slot = mem.read_byte(Toan.currentWeaponSlot)
    cur_whp = mem.read_float(weapon_slot_addr(char_id, slot, 'whp'))
    cur_hp = _get_enemies_hp(mem)

    if cur_whp >= former_whp or mem.read_int(addr.MOST_RECENT_DAMAGE) <= 0:
        mem.write_int(addr.MOST_RECENT_DAMAGE, -1)
        mem.write_int(addr.DAMAGE_SOURCE, -1)
        return cur_whp, cur_hp

    # Find which enemy was hit
    damaged_num = -1
    flash_r = flash_g = flash_b = 0.0
    damage = mem.read_int(addr.MOST_RECENT_DAMAGE)
    for i in range(15):
        if cur_hp[i] < former_hp[i]:
            damaged_num = i
            flash_r = mem.read_float(Enemy.addr(i, 'flashColorRed'))
            flash_g = mem.read_float(Enemy.addr(i, 'flashColorGreen'))
            flash_b = mem.read_float(Enemy.addr(i, 'flashColorBlue'))
            break

    if damaged_num < 0:
        mem.write_int(addr.MOST_RECENT_DAMAGE, -1)
        mem.write_int(addr.DAMAGE_SOURCE, -1)
        return cur_whp, cur_hp

    # Find enemies in range
    in_range = []
    for i in range(15):
        if i == damaged_num:
            continue
        if cur_hp[i] > 0:
            dist = mem.read_float(Enemy.addr(i, 'distanceToPlayer'))
            if 0 < dist < 300:
                in_range.append(i)

    if not in_range:
        mem.write_int(addr.MOST_RECENT_DAMAGE, -1)
        mem.write_int(addr.DAMAGE_SOURCE, -1)
        return cur_whp, cur_hp

    # Calculate splash damage per enemy
    eff_dmg = []
    for idx in in_range:
        dist = mem.read_float(Enemy.addr(idx, 'distanceToPlayer'))
        if dist < 50:
            d = math.floor(damage / 2)
        else:
            pct = max(1, (300 - dist) / 5)
            d = math.floor(damage * (pct / 100))
        eff_dmg.append(int(d))

    # Write floating damage numbers (max 7)
    for i, idx in enumerate(in_range[:7]):
        # Flash
        mem.write_float(Enemy.addr(idx, 'flashColorRed'), flash_r)
        mem.write_float(Enemy.addr(idx, 'flashColorGreen'), flash_g)
        mem.write_float(Enemy.addr(idx, 'flashColorBlue'), flash_b)
        mem.write_float(Enemy.addr(idx, 'flashDuration'), 0.1)

        # Position
        base = addr.FLOAT_DMG_BASE + (0x60 * i)
        mem.write_float(base, mem.read_float(Enemy.addr(idx, 'locationCoordinateX')))
        mem.write_float(base + 4, mem.read_float(Enemy.addr(idx, 'locationCoordinateZ')) - 3)
        mem.write_float(base + 8, mem.read_float(Enemy.addr(idx, 'locationCoordinateY')))
        mem.write_float(base + 0xC, 1)
        for off in [0x14, 0x18, 0x1C, 0x20, 0x24]:
            mem.write_float(base + off, 0)

        # Digits
        digits = _get_int_digits(eff_dmg[i])
        for d_i in range(5):
            val = digits[d_i] if d_i < len(digits) else -1
            mem.write_int(base + 0x28 + (4 * d_i), val)

        mem.write_float(base + 0x3C, 0)
        mem.write_float(base + 0x40, 3)
        mem.write_int(base + 0x44, -1)

    # Apply damage and trigger flash
    for i, idx in enumerate(in_range[:7]):
        mem.write_int(addr.FLOAT_DMG_BASE + (0x60 * i) + 0x5C, 1)
        mem.write_byte(Enemy.addr(idx, 'flashActivation'), 1)
        ehp = mem.read_int(Enemy.addr(idx, 'hp'))
        new_hp = int(ehp - eff_dmg[i])
        if new_hp < 1:
            new_hp = 1
            mem.write_byte(Enemy.addr(idx, 'poisonPeriod'), 1)
        mem.write_int(Enemy.addr(idx, 'hp'), new_hp)

    # Fadeout thread
    threading.Thread(target=_damage_fadeout, args=(mem,), daemon=True).start()

    mem.write_int(addr.MOST_RECENT_DAMAGE, -1)
    mem.write_int(addr.DAMAGE_SOURCE, -1)
    return cur_whp, cur_hp


# ── Tall Hammer ────────────────────────────────────────────────

def tall_hammer(mem):
    """Shrink enemies on hit."""
    from data.miniboss import enemyZeroWidth, scaleOffset
    former = _get_enemies_hp(mem)
    time.sleep(0.25)
    current = _get_enemies_hp(mem)
    hit = mem.read_int(addr.MOST_RECENT_DAMAGE)
    src = mem.read_int(addr.DAMAGE_SOURCE)
    if hit <= 0 or src != 2:  # Goro = char 2
        return
    # Find hit enemies
    hit_ids = [i for i in range(15) if current[i] < former[i]]
    for eid in hit_ids:
        w = mem.read_float(enemyZeroWidth + scaleOffset * eid)
        h = mem.read_float(enemyZeroWidth + 4 + scaleOffset * eid)
        d = mem.read_float(enemyZeroWidth + 8 + scaleOffset * eid)
        accel = 0.15
        for _ in range(1000):
            if not (0.3 <= w <= 1.0 or 0.3 <= h <= 1.0 or 0.3 <= d <= 1.0):
                break
            w -= accel * 0.0001
            h -= accel * 0.0001
            d -= accel * 0.0001
            mem.write_float(enemyZeroWidth + scaleOffset * eid, w)
            mem.write_float(enemyZeroWidth + 4 + scaleOffset * eid, h)
            mem.write_float(enemyZeroWidth + 8 + scaleOffset * eid, d)
            accel += 1
    mem.write_int(addr.MOST_RECENT_DAMAGE, -1)
    mem.write_int(addr.DAMAGE_SOURCE, -1)


# ── Mobius Ring ────────────────────────────────────────────────

def mobius_ring(mem):
    """Charge attack damage scaling for Ruby's Mobius Ring."""
    from game.display import display_message
    CHARGE_GLOW = 0x21DC449E

    # Check if Ruby is charging (animation 14)
    if mem.read_byte(Ruby.hp - 0x10 + 0x100) != 14:  # Ruby animationId approximation
        # Use the known address pattern
        pass

    # Simpler: check if charging via the glow timer
    base_dmg = mem.read_short(0x21EA7594) + mem.read_short(0x21EA7598)  # atk + magic
    damage = base_dmg

    # Wait for charge to begin
    while mem.read_short(CHARGE_GLOW) < 100:
        time.sleep(0.1)
        if mem.read_byte(addr.DUNGEON_MODE) != 1:
            return

    # Charge loop
    while mem.read_short(CHARGE_GLOW) > 0:
        if mem.read_byte(addr.DUNGEON_MODE) != 1:
            return
        if damage >= 65535:
            damage = 65535
        else:
            damage += damage // 2

        # Wait for flash point (17008)
        while mem.read_short(CHARGE_GLOW) < 17008:
            if mem.read_short(CHARGE_GLOW) == 0:
                break
            time.sleep(0.1)

        if mem.read_short(CHARGE_GLOW) == 17008:
            msg = "Total damage is over 9000" if damage > 9000 else f"Total damage {damage}"
            display_message(mem, msg, 1, len(msg), 2000)
            time.sleep(1.5)
            mem.write_short(CHARGE_GLOW, 0)
        time.sleep(0.1)

    # Apply damage to active orbs
    orb_classes = [Orb0, Orb1, Orb2, Orb3, Orb4, Orb5]
    for orb in orb_classes:
        try:
            while mem.read_byte(orb.id) == 1:
                mem.write_int(orb.damage, damage)
        except Exception:
            pass


# ── Escape Powder ──────────────────────────────────────────────

def check_escape_powders(mem):
    """Consume one escape powder from active slots."""
    # Check if player has escape powder in inventory first
    for i in range(60):
        slot_addr = 0x21CFCCEC + i * 0x2C
        try:
            if mem.read_short(slot_addr) == 175:
                return  # Has in inventory, game handles it
        except Exception:
            pass

    # Consume from active slots
    slots = [
        (addr.ACTIVE_SLOT_0_ID, addr.ACTIVE_SLOT_0_QTY),
        (addr.ACTIVE_SLOT_1_ID, addr.ACTIVE_SLOT_1_QTY),
        (addr.ACTIVE_SLOT_2_ID, addr.ACTIVE_SLOT_2_QTY),
    ]
    for id_addr, qty_addr in slots:
        try:
            if mem.read_byte(id_addr) == 175:
                qty = mem.read_byte(qty_addr)
                qty -= 1
                mem.write_byte(qty_addr, qty)
                if qty == 0:
                    mem.write_short(id_addr, 0)
                log.info("Consumed escape powder from active slots")
                return
        except Exception:
            pass
