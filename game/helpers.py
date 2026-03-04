"""Reusable helper functions. Ported from ReusableFunctions.cs."""

from game import addresses as addr
from data.enemies import Enemy, ENEMY_OFFSET
from data.player import weapon_slot_addr


def get_enemies_hp(mem):
    """Read HP of all 16 enemy slots."""
    return [mem.read_short(Enemy.addr(i, 'hp')) for i in range(16)]


def get_enemies_distance(mem):
    """Read distance-to-player of all 16 enemy slots."""
    return [mem.read_float(Enemy.addr(i, 'distanceToPlayer')) for i in range(16)]


def get_enemies_hit(former, current):
    """Return indices of enemies whose HP decreased."""
    return [i for i in range(len(former)) if current[i] < former[i]]


def get_enemies_killed(mem, former, current):
    """Return indices of enemies that were hit and now have 0 HP."""
    hit = get_enemies_hit(former, current)
    return [i for i in hit if mem.read_short(Enemy.addr(i, 'hp')) == 0]


def all_enemies_killed(mem):
    """Return True if all 15 floor enemies are dead."""
    for i in range(15):
        if (mem.read_int(Enemy.addr(i, 'hp')) != 0 or
                mem.read_byte(Enemy.addr(i, 'renderStatus')) != 255):
            return False
    return True


def get_recent_damage(mem):
    """Return last damage dealt by player."""
    return mem.read_int(addr.MOST_RECENT_DAMAGE)


def get_damage_source(mem):
    """Return character ID of damage source (-1 if throwable)."""
    return mem.read_int(addr.DAMAGE_SOURCE)


def clear_damage(mem):
    """Reset damage tracking."""
    mem.write_int(addr.MOST_RECENT_DAMAGE, -1)
    mem.write_int(addr.DAMAGE_SOURCE, -1)


def get_equipped_whp(mem, char_idx, slot_num):
    """Read current WHP of equipped weapon."""
    return mem.read_float(weapon_slot_addr(char_idx, slot_num, 'whp'))
