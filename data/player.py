"""Auto-generated from Player.cs — do not edit manually.

Character stats and weapon slot addresses for all 6 playable characters.
Each character has base stats (hp, defense, thirst, etc.) and 10 weapon slots.
Weapon slots use offset math: slot N = slot 0 + WEAPON_SLOT_OFFSET * N.
Characters chain: next character's slot 0 = previous character's slot 0 + CHARACTER_OFFSET.
"""

# Offset between weapon slots within a character
WEAPON_SLOT_OFFSET = 0xF8

# Offset between characters' weapon slot 0
CHARACTER_OFFSET = 0xAA8

# Weapon slot field offsets relative to slot base (id address)
# Derived from Toan.WeaponSlot0 base = 0x21CDDA58
WEAPON_SLOT_FIELDS = {
    'id':           0x00,  # 0x21CDDA58
    'level':        0x02,  # 0x21CDDA5A
    'attack':       0x04,  # 0x21CDDA5C
    'endurance':    0x06,  # 0x21CDDA5E
    'speed':        0x08,  # 0x21CDDA60
    'magic':        0x0A,  # 0x21CDDA62
    'whpMax':       0x0C,  # 0x21CDDA64
    'whp':          0x10,  # 0x21CDDA68
    'xp':           0x14,  # 0x21CDDA6C
    'elementHUD':   0x16,  # 0x21CDDA6E  (0=Fire,1=Ice,2=Thunder,3=Wind,4=Holy,5=None)
    'fire':         0x17,  # 0x21CDDA6F
    'ice':          0x18,  # 0x21CDDA70
    'thunder':      0x19,  # 0x21CDDA71
    'wind':         0x1A,  # 0x21CDDA72
    'holy':         0x1B,  # 0x21CDDA73
    'aDragon':      0x1C,  # 0x21CDDA74
    'aUndead':      0x1D,  # 0x21CDDA75
    'aMarine':      0x1E,  # 0x21CDDA76
    'aRock':        0x1F,  # 0x21CDDA77
    'aPlant':       0x20,  # 0x21CDDA78
    'aBeast':       0x21,  # 0x21CDDA79
    'aSky':         0x22,  # 0x21CDDA7A
    'aMetal':       0x23,  # 0x21CDDA7B
    'aMimic':       0x24,  # 0x21CDDA7C
    'aMage':        0x25,  # 0x21CDDA7D
    # Attachment slot 1
    'slot1_itemId':              0x28,  # 0x21CDDA80
    'slot1_synthesisedItemId':   0x2A,  # 0x21CDDA82
    'slot1_special1':            0x2C,  # 0x21CDDA84
    'slot1_special2':            0x2D,  # 0x21CDDA85
    'slot1_synthesisedItemLevel':0x2E,  # 0x21CDDA86
    'slot1_attack':              0x30,  # 0x21CDDA88
    'slot1_endurance':           0x32,  # 0x21CDDA8A
    'slot1_speed':               0x34,  # 0x21CDDA8C
    'slot1_magic':               0x36,  # 0x21CDDA8E
    'slot1_fire':                0x38,  # 0x21CDDA90
    'slot1_ice':                 0x39,  # 0x21CDDA91
    'slot1_thunder':             0x3A,  # 0x21CDDA92
    'slot1_wind':                0x3B,  # 0x21CDDA93
    'slot1_holy':                0x3C,  # 0x21CDDA94
    'slot1_dragon':              0x3D,  # 0x21CDDA95
    'slot1_undead':              0x3E,  # 0x21CDDA96
    'slot1_sea':                 0x3F,  # 0x21CDDA97
    'slot1_rock':                0x40,  # 0x21CDDA98
    'slot1_plant':               0x41,  # 0x21CDDA99
    'slot1_beast':               0x42,  # 0x21CDDA9A
    'slot1_sky':                 0x43,  # 0x21CDDA9B
    'slot1_metal':               0x44,  # 0x21CDDA9C
    'slot1_mimic':               0x45,  # 0x21CDDA9D
    'slot1_mage':                0x46,  # 0x21CDDA9E
    # Special bitfields (further into the slot block)
    'special1':     0xEE,  # 0x21CDDB46 (01=unknown, 02=BigBucks, 04=Poor, 08=Quench, 16=Thirst, 32=Poison, 64=Stop, 128=Steal)
    'special2':     0xEF,  # 0x21CDDB47 (02=Durable, 04=Drain, 08=Heal, 16=Critical, 32=AbsUp)
    # Custom mod attributes
    'hasChangedBySynth':       0xC8,  # 0x21CDDB20
    'weaponFormerStatsValue':  0xCA,  # 0x21CDDB22
}

# Toan's WeaponSlot0 base address (all other addresses computed from this)
_TOAN_SLOT0_BASE = 0x21CDDA58


def weapon_slot_addr(char_index, slot_num, field):
    """Get the memory address for a weapon slot field.

    Args:
        char_index: 0=Toan, 1=Xiao, 2=Goro, 3=Ruby, 4=Ungaga, 5=Osmond
        slot_num: 0-9
        field: field name from WEAPON_SLOT_FIELDS
    Returns:
        Memory address as int
    """
    return (_TOAN_SLOT0_BASE
            + CHARACTER_OFFSET * char_index
            + WEAPON_SLOT_OFFSET * slot_num
            + WEAPON_SLOT_FIELDS[field])


# --- Character stat addresses ---

class Toan:
    hp = 0x21CD955E
    maxHP = 0x21CD9552
    defense = 0x21CDD894
    thirst = 0x21CDD850
    thirstMax = 0x21CDD83A
    status = 0x21CDD814
    statusTimer = 0x21CDD824
    currentWeaponSlot = 0x21CDD88C
    CHAR_INDEX = 0

class Xiao:
    hp = 0x21CD9560
    maxHP = 0x21CD9554
    defense = 0x21CDD898
    thirst = 0x21CDD854
    thirstMax = 0x21CDD83E
    status = 0x21CDD818
    statusTimer = 0x21CDD828
    currentWeaponSlot = 0x21CDD88D
    CHAR_INDEX = 1

class Goro:
    hp = 0x21CD9562
    maxHP = 0x21CD9556
    defense = 0x21CDD89C
    thirst = 0x21CDD858
    thirstMax = 0x21CDD842
    status = 0x21CDD81C
    statusTimer = 0x21CDD82C
    currentWeaponSlot = 0x21CDD88E
    CHAR_INDEX = 2

class Ruby:
    hp = 0x21CD9564
    maxHP = 0x21CD9558
    defense = 0x21CDD8A0
    thirst = 0x21CDD85C
    thirstMax = 0x21CDD846
    status = 0x21CDD820
    statusTimer = 0x21CDD830
    currentWeaponSlot = 0x21CDD88F
    CHAR_INDEX = 3

class Ungaga:
    hp = 0x21CD9566
    maxHP = 0x21CD955A
    defense = 0x21CDD8A4
    thirst = 0x21CDD860
    thirstMax = 0x21CDD84A
    status = 0x21CDD824
    statusTimer = 0x21CDD834
    currentWeaponSlot = 0x21CDD890
    CHAR_INDEX = 4

class Osmond:
    hp = 0x21CD9568
    maxHP = 0x21CD955C
    defense = 0x21CDD8A8
    thirst = 0x21CDD864
    thirstMax = 0x21CDD84E
    status = 0x21CDD828
    statusTimer = 0x21CDD838
    currentWeaponSlot = 0x21CDD891
    CHAR_INDEX = 5

CHARACTERS = [Toan, Xiao, Goro, Ruby, Ungaga, Osmond]
CHARACTER_NAMES = ['Toan', 'Xiao', 'Goro', 'Ruby', 'Ungaga', 'Osmond']

# Status effect values
STATUS_FREEZE = 4
STATUS_STAMINA = 8
STATUS_POISON = 16
STATUS_CURSE = 32
STATUS_GOO = 64

# Inventory addresses
inventoryCurrentSize = 0x21CDD8AD
inventoryTotalSize = 0x21CDD8AC

# Animation
animationId = 0x21DC448C

# Ruby charge
rubyAnimationId = 0x21DC4494  # Ruby-specific animation (16 = releasing charge)
chargeGlowTimer = 0x21DC449E

# Inventory
FIRST_BAG_ATTACHMENT = 0x21CE1A48
ATTACHMENT_OFFSET = 0x20
ATTACHMENT_SIZE = 40  # inventorySizeAttachments
