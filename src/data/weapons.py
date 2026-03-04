"""Auto-generated from Weapons.cs — do not edit manually.

Weapon database table addresses in game memory. These are the base stat table
addresses for the Dagger (Toan's first weapon). Other weapons are at:
    addr + weaponoffset * (weapon_item_id - character_base_weapon_id)
Other characters use character offsets added to the base address.
"""

from data.items import (
    dagger, woodenslingshot, mallet, goldring, fightingstick, machinegun,
    baselard, antiquesword, kitchenknife, tsukikage, machosword, heavenscloud,
    lambsswordnormal, braveark, bigbang, smallsword, sandbreaker, drainseeker,
    chopper, choora, claymore, maneater, bonerapier, sax, sevenbranchsword,
    crosshinder, chronicletwo,
    banditslingshot, boneslingshot, hardshooter, matador,
    turtleshell, bigbuckshammer, frozentuna, gaiahammer, trialhammer,
    banditsring, platinumring, pocklekul, thornarmlet, athenasarmlet,
    babelsspear, skunk,
)

# Default weapon IDs per character (first weapon in their list)
daggerid = dagger
woodenid = woodenslingshot
malletid = mallet
goldringid = goldring
stickid = fightingstick
machinegunid = machinegun

# --- Base database table addresses (Dagger / Toan slot 0) ---
synth1 = 0x2027A717
synth2 = 0x2027A718
synth3 = 0x2027A719
synth4 = 0x2027A71A
synth5 = 0x2027A71B
synth6 = 0x2027A71C
ownership = 0x2027A716
whp = 0x2027A70C
abs_ = 0x2027A73C       # 'abs' is a Python builtin
absadd = 0x2027A73E
attack = 0x2027A70E
maxattack = 0x2027A750
endurance = 0x2027A710
speed = 0x2027A712
magic = 0x2027A714
maxmagic = 0x2027A752
fire = 0x2027A71E
ice = 0x2027A720
thunder = 0x2027A722
wind = 0x2027A724
holy = 0x2027A726
dinoslayer = 0x2027A728
undead = 0x2027A72A
sea = 0x2027A72C
stone = 0x2027A72E
plant = 0x2027A730
beast = 0x2027A732
sky = 0x2027A734
metal = 0x2027A736
mimic = 0x2027A738
mage = 0x2027A73A
effect = 0x2027A744
effect2 = 0x2027A745
buildup = 0x2027A748

# Offset between each weapon in the database table
weaponoffset = 0x4C

# Character offsets from Toan's base
xiaooffset = 0xC78
gorooffset = 0x10EC
rubyoffset = 0x15F8
ungagaoffset = 0x1AB8
osmondoffset = 0x1F78

CHARACTER_DB_OFFSETS = [0, xiaooffset, gorooffset, rubyoffset, ungagaoffset, osmondoffset]
CHARACTER_BASE_IDS = [daggerid, woodenid, malletid, goldringid, stickid, machinegunid]

# Lamb sword thresholds
lambTransformThreshold = 0x202A1818
lambStatsThreshold = 0x202A188C


def db_addr(stat_addr, char_offset, weapon_id, base_id):
    """Compute weapon database address for a stat.

    Example: db_addr(endurance, 0, Items.baselard, daggerid)
    """
    return stat_addr + char_offset + (weaponoffset * (weapon_id - base_id))


# --- Weapon balance changes (from WeaponsBalanceChanges()) ---
# Each entry: (stat_address, char_offset, weapon_id, base_id, value, write_type)
# write_type: 'u16' for WriteUShort, 'u8' for WriteByte, 'u32' for WriteUInt,
#             'f64' for WriteDouble, 'f32' for WriteFloat

BALANCE_CHANGES = [
    # === TOAN ===
    # Baselard
    (endurance, 0, baselard, daggerid, 30, 'u16'),
    # Antique Sword
    (speed, 0, antiquesword, daggerid, 70, 'u16'),
    (fire, 0, antiquesword, daggerid, 15, 'u16'),
    # Kitchen Knife
    (whp, 0, kitchenknife, daggerid, 50, 'u16'),
    (attack, 0, kitchenknife, daggerid, 25, 'u16'),
    (endurance, 0, kitchenknife, daggerid, 30, 'u16'),
    (ice, 0, kitchenknife, daggerid, 0, 'u16'),
    (thunder, 0, kitchenknife, daggerid, 8, 'u16'),
    (sea, 0, kitchenknife, daggerid, 90, 'u16'),
    (buildup + 5, 0, kitchenknife, daggerid, 0, 'u16'),
    # Tsukikage
    (endurance, 0, tsukikage, daggerid, 33, 'u16'),
    (speed, 0, tsukikage, daggerid, 80, 'u16'),
    # Macho Sword
    (effect2, 0, machosword, daggerid, 32, 'u8'),
    # Heaven's Cloud
    (synth3, 0, heavenscloud, daggerid, 1, 'u16'),
    # Lamb's Sword
    (synth3, 0, lambsswordnormal, daggerid, 1, 'u16'),
    # Brave Ark
    (synth3, 0, braveark, daggerid, 1, 'u16'),
    # Big Bang
    (speed, 0, bigbang, daggerid, 70, 'u16'),
    # Small Sword
    (whp, 0, smallsword, daggerid, 35, 'u16'),
    (magic, 0, smallsword, daggerid, 17, 'u16'),
    (sea, 0, smallsword, daggerid, 0, 'u16'),
    (metal, 0, smallsword, daggerid, 10, 'u16'),
    # Sand Breaker
    (whp, 0, sandbreaker, daggerid, 45, 'u16'),
    (endurance, 0, sandbreaker, daggerid, 25, 'u16'),
    (synth3, 0, sandbreaker, daggerid, 1, 'u16'),
    # Drain Seeker
    (whp, 0, drainseeker, daggerid, 60, 'u16'),
    # Chopper
    (speed, 0, chopper, daggerid, 60, 'u16'),
    # Choora
    (whp, 0, choora, daggerid, 57, 'u16'),
    (attack, 0, choora, daggerid, 45, 'u16'),
    (speed, 0, choora, daggerid, 70, 'u16'),
    (ice, 0, choora, daggerid, 10, 'u16'),
    (thunder, 0, choora, daggerid, 15, 'u16'),
    (undead, 0, choora, daggerid, 15, 'u16'),
    (beast, 0, choora, daggerid, 15, 'u16'),
    (metal, 0, choora, daggerid, 15, 'u16'),
    (synth3, 0, choora, daggerid, 1, 'u16'),
    # Claymore
    (undead, 0, claymore, daggerid, 10, 'u16'),
    (beast, 0, claymore, daggerid, 10, 'u16'),
    (mage, 0, claymore, daggerid, 10, 'u16'),
    # Maneater
    (endurance, 0, maneater, daggerid, 44, 'u16'),
    (speed, 0, maneater, daggerid, 70, 'u16'),
    (magic, 0, maneater, daggerid, 45, 'u16'),
    (ice, 0, maneater, daggerid, 15, 'u16'),
    (thunder, 0, maneater, daggerid, 15, 'u16'),
    (holy, 0, maneater, daggerid, 15, 'u16'),
    (undead, 0, maneater, daggerid, 15, 'u16'),
    (beast, 0, maneater, daggerid, 15, 'u16'),
    (metal, 0, maneater, daggerid, 15, 'u16'),
    (mimic, 0, maneater, daggerid, 10, 'u16'),
    # Bone Rapier
    (whp, 0, bonerapier, daggerid, 38, 'u16'),
    (magic, 0, bonerapier, daggerid, 26, 'u16'),
    # Sax
    (speed, 0, sax, daggerid, 60, 'u16'),
    (fire, 0, sax, daggerid, 6, 'u16'),
    (sky, 0, sax, daggerid, 10, 'u16'),
    # 7 Branch Sword
    (whp, 0, sevenbranchsword, daggerid, 47, 'u16'),
    (endurance, 0, sevenbranchsword, daggerid, 47, 'u16'),
    (magic, 0, sevenbranchsword, daggerid, 37, 'u16'),
    (dinoslayer, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (undead, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (sea, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (stone, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (plant, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (beast, 0, sevenbranchsword, daggerid, 8, 'u16'),
    (sky, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (metal, 0, sevenbranchsword, daggerid, 10, 'u16'),
    (mimic, 0, sevenbranchsword, daggerid, 7, 'u16'),
    (mage, 0, sevenbranchsword, daggerid, 8, 'u16'),
    # Cross Hinder
    (endurance, 0, crosshinder, daggerid, 50, 'u16'),
    (speed, 0, crosshinder, daggerid, 70, 'u16'),
    (magic, 0, crosshinder, daggerid, 32, 'u16'),
    # Chronicle 2
    (maxattack, 0, chronicletwo, daggerid, 999, 'u16'),

    # === XIAO ===
    # Wooden Slingshot
    (attack, xiaooffset, woodenslingshot, woodenid, 6, 'u16'),
    (magic, xiaooffset, woodenslingshot, woodenid, 2, 'u16'),
    (fire, xiaooffset, woodenslingshot, woodenid, 4, 'u16'),
    # Bandit Slingshot
    (buildup, xiaooffset, banditslingshot, woodenid, 128, 'u32'),
    # Bone Slingshot
    (attack, xiaooffset, boneslingshot, woodenid, 11, 'u16'),
    (endurance, xiaooffset, boneslingshot, woodenid, 30, 'u16'),
    # Hardshooter
    (speed, xiaooffset, hardshooter, woodenid, 60, 'u16'),
    # Matador
    (effect2, xiaooffset, matador, woodenid, 16, 'u8'),

    # === GORO ===
    # Turtle Shell
    (magic, gorooffset, turtleshell, malletid, 10, 'u16'),
    # Big Bucks Hammer
    (buildup, gorooffset, bigbuckshammer, malletid, 8, 'u32'),
    # Frozen Tuna
    (whp, gorooffset, frozentuna, malletid, 65, 'u16'),
    # Gaia Hammer
    (endurance, gorooffset, gaiahammer, malletid, 25, 'u16'),
    # Trial Hammer
    (attack, gorooffset, trialhammer, malletid, 30, 'u16'),
    (endurance, gorooffset, trialhammer, malletid, 25, 'u16'),

    # === RUBY ===
    # Gold Ring
    (attack, rubyoffset, goldring, goldringid, 15, 'u16'),
    (magic, rubyoffset, goldring, goldringid, 30, 'u16'),
    # Bandit's Ring
    (attack, rubyoffset, banditsring, goldringid, 30, 'u16'),
    (maxattack, rubyoffset, banditsring, goldringid, 50, 'u16'),
    (magic, rubyoffset, banditsring, goldringid, 20, 'u16'),
    (buildup, rubyoffset, banditsring, goldringid, 8200, 'i32'),
    # Platinum Ring
    (attack, rubyoffset, platinumring, goldringid, 23, 'u16'),
    # Pocklekul
    (attack, rubyoffset, pocklekul, goldringid, 28, 'u16'),
    (magic, rubyoffset, pocklekul, goldringid, 28, 'u16'),
    (holy, rubyoffset, pocklekul, goldringid, 0, 'u16'),
    (buildup, rubyoffset, pocklekul, goldringid, 8256, 'u16'),
    # Thorn Armlet
    (maxmagic, rubyoffset, thornarmlet, goldringid, 65, 'u16'),
    (buildup, rubyoffset, thornarmlet, goldringid, 128, 'u16'),
    # Athena's Armlet — NOTE: C# uses daggerid here (likely a bug in original)
    (effect2, rubyoffset, athenasarmlet, daggerid, 32, 'u8'),

    # === UNGAGA === (loop: +10 atk, +10 maxatk, +15 endurance for all except id 357)
    # Handled specially in apply_balance_changes()

    # === OSMOND === (loop: +15 atk, +15 maxatk for all)
    # Handled specially in apply_balance_changes()

    # Babel's Spear
    (synth4, ungagaoffset, babelsspear, stickid, 1, 'u16'),
    # Skunk (Osmond)
    (buildup, osmondoffset, skunk, machinegunid, 386, 'u16'),
]

# Special: Lamb sword threshold writes (not weapon-offset based)
LAMB_CHANGES = [
    (lambTransformThreshold, 0.5, 'f64'),
    (lambStatsThreshold, 0.5, 'f32'),
]

# Ungaga weapon range for loop buff
UNGAGA_WEAPON_RANGE = (348, 360)  # inclusive
UNGAGA_SKIP_ID = 357
UNGAGA_BUFFS = {'attack': 10, 'maxattack': 10, 'endurance': 15}

# Osmond weapon range for loop buff
OSMOND_WEAPON_RANGE = (machinegun, machinegun + 10)  # machinegun through swallow
OSMOND_BUFFS = {'attack': 15, 'maxattack': 15}

# Check address: if this value != 30, balance hasn't been applied yet
BALANCE_CHECK_ADDR = endurance + (weaponoffset * (baselard - daggerid))
BALANCE_CHECK_VALUE = 30
