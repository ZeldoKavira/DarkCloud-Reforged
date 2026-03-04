"""Daily shop item rotation. Ported from DailyShopItem.cs."""

import logging
import random

from data import items
from data.customchests import (
    dbcSecondHalfWeapons, wiseowlSecondHalfWeapons,
    shipwreckSecondHalfWeapons, sunmoonSecondHalfWeapons,
    moonseaFirstHalfWeapons, galleryWeapons,
)

log = logging.getLogger(__name__)

# Shared tables
_gems = [items.garnet, items.amethyst, items.aquamarine, items.diamond,
         items.emerald, items.pearl, items.ruby, items.peridot,
         items.sapphire, items.opal, items.topaz, items.turquoise]
_useful = [items.amulet_antifreeze, items.amulet_anticurse,
           items.amulet_antigoo, items.amulet_antidote,
           items.staminadrink, items.mightyhealing]

# Shop rotations (5-day cycle)
_ROTATIONS = {
    'gaffer': [
        [items.treasurechestkey, items.treasurechestkey, items.tramoil],
        _gems,
        [items.mimi, items.prickly],
        _useful,
        list(dbcSecondHalfWeapons),
    ],
    'wiseowl': [
        [items.carrot, items.minon, items.battan],
        _useful,
        list(wiseowlSecondHalfWeapons),
        [items.treasurechestkey, items.treasurechestkey, items.sundew],
        _gems,
    ],
    'jack': [list(shipwreckSecondHalfWeapons)] * 5,
    'joker': [
        _gems,
        [items.carrot, items.minon, items.battan, items.mimi, items.prickly],
        _useful,
        [items.dragonslayer, items.undeadbuster, items.seakiller,
         items.stonebreaker, items.plantbuster, items.beastbuster,
         items.skyhunter, items.metalbreaker, items.mimicbreaker, items.mageslayer],
        [181],
    ],
    'brooke': [
        [items.amulet_antifreeze, items.amulet_anticurse,
         items.amulet_antigoo, items.amulet_antidote, items.staminadrink],
        list(sunmoonSecondHalfWeapons),
        [items.treasurechestkey, items.treasurechestkey, items.secretpathkey],
        _gems,
        [items.poisonousapple, items.carrot, items.minon, items.battan,
         items.evy, items.mimi, items.prickly],
    ],
    'ledan': [
        [items.treasurechestkey, items.treasurechestkey, items.braverylaunch],
        _gems,
        [items.metalbreaker, items.mimicbreaker],
        _useful,
        list(moonseaFirstHalfWeapons),
    ],
    'fairyking': [
        list(galleryWeapons),
        [items.treasurechestkey, items.treasurechestkey, items.flappingduster],
        [items.poisonousapple, items.carrot, items.potatocake, items.minon,
         items.battan, items.evy, items.mimi, items.prickly],
        _useful,
        [items.treasurechestkey, items.treasurechestkey, items.flappingduster],
    ],
}

# Save-file addresses for daily items (one per shop)
_SAVE_ADDRS = [0x21CE447C, 0x21CE447E, 0x21CE4480,
               0x21CE4482, 0x21CE4484, 0x21CE4486, 0x21CE4488]
_SHOP_ORDER = ['gaffer', 'wiseowl', 'jack', 'joker', 'brooke', 'ledan', 'fairyking']

# Shop slot addresses for daily item display
_SLOT_ADDRS = [0x20292046, 0x20292068, 0x20292178,
               0x2029221A, 0x202921A8, 0x202921CE, 0x202921EC]


def base_shop_changes(mem):
    """One-time base shop inventory modifications."""
    # Gaffer: replace attachment slots with elements + dragon slayer + gold bullion
    writes = [
        (0x20292038, items.fire), (0x2029203A, items.ice),
        (0x2029203C, items.thunder), (0x2029203E, items.wind),
        (0x20292040, items.holy), (0x20292042, items.dragonslayer),
        (0x20292044, items.goldbullion),
        # Fairy King attachment shop
        (0x202922E0, items.metalbreaker), (0x202922E2, items.mimicbreaker),
    ]
    for a, v in writes:
        mem.write_short(a, v)
    log.info("Base shop changes applied")


def reroll_daily_rotation(mem, in_game_day):
    """Roll new daily items for each shop based on day cycle."""
    rot = in_game_day % 5
    for i, name in enumerate(_SHOP_ORDER):
        table = _ROTATIONS[name][rot]
        val = random.choice(table)
        mem.write_short(_SAVE_ADDRS[i], val)
    log.info("Daily Shop Items rerolled!")
    set_daily_items_to_shop(mem)


def set_daily_items_to_shop(mem):
    """Copy saved daily items into shop display slots."""
    for save, slot in zip(_SAVE_ADDRS, _SLOT_ADDRS):
        mem.write_short(slot, mem.read_short(save))

    # Fairy King crystal eyeball if demon shaft unlocked
    if mem.read_byte(0x21CE4464) != 0:
        mem.write_short(0x202921EE, 231)
        mem.write_short(0x20291DD8, 5000)
