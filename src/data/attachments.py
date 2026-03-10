# Gem and attachment stat data for overlay display
# Stats: (At, Ed, Sp, Mp, Fi, Ic, Th, Wi, Ho, Din, Und, Sea, Stn, Pln, Bst, Fly, Mtl, Mmc, Mag)
# Source: Dark Cloud game data. Content paraphrased for compliance with licensing restrictions.

_STAT_NAMES = ("Attack", "Endurance", "Speed", "Magic", "Fire", "Ice", "Thunder", "Wind", "Holy",
               "Dino", "Undead", "Sea", "Stone", "Plant", "Beast", "Sky", "Metal", "Mimic", "Mage")

# item_id -> (name, stat_tuple)
ATTACHMENT_STATS = {
    81: ("Fire",          (0,0,0,0, 3,0,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    82: ("Ice",           (0,0,0,0, 0,3,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    83: ("Thunder",       (0,0,0,0, 0,0,3,0,0, 0,0,0,0,0,0,0,0,0,0)),
    84: ("Wind",          (0,0,0,0, 0,0,0,3,0, 0,0,0,0,0,0,0,0,0,0)),
    85: ("Holy",          (0,0,0,0, 0,0,0,0,3, 0,0,0,0,0,0,0,0,0,0)),
    90: ("Synth Sphere",  (0,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    91: ("Attack+1",      (1,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    92: ("Attack+2",      (2,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    93: ("Attack+3",      (3,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    94: ("Endurance+1",   (0,1,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0)),
    # IDs 95-107 are gems
    95:  ("Garnet",    (5,0,0,0, 10,0,0,0,0, 0,0,0,10,0,10,0,0,0,0)),
    96:  ("Amethyst",  (0,0,0,0, 0,10,0,0,0, 10,0,0,0,0,0,0,0,0,10)),
    97:  ("Aquamarine",(0,0,0,0, 0,10,0,0,0, 0,0,10,0,0,0,10,0,0,0)),
    98:  ("Diamond",   (0,0,0,0, 0,0,0,0,0, 5,5,5,5,5,5,5,10,5,5)),
    99:  ("Emerald",   (0,0,0,10, 0,0,0,0,0, 10,0,0,0,10,0,0,0,0,0)),
    100: ("Pearl",     (0,10,0,0, 0,0,10,0,0, 0,10,0,0,0,0,0,0,0,0)),
    101: ("Ruby",      (0,0,10,0, 10,0,0,0,0, 0,0,0,0,0,0,0,0,0,10)),
    102: ("Peridot",   (5,0,0,0, 0,0,0,0,10, 0,0,0,0,10,10,0,0,0,0)),
    103: ("Sapphire",  (0,0,0,10, 0,0,0,10,0, 0,0,0,0,0,0,10,0,0,0)),
    104: ("Opal",      (0,10,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,10,0,10)),
    105: ("Topaz",     (5,0,10,0, 0,0,0,0,0, 0,10,0,0,0,0,10,0,0,0)),
    106: ("Turquoise", (0,0,0,0, 0,10,0,0,0, 0,0,0,10,0,0,0,0,10,0)),
    107: ("Sun",       (10,0,0,0, 10,10,10,10,10, 3,3,3,3,3,3,3,3,3,3)),
    111: ("Dragon Slayer", (0,0,0,0, 0,0,0,0,0, 3,0,0,0,0,0,0,0,0,0)),
    112: ("Undead Buster", (0,0,0,0, 0,0,0,0,0, 0,3,0,0,0,0,0,0,0,0)),
    113: ("Sea Killer",    (0,0,0,0, 0,0,0,0,0, 0,0,3,0,0,0,0,0,0,0)),
    114: ("Stone Breaker", (0,0,0,0, 0,0,0,0,0, 0,0,0,3,0,0,0,0,0,0)),
    115: ("Plant Buster",  (0,0,0,0, 0,0,0,0,0, 0,0,0,0,3,0,0,0,0,0)),
    116: ("Beast Buster",  (0,0,0,0, 0,0,0,0,0, 0,0,0,0,0,3,0,0,0,0)),
    117: ("Sky Hunter",    (0,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,3,0,0,0)),
    118: ("Metal Breaker", (0,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,3,0,0)),
    119: ("Mimic Breaker", (0,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,3,0)),
    120: ("Mage Slayer",   (0,0,0,0, 0,0,0,0,0, 0,0,0,0,0,0,0,0,0,3)),
}

STAT_NAMES = _STAT_NAMES


def get_attachment_info(item_id):
    """Return (name, [(stat_name, value), ...]) for non-zero stats, or None."""
    entry = ATTACHMENT_STATS.get(item_id)
    if not entry:
        return None
    name, stats = entry
    nonzero = [(n, v) for n, v in zip(_STAT_NAMES, stats) if v]
    return (name, nonzero) if nonzero else None
