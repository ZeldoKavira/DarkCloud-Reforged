"""Dialogue system. Ported from Dialogues.cs.

Handles NPC dialogue text encoding and writing to game memory.
The dialogue strings themselves are stored as data — the encoding
and write mechanics are the core logic.
"""

import logging
from game import addresses as addr

log = logging.getLogger(__name__)

# Default dialogue base addresses per area
_DEFAULT_ADDRS = {
    0: 0x206494C4,   # Norune
    1: 0x20649B88,   # Matataki
    2: 0x20649B8A,   # Queens
    3: 0x2065207C,   # Muska Racka
    14: 0x20649000,  # Brownboo
    23: 0x20648F50,  # Yellow Drops
    38: 0x20649710,  # Sun & Moon
    42: 0x20648EC8,  # Dark Heaven
}

# NPC character IDs per area
NORUNE_NPCS = [12592, 12848, 13104, 13360, 13616, 13872, 14128, 14384, 14640, 12337, 12849, 13105, 13361]
MATATAKI_NPCS = [12594, 12850, 13106, 13362, 13618, 13874, 14130, 14386, 14642, 12339, 12595, 12851]
QUEENS_NPCS = [13107, 13363, 13619, 13875, 14131, 14643, 12340, 12596, 12852, 13108, 13364, 13620, 14644]
MUSKA_NPCS = [13876, 14388, 12341, 12597, 12853, 13109, 13365, 13621, 13877, 14133, 14389]

# Side quest NPC IDs per area
NORUNE_QUEST_NPCS = [12592, 13872, 13360, 13361]
MATATAKI_QUEST_NPCS = [13618, 13362, 12594]
QUEENS_QUEST_NPCS = [13108, 13363, 12852]
MUSKA_QUEST_NPCS = [14388, 13109, 12341]


# Raw gameCharacters index encoding (matches C# SetDialogue/SetDialogueOptions)
# This matches C# SetDialogueOptions which writes the array index directly
_OPTIONS_CHAR_INDEX = {}
_OPTIONS_CHARS = (
    '^§_¤§§§§§§§§§§Ȟ§§§§§§§§§§§§§§§§§§'  # 0-33 (34 chars, matching C# indices 0-33)
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'             # 34-59 -> C# 33-58... 
)
# Build from the C# gameCharacters array directly (128 entries, index 0-127)
_OPT_CHARS = list('^§_¤') + ['§']*10 + ['Ȟ'] + ['§']*18 + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + list('abcdefghijklmnopqrstuvwxyz') + list('´="!?#&+-*/%()@|<>{}[]:,.$') + list('0123456789ŤӾƱƀŲŌ ')
_OPT_MAP = {}
for _i, _ch in enumerate(_OPT_CHARS):
    if _ch not in _OPT_MAP or _ch == '§':  # first occurrence wins, except § is filler
        if _ch != '§':
            _OPT_MAP[_ch] = _i


def _encode_options(text):
    """Encode dialogue options text using raw index encoding (C# SetDialogueOptions style)."""
    out = []
    for ch in text:
        if ch in _OPT_MAP:
            idx = _OPT_MAP[ch]
        else:
            idx = 127  # space fallback
        # C# maps high indices: 121→250, 122→251, ..., 126→255, 127→2
        if idx > 120:
            val = (idx - 121) + 250 if idx <= 126 else 2
        else:
            val = idx
        out.append(val)
        # Suffix byte
        if val in (0, 2, 3):
            out.append(255)
        elif val >= 250:
            out.append(250)
        else:
            out.append(253)
    # Terminator
    out.extend([1, 255])
    return out


def _write_options(mem, base_addr, text):
    """Encode and write dialogue options to memory."""
    encoded = _encode_options(text)
    for i, b in enumerate(encoded):
        mem.write_byte(base_addr + i, b)
    return len(encoded)


def set_default_dialogue(mem, area):
    """Write a default/fallback dialogue for the given area."""
    base = _DEFAULT_ADDRS.get(area)
    if base is None:
        return
    text = "Hello."
    if area == 14:
        text = "Hey chill, don\u00b4t come talking so fast!"
    elif area == 38:
        text = "Wait a second please,^I was doing something."
    _write_options(mem, base, text)


def set_dialogue_options(mem, area, building_check=False):
    """Write dialogue menu options for the given area."""
    _OPTION_CFG = {
        0: {'base': 0x206492F6, 'storage_house': 5, 'storage_addr': 0x20649364,
            'normal': "Hello.^  How should I rebuild Norune?^  It\u00b4s finished!^  Do you have any sidequests?",
            'storage': "   Can I check in some items?^  Hello.^  How should I rebuild Norune?^  It\u00b4s finished!",
            'sq_id': 107},
        1: {'base': 0x20649306, 'storage_house': 5, 'storage_addr': 0x2064938A,
            'normal': "Hello.^  How should I rebuild Matataki Village?^  It\u00b4s finished!^  Do you have any sidequests?",
            'storage': "  Can I check in some items?^  Hello.^  How should I rebuild Matataki Village?^  It\u00b4s finished!",
            'sq_id': 107},
        2: {'base': 0x206492DA, 'storage_house': 7, 'storage_addr': 0x20649354,
            'normal': "Hi.^  Any requests for rebuilding Queens?^  It\u00b4s finished!^  Do you have any sidequests?",
            'storage': "  Can I check in some items?^  Hello.^  Any requests for rebuilding Queens?^  It\u00b4s finished!",
            'sq_id': 127},
        3: {'base': 0x20649288, 'storage_house': 5, 'storage_addr': 0x2064930C,
            'normal': "Hello.^  Any requests for building Muska Racka?^  It\u00b4s finished!^  Do you have any sidequests?",
            'storage': "  Can I check in some items?^  Hello.^  Any requests for building Muska Racka?^  It\u00b4s finished!",
            'sq_id': 147},
    }
    cfg = _OPTION_CFG.get(area)
    if not cfg:
        # Yellow Drops (23) special handling
        if area == 23 and building_check:
            npc_type = mem.read_byte(0x21D26FD4)
            if npc_type == 0:
                _write_options(mem, 0x20649004, "Can I shop here?^  Hello.^  Do you have any sidequests?")
            elif npc_type == 1:
                _write_options(mem, 0x20649004, "Can I check in some items?^  Hello.^  Do you have any sidequests?")
        return

    if not building_check:
        _write_options(mem, cfg['base'], cfg['normal'])
    else:
        house = mem.read_byte(0x202A2820)
        if house == cfg['storage_house']:
            _write_options(mem, cfg['storage_addr'], cfg['storage'])
        elif area == 0 and mem.read_int(0x202A2820) == -1:
            _write_options(mem, cfg['base'], "Hello.^  Do you have any sidequests?")
        else:
            _write_options(mem, cfg['base'], cfg['normal'])


class DialogueState:
    """Tracks dialogue state per area/NPC."""

    def __init__(self):
        self.current_area = 255
        self.current_char = 0  # chr file signature
        self.dialogue_checks = [0] * 15
        self.saved_check = 0
        self.is_using_ally = False
        self.storage_backup = None

    def on_area_change(self, mem, new_area):
        """Reset dialogue state when entering a new area."""
        self.current_area = new_area
        self.dialogue_checks = [0] * 15
        self.current_char = 0
        # C# only calls SetDefaultDialogue for areas 42 and 14
        if new_area in (42, 14):
            set_default_dialogue(mem, new_area)

    def change_dialogue(self, idx=None):
        """Toggle dialogue flag between 0 and 1 for current/given index."""
        i = idx if idx is not None else self.saved_check
        self.dialogue_checks[i] = 0 if self.dialogue_checks[i] == 1 else 1

    def set_npc_dialogue(self, mem, npc_id, text, base_addr):
        """Write custom dialogue for a specific NPC."""
        _write_options(mem, base_addr, text)
        log.debug("Set dialogue for NPC %d", npc_id)

    def set_dialogue(self, mem, npc_slot, is_ally, is_sidequest, is_finished=False):
        """Full dialogue dispatch. Ported from Dialogues.SetDialogue().

        npc_slot: NPC proximity slot index (0-5)
        is_ally: True if using non-Toan character
        is_sidequest: True if sidequest dialogue requested
        is_finished: True if "it's finished" dialogue requested
        """
        area = mem.read_byte(0x202A2518)

        # Area change detection
        if area != self.current_area:
            self.current_area = area
            if area in (42, 14):
                set_default_dialogue(mem, area)
            self.dialogue_checks = [0] * 15
            self.current_char = 0

        chr_sig = mem.read_int(addr.CHR_FILE_LOC + 6)

        # Character change — reload dialogue arrays
        if chr_sig != self.current_char:
            if is_ally:
                self.dialogue_checks = [0] * 15
            self.current_char = chr_sig
            if area in (42, 14):
                set_default_dialogue(mem, area)

        # Read NPC character ID from proximity slot
        npc_addr = npc_slot * 0x14A0 + 0x21D26FD9
        npc_id = mem.read_short(npc_addr)

        # Get dialogue text
        text = self._resolve_dialogue(mem, area, npc_id, chr_sig,
                                      is_ally, is_sidequest, is_finished)
        if text is None:
            return

        # Get write address for this area
        write_addr = _get_write_addr(area, is_sidequest, is_finished)
        if write_addr:
            _write_options(mem, write_addr, text)
            log.debug("Wrote dialogue for NPC %d in area %d", npc_id, area)

    def _resolve_dialogue(self, mem, area, npc_id, chr_sig,
                          is_ally, is_sidequest, is_finished):
        """Determine the correct dialogue string."""
        from data import dialogues as dlg

        # Areas 0-3, 42: array-based NPC lookup
        npc_lists = {0: NORUNE_NPCS, 1: MATATAKI_NPCS,
                     2: QUEENS_NPCS, 3: MUSKA_NPCS}
        quest_lists = {0: NORUNE_QUEST_NPCS, 1: MATATAKI_QUEST_NPCS,
                       2: QUEENS_QUEST_NPCS, 3: MUSKA_QUEST_NPCS}
        finished_arrays = {0: dlg.norunefinishedDialogue,
                           1: dlg.matatakifinishedDialogue,
                           2: dlg.queensfinishedDialogue,
                           3: dlg.muskafinishedDialogue}

        if area in npc_lists:
            npcs = npc_lists[area]
            if npc_id not in npcs:
                return None
            idx = npcs.index(npc_id)

            if is_sidequest:
                return self._get_sidequest_dialogue(mem, area, npc_id)
            if is_finished and area in finished_arrays:
                arr = finished_arrays[area]
                return arr[idx] if idx < len(arr) and arr[idx] else None

            d1, d2 = _get_dialogue_arrays(area, chr_sig)
            if d1 is None:
                return None
            self.saved_check = idx
            if self.dialogue_checks[idx] != 1:
                return d1[idx] if idx < len(d1) and d1[idx] else None
            else:
                return d2[idx] if d2 and idx < len(d2) and d2[idx] else None

        elif area == 42:  # Sun & Moon
            sun_npcs = [12337, 13111]
            if npc_id not in sun_npcs:
                return None
            idx = sun_npcs.index(npc_id)
            d1, d2 = _get_dialogue_arrays(area, chr_sig)
            if d1 is None:
                return None
            self.saved_check = idx
            if self.dialogue_checks[idx] != 1:
                return d1[idx] if idx < len(d1) and d1[idx] else None
            else:
                return d2[idx] if d2 and idx < len(d2) and d2[idx] else None

        elif area == 38:  # Dark Heaven — single dialogue
            d1, d2 = _get_darkheaven_dialogues(chr_sig)
            if d1 is None:
                return None
            self.saved_check = 0
            return d1 if self.dialogue_checks[0] != 1 else d2

        elif area == 14:  # Brownboo — special NPC ID handling
            return self._brownboo_dialogue(mem, npc_id, chr_sig, is_ally)

        elif area == 23:  # Yellow Drops — special NPC ID handling
            return self._yellowdrops_dialogue(mem, npc_id, chr_sig,
                                              is_sidequest)

        return None

    def _get_sidequest_dialogue(self, mem, area, npc_id):
        """Get sidequest dialogue for NPC. Delegates to SideQuestManager."""
        from mods.sidequests import QUEST_ADDRS, FISH_QUEST_ADDRS, get_fishing_quest_dialogue
        quest_lists = {0: NORUNE_QUEST_NPCS, 1: MATATAKI_QUEST_NPCS,
                       2: QUEENS_QUEST_NPCS, 3: MUSKA_QUEST_NPCS}
        quest_npcs = quest_lists.get(area, [])
        if npc_id in quest_npcs:
            if npc_id in FISH_QUEST_ADDRS:
                return get_fishing_quest_dialogue(mem, npc_id)
            return None  # Monster quest dialogue handled elsewhere
        # Special non-quest NPCs with hardcoded sidequest dialogue
        _SPECIAL = {
            12849: "I needed your help earlier,^but I\u00b4m okay now.\u00a4You see, I slipped on this^pink thing which made me all^slow and slimey.\u00a4Well, I survived from that disaster.",
            14386: "I wish you happened to be there.\u00a4One day I accidentally ventured^too deep into the forest and^was surronded by monsters.\u00a4Luckily, I had this red pouch which^allowed me to get back to safety.",
            13106: "Unless I was made of Gilda, I wouldn\u00b4t^buy fish bait from Mr. Mustache.^With the right weapon, you can find^plenty of bait in the forest.",
            13364: "There was a large fight a while ago.\u00a4I almost wanted to call you for help.^There was this thief who suddenly^took a sip of something and^became more powerful.\u00a4Thanks to the strength of Macho^Brothers\u00b4s bloodline, I was able^to deal with him myself.",
            13877: "How about you get me out of here?\u00a4I wish I had something to^blow up this darn door.\u00a4Oh wait, I probably shouldn\u00b4t^be in the cell then.",
        }
        if npc_id == 14640:  # Paige — check if Toan
            if mem.read_int(0x2029AA0E) == 1680945251:
                return "Did you buy bombs from Gaffer\u00b4s shop?^Please be careful \u0164,^I just want you to come home safely."
            return "Sorry, I don\u00b4t have any quests currently."
        if npc_id == 13107:  # King — check lamp
            from mods.sidequests import check_item_quest_reward
            if check_item_quest_reward(mem, 241, True, False):
                return "What do you want?\u00a4Wait... that lamp...\u00a4...that cursed lamp...\u00a4NO! Get it away from me!"
            return "I don\u00b4t need you to do sidequests,^those are for my henchmen."
        return _SPECIAL.get(npc_id, "Sorry, I don\u00b4t have any quests currently.")

    def _brownboo_dialogue(self, mem, npc_id, chr_sig, is_ally):
        """Handle Brownboo (area 14) special NPC dialogues."""
        from data import dialogues as dlg
        # Brownboo uses raw NPC byte ID, not short
        npc_byte = mem.read_byte(0x21D26FD9 - 5 + (npc_id if isinstance(npc_id, int) else 0))
        # Pickle (9), Fish master (5), Demon shaft NPC (3)
        # For regular NPCs, use brownboo arrays indexed by NPC byte
        talkable = {6, 7, 8, 10, 11, 12}
        d1, d2 = _get_dialogue_arrays(14, chr_sig)
        if d1 is not None and npc_byte in talkable:
            self.saved_check = npc_byte
            if not is_ally:
                return "Hello."
            if self.dialogue_checks[npc_byte] != 1:
                return d1[npc_byte] if npc_byte < len(d1) and d1[npc_byte] else None
            else:
                return d2[npc_byte] if d2 and npc_byte < len(d2) and d2[npc_byte] else None
        return None

    def _yellowdrops_dialogue(self, mem, npc_id, chr_sig, is_sidequest):
        """Handle Yellow Drops (area 23) special NPC dialogues."""
        from data import dialogues as dlg
        npc_byte = mem.read_byte(0x21D26FD9 - 5)
        talkable = {2, 3, 4, 5, 6, 7, 9, 10, 11, 12}
        d1, d2 = _get_dialogue_arrays(23, chr_sig)
        if d1 is not None and npc_byte in talkable:
            self.saved_check = npc_byte
            if self.dialogue_checks[npc_byte] != 1:
                return d1[npc_byte] if npc_byte < len(d1) and d1[npc_byte] else None
            else:
                return d2[npc_byte] if d2 and npc_byte < len(d2) and d2[npc_byte] else None
        return None

    def storage_save(self, mem, area):
        """Save original dialogue before storage overwrites it."""
        addrs = {0: 0x2064C088, 1: 0x2064C492, 2: 0x2064DB3A,
                 3: 0x2064DDB8, 23: 0x2064B11C}
        a = addrs.get(area)
        if a:
            size = 200 if area == 23 else 1000
            self.storage_backup = mem.read_bytes(a, size)

    def storage_restore(self, mem, area):
        """Restore original dialogue after leaving storage."""
        addrs = {0: 0x2064C088, 1: 0x2064C492, 2: 0x2064DB3A,
                 3: 0x2064DDB8, 23: 0x2064B11C}
        a = addrs.get(area)
        if a and self.storage_backup:
            mem.write_bytes(a, self.storage_backup)


# ── Character name replacement in game memory ────────────────

# Dialogue array lookup: (area, chr_signature) → (primary, secondary) arrays
def _get_dialogue_arrays(area, chr_sig):
    """Return (primary, secondary) dialogue arrays for area + character."""
    from data import dialogues as d
    _MAP = {
        (0, 791752805): (d.noruneXiao, d.noruneXiao2),
        (0, 791752819): (d.noruneGoro, d.noruneGoro2),
        (0, 791883877): (d.noruneRuby, d.noruneRuby2),
        (0, 792278899): (d.noruneUngaga, d.noruneUngaga2),
        (0, 792014949): (d.noruneOsmond, d.noruneOsmond2),
        (1, 791752805): (d.matatakiXiao, d.matatakiXiao2),
        (1, 791752819): (d.matatakiGoro, d.matatakiGoro2),
        (1, 791883877): (d.matatakiRuby, d.matatakiRuby2),
        (1, 792278899): (d.matatakiUngaga, d.matatakiUngaga2),
        (1, 792014949): (d.matatakiOsmond, d.matatakiOsmond2),
        (2, 791752805): (d.queensXiao, d.queensXiao2),
        (2, 791752819): (d.queensGoro, d.queensGoro2),
        (2, 791883877): (d.queensRuby, d.queensRuby2),
        (2, 792278899): (d.queensUngaga, d.queensUngaga2),
        (2, 792014949): (d.queensOsmond, d.queensOsmond2),
        (3, 791752805): (d.muskarackaXiao, d.muskarackaXiao2),
        (3, 791752819): (d.muskarackaGoro, d.muskarackaGoro2),
        (3, 791883877): (d.muskarackaRuby, d.muskarackaRuby2),
        (3, 792278899): (d.muskarackaUngaga, d.muskarackaUngaga2),
        (3, 792014949): (d.muskarackaOsmond, d.muskarackaOsmond2),
        (14, 791752805): (d.brownbooXiao, d.brownbooXiao2),
        (14, 791752819): (d.brownbooGoro, d.brownbooGoro2),
        (14, 791883877): (d.brownbooRuby, d.brownbooRuby2),
        (14, 792278899): (d.brownbooUngaga, d.brownbooUngaga2),
        (14, 792014949): (d.brownbooOsmond, d.brownbooOsmond2),
        (23, 791752805): (d.yellowdropsXiao, d.yellowdropsXiao2),
        (23, 791752819): (d.yellowdropsGoro, d.yellowdropsGoro2),
        (23, 791883877): (d.yellowdropsRuby, d.yellowdropsRuby2),
        (23, 792278899): (d.yellowdropsUngaga, d.yellowdropsUngaga2),
        (23, 792014949): (d.yellowdropsOsmond, d.yellowdropsOsmond2),
        (42, 791752805): (d.sunmoonXiao, d.sunmoonXiao2),
        (42, 791752819): (d.sunmoonGoro, d.sunmoonGoro2),
        (42, 791883877): (d.sunmoonRuby, d.sunmoonRuby2),
        (42, 792278899): (d.sunmoonUngaga, d.sunmoonUngaga2),
        (42, 792014949): (d.sunmoonOsmond, d.sunmoonOsmond2),
    }
    return _MAP.get((area, chr_sig), (None, None))


def _get_darkheaven_dialogues(chr_sig):
    """Return (primary, secondary) single dialogue strings for Dark Heaven."""
    from data import dialogues as d
    _MAP = {
        791752805: (d.darkheavenXiao, d.darkheavenXiao2),
        791752819: (d.darkheavenGoro, d.darkheavenGoro2),
        791883877: (d.darkheavenRuby, d.darkheavenRuby2),
        792278899: (d.darkheavenUngaga, d.darkheavenUngaga2),
        792014949: (d.darkheavenOsmond, d.darkheavenOsmond2),
    }
    return _MAP.get(chr_sig, (None, None))


# Write addresses per area for dialogue output
_WRITE_ADDRS = {
    0: 0x206507BE,   # Gaffer's hello
    1: 0x2064ECBC,   # Pao's hello
    2: 0x2064BED8,   # Suzy's hello
    3: 0x20649A56,   # Bonka's hello
    14: 0x2064ADCA,  # Pickle's message
    23: 0x2064AE4A,  # Aily's message
    38: 0x20649784,
    42: 0x20648FBA,
}
_SIDEQUEST_ADDRS = {0: 0x2064C088, 1: 0x2064C492, 2: 0x2064DB3A, 3: 0x2064DDB8}
_FINISHED_ADDRS = {0: 0x206519EE, 1: 0x2064F7BC, 2: 0x2064ED8A, 3: 0x2064E9B4}


def _get_write_addr(area, is_sidequest, is_finished):
    """Get the memory address to write dialogue to."""
    if is_sidequest and area in _SIDEQUEST_ADDRS:
        return _SIDEQUEST_ADDRS[area]
    if is_finished and area in _FINISHED_ADDRS:
        return _FINISHED_ADDRS[area]
    return _WRITE_ADDRS.get(area)


# ── Character name replacement in game memory ────────────────

# chr file signature → char byte mapping
_CHR_SIGNATURES = {
    791752805: 251,   # Xiao
    791752819: 252,   # Goro
    791883877: 253,   # Ruby
    792278899: 254,   # Ungaga
    792014949: 255,   # Osmond
}

_DIALOGUE_REGION = 0x20645000
_DIALOGUE_REGION_LEN = 200000


def fix_character_names_in_dialogues(mem):
    """Replace Toan name placeholder (0xFA 0xFA) with current ally's byte.

    Scans 200KB of dialogue memory. Only runs when ally is not Toan.
    """
    sig = mem.read_int(addr.CHR_FILE_LOC + 6)
    char_byte = _CHR_SIGNATURES.get(sig)
    if char_byte is None:
        return  # Toan or unknown — no replacement needed

    data = mem.read_bytes(_DIALOGUE_REGION, _DIALOGUE_REGION_LEN)
    buf = bytearray(data)
    i = 0
    while i < len(buf) - 1:
        if buf[i] == 250 and buf[i + 1] == 250:
            buf[i] = char_byte
            i += 2
        else:
            i += 2
    mem.write_bytes(_DIALOGUE_REGION, bytes(buf))
    log.info("Fixed character names in dialogues (char_byte=%d)", char_byte)


def fix_character_names_in_shop(mem):
    """Same replacement but for shop dialogue region (0x20645000+200000 to +400000)."""
    sig = mem.read_int(addr.CHR_FILE_LOC + 6)
    char_byte = _CHR_SIGNATURES.get(sig)
    if char_byte is None:
        return

    base = _DIALOGUE_REGION + _DIALOGUE_REGION_LEN
    data = mem.read_bytes(base, _DIALOGUE_REGION_LEN)
    buf = bytearray(data)
    i = 0
    while i < len(buf) - 1:
        if buf[i] == 250 and buf[i + 1] == 250:
            buf[i] = char_byte
            i += 2
        else:
            i += 2
    mem.write_bytes(base, bytes(buf))
    log.info("Fixed character names in shop dialogues")


# ── Fishing disabled dialogue ─────────────────────────────────

_FISHING_DISABLE_ADDRS = {
    0: 0x204334F6,
    1: 0x2042F628,
    19: 0x20429AD6,
    3: 0x204305B8,
}

# Fishing NPC disable bytes (write 1 to disable fishing)
_FISHING_NPC_DISABLE = {
    0: 0x2041BF4E,
    1: 0x2041AABA,
    19: 0x2041495E,
    3: 0x20421A8A,
}

# Queens submarine disable
_SUBMARINE_ADDRS = (0x20420B6C, 0x20420B7C)


def set_fishing_disabled_dialogue(mem, area):
    """Write 'Only Toan can fish' dialogue when ally is active."""
    base = _FISHING_DISABLE_ADDRS.get(area)
    if base is None:
        return
    _write_options(mem, base, "Only Ť is able to fish here.")
    log.debug("Set fishing disabled dialogue for area %d", area)


def check_ally_fishing(mem, area, is_using_ally):
    """Disable fishing when using an ally character."""
    if not is_using_ally:
        return
    disable = _FISHING_NPC_DISABLE.get(area)
    if disable is not None:
        mem.write_byte(disable, 1)
        set_fishing_disabled_dialogue(mem, area)
    if area == 19:
        for a in _SUBMARINE_ADDRS:
            mem.write_byte(a, 0)


# ── Fairy King + Intro text ──────────────────────────────────

def fix_fairy_king_dialogue(mem):
    """Write custom Fairy King dialogue about ally summoning."""
    _write_options(mem, 0x20425014,
                   "You can call your allies everywhere^in the world, but however...")


def intro_text_at_norune(mem):
    """Write intro cutscene text at Norune."""
    _write_options(mem, 0x20370A4E,
                   "Wait...\u00a4Have you already done^this before?\u00a4Hmm... well,^whatever the case is...\u00a4Prepare for a great journey,^or should I say...\u00a4A Reforged journey!!")


# ── Collection tracker (Brownboo Pickle) ─────────────────────

# Items that count toward 100% collection
_OBTAINABLE_ITEMS = [
    81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,
    101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,
    117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,
    133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,
    149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,
    165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,
    181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,
    197,198,199,200,201,202,203,204,205,206,207,208,209,210,211,212,
    213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,
    229,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,
    245,246,247,248,249,250,251,252,253,254,255,256,257,
]
_OBTAINABLE_ATTACHMENTS = [81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110]
_OBTAINABLE_ULT_WEAPONS = [258,259,260,261,262,263,264,265,266,267,268,269,270,271,272,273,274,275,276,277,278,279,280]
_OBTAINABLE_SECRET_ITEMS = [234,248]


def check_items_collection(mem):
    """Scan inventory/storage/weapons for collection progress.

    Returns (items_count, total_items, ult_count, ult_total, secret_count, secret_total).
    Used by Brownboo Pickle NPC dialogue.
    """
    checklist = [False] * 380

    # Active item slots
    a = 0x21CDD8AE
    for _ in range(3):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 2

    # Inventory
    a = 0x21CDD8BA
    for _ in range(100):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 2

    # Storage
    a = 0x21CE21E8
    for _ in range(60):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 2

    items = sum(1 for i in _OBTAINABLE_ITEMS if checklist[i])

    # Attachments (bag)
    a = 0x21CE1A48
    for _ in range(40):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 0x20

    # Attachments (storage)
    a = 0x21CE3FE8
    for _ in range(30):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 0x20

    items += sum(1 for i in _OBTAINABLE_ATTACHMENTS if checklist[i])
    total = len(_OBTAINABLE_ITEMS) + len(_OBTAINABLE_ATTACHMENTS)

    # Weapons (bag + storage)
    a = 0x21CDDA58
    for _ in range(65):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 0xF8
    a = 0x21CE22D8
    for _ in range(30):
        iid = mem.read_short(a)
        if 0 < iid < 380:
            checklist[iid] = True
        a += 0xF8

    ult = sum(1 for i in _OBTAINABLE_ULT_WEAPONS if checklist[i])
    secret = sum(1 for i in _OBTAINABLE_SECRET_ITEMS if checklist[i])

    return (items, total, ult, len(_OBTAINABLE_ULT_WEAPONS),
            secret, len(_OBTAINABLE_SECRET_ITEMS))


def check_master_fish_quest_reward(mem):
    """Check if player already has Saving Book (191) in inventory or storage."""
    a = 0x21CDD8BA
    for _ in range(100):
        if mem.read_short(a) == 191:
            return True
        a += 2
    a = 0x21CE21E8
    for _ in range(60):
        if mem.read_short(a) == 191:
            return True
        a += 2
    return False
