"""Town character system. Ported from TownCharacter.cs.

Handles:
- One-time item/shop QoL patches on entering town
- Daily shop rotation (DailyShopItem)
- Area change detection
- Character change detection
- Clock/day tracking
- Element swapping (DPad Up/Down to cycle weapon element)
- Side quest state management
"""

import logging
import time
from mods.base import ModBase
from game import addresses as addr
from data.player import weapon_slot_addr, CHARACTERS

log = logging.getLogger(__name__)

# One-time QoL memory patches applied when entering town
# (address, value, write_type) — from TownCharacter.MainScript()
TOWN_PATCHES = [
    (0x2027DD50, 0, 'byte'),   # shell ring discardable
    (0x2027DD28, 0, 'byte'),   # magical lamp discardable
    (0x2027DC80, 8, 'byte'),   # map ordering
    (0x2027DC94, 8, 'byte'),   # magical crystal ordering
    (0x20291CEE, 1, 'byte'),   # hardening powder cost 1g
    (0x2027D808, 0, 'byte'),   # escape powder equippable+stackable
    (0x2027D7F8, 2, 'byte'),   # escape powder arrow to active slots
    (0x2027D81C, 0, 'byte'),   # revival powder stackable
    (0x2027D830, 0, 'byte'),   # repair powder equippable+stackable
    (0x2027D8A8, 0, 'byte'),   # auto-repair powder stackable
    (0x20292A3E, 2000, 'short'),  # matador fishing cost 2k
    (0x21CB6AEC, 50, 'byte'),  # fix matador model
    (0x21CB6AF7, 50, 'byte'),
    (0x21CB6B02, 51, 'byte'),
    (0x21CB6B0D, 51, 'byte'),
]

# Mayor quest max HP patches
MAYOR_HP_PATCHES = [
    0x20293978, 0x2029397A, 0x2029397C,
    0x2029397E, 0x20293980, 0x20293982,
]

# Element RGB data for element swapping HUD
ELEM_RGBS = {
    0: [63,15,0,63,6,1,0,63,63,15,0,31,6,1,0,31],     # Fire
    1: [25,50,63,63,2,5,6,63,25,50,63,31,2,5,6,31],    # Ice
    2: [63,63,25,63,6,6,2,63,63,63,25,31,6,6,2,31],    # Thunder
    3: [34,63,47,63,3,6,4,63,34,63,47,31,3,6,4,31],    # Wind
    4: [56,37,43,63,5,3,4,63,56,37,43,31,5,3,4,31],    # Holy
    5: [64,64,64,63,6,6,6,63,64,64,64,31,6,6,6,31],    # None
}

ELEM_NAMES = ['Fire', 'Ice', 'Thunder', 'Wind', 'Holy', 'None']

# Daily shop addresses
DAILY_SHOPS = [
    addr.DAILY_GAFFER, addr.DAILY_WISE_OWL, addr.DAILY_JACK,
    addr.DAILY_JOKER, addr.DAILY_BROOKE, addr.DAILY_LEDAN, addr.DAILY_FAIRY_KING,
]


class TownMod(ModBase):
    name = "Town"

    def __init__(self, mem):
        super().__init__(mem)
        self.prev_char = 255
        self.prev_area = -1
        self.patches_applied = False
        self.current_day = 0
        self.elem_switching = False
        self.ally = None
        self.fishing_state = None
        self.dialogue_state = None

    def run(self):
        log.info("Town thread activated")
        while self._running:
            try:
                mode = self.mem.read_byte(addr.MODE)
            except Exception:
                time.sleep(0.5)
                continue

            if mode != addr.Mode.TOWN:
                # Credits scene check
                if mode == 13:
                    try:
                        from mods.allyswitch import check_credits_scene
                        self._at_credits = check_credits_scene(
                            self.mem, getattr(self, '_at_credits', False))
                    except Exception:
                        pass
                # Exit check
                if mode in (0, 1):
                    time.sleep(0.1)
                    try:
                        if self.mem.read_byte(addr.MODE) in (0, 1):
                            log.info("Not in-game, exiting town thread")
                            self._running = False
                    except Exception:
                        pass
                time.sleep(0.1)
                continue

            # One-time patches
            if not self.patches_applied:
                self._apply_patches()
                from mods.allyswitch import AllySwitchState
                from mods.fishing import FishingState
                from mods.dialogues import DialogueState
                self.ally = AllySwitchState()
                self.fishing_state = FishingState()
                self.dialogue_state = DialogueState()
                self.ally.dialogue_state = self.dialogue_state

            try:
                char_id = self.mem.read_byte(addr.CURRENT_CHARACTER)
                area_id = self.mem.read_byte(addr.TOWN_AREA)
            except Exception:
                time.sleep(0.01)
                continue

            # Area change
            if area_id != self.prev_area:
                log.info("Entered area: %s", addr.TOWN_NAMES.get(area_id, f"Area {area_id}"))
                self.prev_area = area_id
                self._on_area_change(area_id)

            # Character change
            if char_id != self.prev_char:
                log.info("Character: %s", addr.CHARACTER_NAMES.get(char_id, "Unknown"))
                self.prev_char = char_id

            # Day change → refresh daily shops
            try:
                day = self.mem.read_short(0x21CD4318)
                if day != self.current_day:
                    self.current_day = day
                    self._set_daily_shops()
                    log.info("Day changed to %d, refreshed shops", day)
            except Exception:
                pass

            # L3: show georama request status
            try:
                btn = self.mem.read_short(addr.BUTTON_INPUTS)
                l3_now = bool(btn & 0x0200)
                if l3_now and not getattr(self, '_l3_held', False):
                    self._show_georama_requests()
                self._l3_held = l3_now
            except Exception as e:
                log.info("L3 check error: %s", e)

            # Ally switching tick
            if self.ally:
                try:
                    self.ally.tick(self.mem)
                except Exception:
                    pass

                # Broken dagger fix on shop enter
                if self.ally.currently_in_shop and not self.ally.shop_data_cleared:
                    from mods.allyswitch import fix_broken_dagger
                    fix_broken_dagger(self.mem)
                    self.ally.shop_data_cleared = True

            # Landing animation cancel (prevent stuck ally)
            try:
                if self.mem.read_byte(0x21D33E28) == 9:
                    if not getattr(self, '_fishing_active_cache', False):
                        self.mem.write_byte(0x21D33E30, 3)
                self._fishing_active_cache = self.ally.fishing_active if self.ally else False
            except Exception:
                pass

            # Yaya enable
            try:
                if self.mem.read_byte(0x21CDD80D) != 255:
                    self.mem.write_byte(0x21F10004, 1)
            except Exception:
                pass

            # Mayor door event disable
            try:
                if self.mem.read_byte(0x21F10014) == 1:
                    self.mem.write_byte(0x20415508, 0)
                    self.mem.write_byte(0x20415538, 0)
            except Exception:
                pass

            # Demon shaft unlock check
            try:
                from mods.allyswitch import demon_shaft_unlock_check
                demon_shaft_unlock_check(self.mem, getattr(self, '_ds_unlocked', False))
            except Exception:
                pass

            # Weapon level-up check (also runs in town for synth menu)
            # Handled by dungeon mod's _check_wep_lvl_up via weapons mod

            # Fishing tick
            if self.ally and self.ally.fishing_active and self.fishing_state:
                try:
                    if not self.fishing_state.initialized:
                        from mods.allyswitch import check_mardan_sword
                        has_m, mult = check_mardan_sword(self.mem)
                        self.fishing_state.init_area(self.mem, area_id, has_m, mult)
                    else:
                        self.fishing_state.tick(self.mem)
                except Exception:
                    pass
            elif self.fishing_state and self.fishing_state.initialized:
                self.fishing_state.initialized = False

            time.sleep(0.05)  # 50ms — matches C# TownCharacter.MainScript

    def _apply_patches(self):
        """One-time QoL patches from TownCharacter.MainScript()."""
        log.info("Applying town QoL patches...")
        for a, v, t in TOWN_PATCHES:
            try:
                if t == 'byte':
                    self.mem.write_byte(a, v)
                elif t == 'short':
                    self.mem.write_short(a, v)
            except Exception:
                pass

        # Mayor quest max HP patches
        try:
            if self.mem.read_byte(addr.MAYOR_QUEST_FLAG) != 0:
                for a in MAYOR_HP_PATCHES:
                    self.mem.write_byte(a, 250)
        except Exception:
            pass

        # Restore SoZ max attack from saved thunder value
        try:
            stored_thunder = self.mem.read_short(0x21CE446D)
            if stored_thunder > 0:
                self._update_soz_max_attack(stored_thunder)
        except Exception:
            pass

        # Initialize character file offset for ally switching
        self._init_chr_offsets()

        self.current_day = 0
        try:
            self.current_day = self.mem.read_short(0x21CD4318)
        except Exception:
            pass

        self._set_daily_shops()
        self.patches_applied = True
        self._applied = True
        log.info("Town patches applied")

        # One-time base shop changes
        from mods.dailyshop import base_shop_changes
        base_shop_changes(self.mem)

    def _init_chr_offsets(self):
        """Patch game code to redirect character file loading (C# InitializeCharacterOffsetValues).
        Writes new offset value so the game reads chr paths from our memory location."""
        # Patch the code offset to point to our config file location
        self.mem.write_int(addr.CHR_CONFIG_OFFSET, 608545264)

        # Clear config file location (15 bytes)
        for i in range(15):
            self.mem.write_byte(addr.CHR_CONFIG_FILE_LOC + i, 0)
        # Clear chr file secondary area (9 bytes at 0x2029AA18)
        for i in range(9):
            self.mem.write_byte(0x2029AA18 + i, 0)

        # Write "info.cfg" to config file location
        for i, ch in enumerate("info.cfg"):
            self.mem.write_byte(addr.CHR_CONFIG_FILE_LOC + i, ord(ch))

        # Write default chr path "chara/c01d.chr" to file location
        for i, ch in enumerate("chara/c01d.chr"):
            self.mem.write_byte(addr.CHR_FILE_LOC + i, ord(ch))

        log.info("Character file offsets initialized")

    def _set_daily_shops(self):
        """Set daily shop rotation items. Ported from DailyShopItem."""
        from mods.dailyshop import reroll_daily_rotation, set_daily_items_to_shop
        reroll_daily_rotation(self.mem, self.current_day)

    def _on_area_change(self, area_id):
        """Called when player enters a new town area."""
        if self.dialogue_state:
            self.dialogue_state.on_area_change(self.mem, area_id)
        if self.ally and self.ally.is_using_ally:
            from mods.dialogues import check_ally_fishing, fix_character_names_in_dialogues
            check_ally_fishing(self.mem, area_id, True)
            fix_character_names_in_dialogues(self.mem)
        from mods.allyswitch import check_clock_advancement
        check_clock_advancement(self.mem, area_id)

    def _update_soz_max_attack(self, stored_thunder):
        """Scale Sword of Zeus max attack based on stored thunder."""
        if stored_thunder > 2000:
            max_atk = 599 + (stored_thunder - 2000) // 20
        elif stored_thunder > 1000:
            max_atk = 499 + (stored_thunder - 1000) // 10
        elif stored_thunder > 500:
            max_atk = 399 + (stored_thunder - 500) // 5
        elif stored_thunder > 200:
            max_atk = 299 + (stored_thunder - 200) // 3
        else:
            max_atk = 199 + stored_thunder // 2
        try:
            self.mem.write_short(0x2027B298, max_atk)
        except Exception:
            pass

    # DC text encoding: ASCII -> DC glyph bytes
    _DC_CHAR_MAP = {
        **{chr(c): b for c, b in zip(range(0x41, 0x5B), range(0x21, 0x3B))},  # A-Z
        **{chr(c): b for c, b in zip(range(0x61, 0x7B), range(0x3B, 0x55))},  # a-z
        **{chr(c): b for c, b in zip(range(0x30, 0x3A), range(0x6F, 0x79))},  # 0-9
        "'": 0x55, '=': 0x56, '"': 0x57, '!': 0x58, '?': 0x59, '#': 0x5A,
        '&': 0x5B, '+': 0x5C, '-': 0x5D, '*': 0x5E, '(': 0x61, ')': 0x62,
        '@': 0x63, '<': 0x65, '>': 0x66, '.': 0x6D, '$': 0x6E,
        '[': 0x69, ']': 0x6A,
        ':': 0x6B, ',': 0x6C, '/': 0x5F, ';': 0x60,  # likely glyph slots
    }

    _DC_COLORS = {
        'W': 0x01, 'Y': 0x02, 'B': 0x03, 'G': 0x04, 'O': 0x06, 'R': 0xFF,
    }

    def _dc_encode(self, text):
        """Encode ASCII string to DC message bytes. Supports ^R ^G ^W etc for colors."""
        out = bytearray()
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '^' and i + 1 < len(text) and text[i + 1] in self._DC_COLORS:
                out += bytes([self._DC_COLORS[text[i + 1]], 0xFC])
                i += 2
            elif ch == ' ':
                out += b'\x02\xFF'
                i += 1
            elif ch == '\n':
                out += b'\x00\xFF'
                i += 1
            elif ch in self._DC_CHAR_MAP:
                out += bytes([self._DC_CHAR_MAP[ch], 0xFD])
                i += 1
            else:
                i += 1  # skip unknown
        out += b'\x01\xFF'
        return bytes(out)

    def _show_georama_requests(self):
        """Display georama request info via overlay."""
        from data.georama import AREAS, AREA_NAMES
        from ui.overlay import show_text
        area = self.mem.read_byte(addr.TOWN_AREA)
        if area < 0 or area >= len(AREAS):
            return
        houses = AREAS[area]
        # CommonMenuAtoraInfo: first int = house count, then per-house satisfaction flags
        atora_ptr = self.mem.read_int(0x202A2ECC)
        atora = 0x20000000 + (atora_ptr & 0x1FFFFFF) if atora_ptr else 0
        # Read all 24 satisfaction flags
        flags = []
        if atora:
            for j in range(24):
                flags.append(self.mem.read_int(atora + 4 + j * 4))
        lines = ["^Y" + AREA_NAMES[area]]
        for name, requests, fidx in houses:
            done = bool(flags[fidx]) if fidx < len(flags) else False
            color = "^G" if done else "^R"
            for req in requests:
                lines.append(color + name + ": ^W" + req)
        if not any(bool(flags[fidx]) for _, _, fidx in houses if fidx < len(flags)):
            lines.append('^sYou must open "Georama Analysis" at least once per session.')
        show_text("\n".join(lines))

    def _display_town_message(self, text, duration=300):
        """Write text to Edit buffer and trigger display via PNACH cave."""
        ebase = 0x21D22C10
        buf_ptr = self.mem.read_int(ebase + 0x17A0)
        if buf_ptr == 0:
            return
        buf = 0x20000000 + (buf_ptr & 0x1FFFFFF)
        count = self.mem.read_short(buf)
        idx_off = self.mem.read_short(buf + 6)
        text_addr = buf + 2 + count * 2 + idx_off * 2
        msg = self._dc_encode(text)
        for i, b in enumerate(msg):
            self.mem.write_byte(text_addr + i, b)
        # Position: set EditSystemMes struct X/Y directly
        ebase = 0x21D22C10
        self.mem.write_int(ebase + 0x00, 20)   # X position
        self.mem.write_int(ebase + 0x04, 20)   # Y position
        self.mem.write_int(0x21F10044, 1)
        self.mem.write_int(0x21F10040, 1)
        self.mem.write_int(0x202A1F4C, 1)
        self.mem.write_int(0x202A278C, duration)


class ElementSwapMod(ModBase):
    """DPad Up/Down element swapping in dungeon. Ported from Dayuppy.ElementSwapping()."""
    name = "Element Swap"

    def __init__(self, mem):
        super().__init__(mem)
        self.switching = False

    def run(self):
        log.info("Element swap thread started")
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(0.001)

    def _tick(self):
        mode = self.mem.read_byte(addr.MODE)
        if mode in (0, 1):
            time.sleep(0.1)
            if self.mem.read_byte(addr.MODE) in (0, 1):
                self._running = False
                return

        anim = self.mem.read_byte(0x21DC4484)
        # Valid animations for element swap
        valid = anim in (0, 1, 2, 8, 9, 10, 18, 19, 20, 21, 22, 33)
        if not valid:
            self.switching = False
            return

        btn = self.mem.read_short(addr.BUTTON_INPUTS)
        dpad_up = btn in (0x1000, 0x1000 | 0x0008)    # DPad_Up or DPad_Up+R1
        dpad_down = btn in (0x4000, 0x4000 | 0x0008)  # DPad_Down or DPad_Down+R1

        if not (dpad_up or dpad_down):
            self.switching = False
            return

        if self.switching:
            return

        if self.mem.read_byte(addr.DUNGEON_FLOOR_CHECK) == 255:
            return

        dbg = self.mem.read_int(addr.DUNGEON_DEBUG_MENU)
        if dbg not in (0, 10):
            return

        char_idx = self.mem.read_byte(addr.CURRENT_CHARACTER)
        slot = self.mem.read_byte(0x21CDD88C + char_idx)
        elem_addr = weapon_slot_addr(char_idx, slot, 'elementHUD')
        cur_elem = self.mem.read_byte(elem_addr)

        # Ruby (3) and Osmond with special flag (5) skip "None" element
        skip_none = (char_idx == 3 or
                     (char_idx == 5 and self.mem.read_byte(0x21DC4520) != 0))

        # Cycle element
        new_elem = cur_elem
        for _ in range(6):
            if dpad_up:
                new_elem = (new_elem - 1) if new_elem > 0 else (4 if skip_none else 5)
            else:
                if new_elem >= (4 if skip_none else 5):
                    new_elem = 0
                else:
                    new_elem += 1

            if new_elem == 5:
                break  # "None" is always valid
            if new_elem > 5:
                break

            # Check if element has any points
            elem_amount = self.mem.read_byte(0x21EA75A7 + new_elem)
            if elem_amount > 0:
                break
        else:
            return

        if 0 <= new_elem <= 5:
            self.mem.write_byte(elem_addr, new_elem)
            self.mem.write_byte(0x21EA75A6, new_elem)

            # Write RGB data
            rgb = ELEM_RGBS.get(new_elem, ELEM_RGBS[5])
            for i, v in enumerate(rgb):
                self.mem.write_byte(0x21E59450 + i, v)

            # Ruby texture swap
            if char_idx == 3 and new_elem <= 4:
                from mods.ruby_tex import check_elements
                check_elements(self.mem, new_elem)

            self.switching = True
            log.info("Element changed to %s", ELEM_NAMES[new_elem])

            from game.display import display_message
            name = ELEM_NAMES[new_elem]
            msg = f"Changed current attribute to {name}"
            display_message(self.mem, msg, height=1, width=len(msg) + 2, display_time=1000)
            time.sleep(1.1)  # Debounce
