"""Ally switching system. Ported from TownCharacter.cs.

Handles character file path writing for overworld ally switching,
NPC proximity detection, building/georama checks, fishing detection,
and area change management.
"""

import logging
import time
from game import addresses as addr

log = logging.getLogger(__name__)

# Character file paths (index = charNumber from ally menu)
CHR_PATHS = {
    0: "chara/c01d.chr",           # Toan
    1: "gedit/e01/chara/c04pcat.chr",  # Xiao
    2: "gedit/s01/chara/c06p.chr",     # Goro
    3: "gedit/e03/chara/c05a.chr",     # Ruby
    4: "gedit/s79/chara/c10a.chr",     # Ungaga
    5: "gedit/e05/chara/c18p.chr",     # Osmond
}

# Addresses
CHR_FILE_LOC = 0x2029AA08
CHR_CONFIG_LOC = 0x2029AA18  # from Addresses.chrConfigFileLocation
CHR_CONFIG_OFFSET = None  # Platform-specific, set at runtime
SELECTED_MENU = 0x202A2010
ALLY_MENU_CHECK = 0x202A28F4
CHAR_NUMBER = 0x21D90470
ALLY_COUNT = 0x21CD9551
AREA_ID = 0x202A2518
AREA_FRAMES = 0x202A2880
LOCATION_CHANGE = 0x202A1E90
BUILDING_CHECK = 0x202A281C
HOUSE_ID = 0x202A2820
DIALOGUE_ID_ADDR = 0x21D1CC0C
FISHING_FLAG = 0x21D19714
NPC_BASE = 0x21D26FF8
NPC_STRIDE = 0x14A0
SHOP_CHECK_1 = 0x21DA52E4
SHOP_CHECK_2 = 0x21DA52E8

# Town dialogue IDs per area (sparse — most are 0)
TOWN_DIALOGUE_IDS = [0] * 256
TOWN_DIALOGUE_IDS[0] = 247   # Norune
TOWN_DIALOGUE_IDS[1] = 167   # Matataki
TOWN_DIALOGUE_IDS[2] = 87    # Queens
TOWN_DIALOGUE_IDS[3] = 27    # Muska Racka
TOWN_DIALOGUE_IDS[14] = 200  # Brownboo
TOWN_DIALOGUE_IDS[23] = 240  # Yellow Drops
TOWN_DIALOGUE_IDS[38] = 101  # Sun & Moon
TOWN_DIALOGUE_IDS[42] = 12   # Dark Heaven

# Xiao camera offsets per area
XIAO_CAMERA = {
    0: (0, 9), 1: (2544, 9), 2: (2306, 9), 3: (2306, 9),
    14: (6, 0), 23: (55, 6), 38: (48, 7), 42: (72, 6),
}

# Areas where event triggers should be disabled for allies
DISABLE_EVENT_AREAS = {11, 13, 33, 35, 37, 14}


def _write_chr_path(mem, path):
    """Write character file path string to game memory."""
    a = CHR_FILE_LOC
    # Clear first
    for i in range(30):
        mem.write_byte(a + i, 0)
    # Write path bytes (ASCII, offset by 32 from character table position)
    for ch in path:
        mem.write_byte(a, ord(ch))
        a += 1


def _check_near_npc(mem):
    """Check 6 NPC proximity slots. Returns list of active slot indices."""
    active = []
    for i in range(6):
        a = i * NPC_STRIDE + NPC_BASE
        if mem.read_byte(a) == 1:
            active.append(i)
    return active


class AllySwitchState:
    """Tracks ally switching state for the town loop."""

    def __init__(self):
        self.chr_path = "chara/c01d.chr"
        self.current_character = "chara/c01d.chr"
        self.prev_char_number = 255
        self.menu_exited = True
        self.is_using_ally = False
        self.near_npc = False
        self.on_dialogue_flag = 0
        self.changing_location = False
        self.current_area = 255
        self.area_changed = False
        self.area_entered_check = False
        self.area_entered_clock = False
        self.building_flag = False
        self.fishing_active = False
        self._fish_boost_time = None
        self._fish_boost_idx = 0
        self.currently_in_shop = False
        self.shop_data_cleared = False
        self.sidequest_option_flag = False
        self._sq_dialogue_active = False
        self._sq_dlg_flag = 0
        self._last_sq_npc_id = 0
        self.dialogue_state = None  # Set externally by TownMod

    def tick(self, mem):
        """Main town tick — call every ~10ms while in town mode."""
        if mem.read_byte(addr.MODE) != 2:
            return

        # Ally menu handling
        if mem.read_byte(SELECTED_MENU) == 3:
            self._handle_ally_menu(mem)
        elif not self.menu_exited and mem.read_byte(LOCATION_CHANGE) == 255:
            # Exited menu without switching — restore current character
            self.chr_path = self.current_character
            _write_chr_path(mem, self.chr_path)
            self.menu_exited = True
            self.prev_char_number = 255

        # Determine if using ally
        if mem.read_int(CHR_FILE_LOC + 6) != 1680945251:  # Not Toan's "c01d.ch"
            self.is_using_ally = True
        else:
            self.is_using_ally = False

        # Area management
        area = mem.read_byte(AREA_ID)
        if area != self.current_area:
            self.current_area = area

        # Event trigger disable for allies
        if self.is_using_ally:
            if area in DISABLE_EVENT_AREAS:
                mem.write_byte(0x21F10000, 1)
            else:
                mem.write_byte(0x21F10000, 0)

            # NPC proximity check
            self._check_npc_proximity(mem)

            # Xiao camera
            if mem.read_int(CHR_CONFIG_LOC) == 1882468451:  # Xiao
                cam = XIAO_CAMERA.get(area)
                if cam:
                    mem.write_short(0x202A2A6C, cam[0])
                    mem.write_byte(0x202A2A6E, cam[1])
                mem.write_byte(0x21F1000C, 1)
            else:
                mem.write_byte(0x21F1000C, 0)

            # Building/georama check
            self._check_building(mem, area)
        else:
            mem.write_byte(0x21F10000, 0)
            mem.write_byte(0x21F1000C, 0)

        # Area change detection
        frames = mem.read_int(AREA_FRAMES)
        if frames < 50 and frames > 30 and not self.area_entered_check:
            self.area_changed = True
            self.area_entered_check = True
        elif frames >= 50:
            self.area_changed = False
            self.area_entered_check = False

        # Building enter/exit → set dialogue options + storage dialogue (C# TownCharacter)
        from mods.dialogues import set_dialogue_options
        building_val = mem.read_byte(BUILDING_CHECK)
        if (building_val == 0 and self.building_flag) or self.area_changed:
            set_dialogue_options(mem, self.current_area, False)
            if hasattr(self, 'dialogue_state') and self.dialogue_state:
                self.dialogue_state.storage_save(mem, self.current_area)
            self.building_flag = False
            self.area_changed = False
        elif building_val == 1 and not self.building_flag:
            if self.current_area != 23:
                set_dialogue_options(mem, self.current_area, True)
                if hasattr(self, 'dialogue_state') and self.dialogue_state:
                    self.dialogue_state.storage_restore(mem, self.current_area)
                self.building_flag = True
            else:
                npc_type = mem.read_byte(0x21D26FD4)
                if npc_type in (0, 1):
                    set_dialogue_options(mem, self.current_area, True)
                    if hasattr(self, 'dialogue_state') and self.dialogue_state:
                        self.dialogue_state.storage_restore(mem, self.current_area)
                    self.building_flag = True

        # Toan path — NPC proximity for PNACH dialogue ID switching
        if not self.is_using_ally:
            active = _check_near_npc(mem)
            if active:
                if not self.near_npc:
                    self.near_npc = True
                mem.write_byte(0x21F10008, 1)
            else:
                if self.near_npc:
                    self.near_npc = False
                mem.write_byte(0x21F10008, 0)

        # Location change — swap back to Toan
        # Toan sidequest detection (areas 0-3)
        if not self.is_using_ally:
            area = self.current_area
            _SQ_DLG_IDS = {0: 107, 1: 107, 2: 127, 3: 147}
            sq_id = _SQ_DLG_IDS.get(area, 0)
            if area in (0, 1, 2, 3):
                cur_dlg = mem.read_byte(DIALOGUE_ID_ADDR)
                sq_trigger = 15 if area == 2 else 11
                if not self.sidequest_option_flag and cur_dlg == sq_trigger:
                    self.sidequest_option_flag = True
                elif self.sidequest_option_flag and cur_dlg == 255:
                    self.sidequest_option_flag = False
                    self._sq_dialogue_active = False
                    self._sq_dlg_flag = 0
                if self.sidequest_option_flag and sq_id:
                    mem.write_int(0x21D3D440, sq_id)
                    self._set_sidequest_dialogue(mem)
                    cur_dlg_s = mem.read_short(DIALOGUE_ID_ADDR)
                    if cur_dlg_s == sq_id and not self._sq_dialogue_active:
                        self._check_sidequest_dialogue(mem)
                        self._sq_dialogue_active = True
                    elif cur_dlg_s != sq_id:
                        self._sq_dialogue_active = False
                elif not self.sidequest_option_flag:
                    self._sq_dlg_flag = 0

        # Location change — swap back to Toan
        if (mem.read_byte(LOCATION_CHANGE) != 255 and
                mem.read_short(LOCATION_CHANGE) != 1000 and
                not self.changing_location):
            self.changing_location = True
            self.chr_path = "chara/c01d.chr"
            mem.write_byte(0x21F10000, 0)
            _write_chr_path(mem, self.chr_path)
        if mem.read_byte(LOCATION_CHANGE) == 255:
            self.changing_location = False

        # Fishing detection
        fishing = mem.read_byte(FISHING_FLAG) == 1
        if fishing:
            if not self.fishing_active:
                self.fishing_active = True
                self._fish_boost_time = None
                log.info("Fishing mode entered")
            try:
                from mods.fishing import get_pond_status, progressive_attract
                from ui.overlay import show_text
                text = get_pond_status(mem, self.current_area)
                if text:
                    show_text(text)
                self._fish_boost_time, self._fish_boost_idx = progressive_attract(
                    mem, self.current_area, self._fish_boost_time, self._fish_boost_idx)
            except Exception:
                pass
        elif self.fishing_active:
            self.fishing_active = False
            self._fish_boost_time = None
            self._fish_boost_idx = 0
            try:
                from ui.overlay import hide_text
                hide_text()
            except Exception:
                pass

        # Shop detection
        if not self.currently_in_shop:
            if mem.read_byte(SHOP_CHECK_1) == 1 and mem.read_byte(SHOP_CHECK_2) == 11:
                self.currently_in_shop = True
                self.shop_data_cleared = False
                log.info("Entered shop")
        if self.currently_in_shop and mem.read_byte(SHOP_CHECK_1) != 1:
            self.currently_in_shop = False
            log.info("Exited shop")

    def _handle_ally_menu(self, mem):
        """Handle ally selection menu cycling."""
        if mem.read_int(ALLY_MENU_CHECK) == 0:
            self.current_character = self.chr_path

        char_num = mem.read_byte(CHAR_NUMBER)
        if char_num != self.prev_char_number:
            path = CHR_PATHS.get(char_num, "chara/c01d.chr")
            self.chr_path = path
            _write_chr_path(mem, path)
            self.prev_char_number = char_num
            self.menu_exited = False

    def _check_npc_proximity(self, mem):
        """Check if player is near an NPC and trigger dialogue."""
        active = _check_near_npc(mem)
        if active:
            if not self.near_npc or self.on_dialogue_flag == 1:
                # Write dialogue for the first active NPC slot
                if self.dialogue_state:
                    self.dialogue_state.set_dialogue(
                        mem, active[0], self.is_using_ally, False)
                mem.write_byte(0x21F10008, 1)
                self.near_npc = True
                if self.on_dialogue_flag == 1:
                    self.on_dialogue_flag = 2
        else:
            self.near_npc = False
            mem.write_byte(0x21F10008, 0)
            self.on_dialogue_flag = 0

        # Dialogue flag tracking
        area = self.current_area
        if area < len(TOWN_DIALOGUE_IDS):
            dlg_id = TOWN_DIALOGUE_IDS[area]
            if dlg_id > 0:
                cur_dlg = mem.read_byte(DIALOGUE_ID_ADDR)
                if cur_dlg == dlg_id and self.on_dialogue_flag == 0:
                    self.on_dialogue_flag = 1
                    if self.dialogue_state:
                        self.dialogue_state.change_dialogue()
                elif cur_dlg == dlg_id and self.on_dialogue_flag == 3:
                    self.on_dialogue_flag = 0
                if self.on_dialogue_flag == 2 and cur_dlg == 255:
                    self.on_dialogue_flag = 3

                # Sidequest option detection — ally path (shopkeeper NPCs)
                _SQ_DLG_IDS = {0: 107, 1: 107, 2: 127, 3: 147}
                sq_id = _SQ_DLG_IDS.get(area, 0)
                if not self.sidequest_option_flag and cur_dlg == 12:
                    self.sidequest_option_flag = True
                elif self.sidequest_option_flag and cur_dlg == 255:
                    self.sidequest_option_flag = False
                    self._sq_dialogue_active = False
                    self._sq_dlg_flag = 0

                if self.sidequest_option_flag and sq_id:
                    mem.write_int(0x21D3D43C, sq_id)
                    self._set_sidequest_dialogue(mem)
                    cur_dlg_s = mem.read_short(DIALOGUE_ID_ADDR)
                    if cur_dlg_s == sq_id and not self._sq_dialogue_active:
                        self._check_sidequest_dialogue(mem)
                        self._sq_dialogue_active = True
                    elif cur_dlg_s != sq_id:
                        self._sq_dialogue_active = False
                elif not self.sidequest_option_flag:
                    self._sq_dlg_flag = 0

    def _set_sidequest_dialogue(self, mem):
        """Re-scan NPC proximity and write sidequest dialogue. Matches C# SetSideQuestDialogue."""
        active = _check_near_npc(mem)
        for slot in active:
            if self._sq_dlg_flag == 0 and self.dialogue_state:
                self.dialogue_state.set_dialogue(mem, slot, False, True)
                mem.write_byte(0x21F10010, 1)
                self._sq_dlg_flag = 1
                # Store NPC ID for CheckSideQuestDialogue
                npc_addr = slot * NPC_STRIDE + 0x21D26FD9
                self._last_sq_npc_id = mem.read_short(npc_addr)
                log.debug("Sidequest dialogue set for NPC %d", self._last_sq_npc_id)

    def _check_sidequest_dialogue(self, mem):
        """Handle quest state when player views sidequest dialogue. Matches C# CheckSideQuestDialogue."""
        self.sidequest_option_flag = False
        npc_id = self._last_sq_npc_id
        if not npc_id:
            return
        from mods.sidequests import QUEST_ADDRS, FISH_QUEST_ADDRS, _FISH_NPC_CONFIG

        # Monster quest NPCs
        if npc_id in QUEST_ADDRS:
            unlock_addrs = {12592: 0x21CE4474, 13618: 0x21CE4476,
                            13108: 0x21CE4478, 14388: 0x21CE447A}
            progress_addrs = {12592: 0x21CE4402, 13618: 0x21CE4407,
                              13108: 0x21CE440C, 14388: 0x21CE4411}
            unlock = unlock_addrs.get(npc_id)
            progress = progress_addrs.get(npc_id)
            if unlock and progress:
                if mem.read_byte(unlock) == 1:
                    p = mem.read_byte(progress)
                    if p == 0:
                        mem.write_byte(progress, 1)
                    elif p == 2:
                        from mods.sidequests import monster_quest_reward
                        monster_quest_reward(mem)
                        mem.write_byte(progress, 0)
                else:
                    mem.write_byte(unlock, 1)
            log.debug("CheckSideQuestDialogue: monster NPC %d", npc_id)

        # Fishing quest NPCs
        elif npc_id in FISH_QUEST_ADDRS:
            cfg = _FISH_NPC_CONFIG.get(npc_id)
            if cfg:
                if mem.read_byte(cfg['unlock']) == 1:
                    p = mem.read_byte(cfg['progress'])
                    if p == 0:
                        mem.write_byte(cfg['progress'], 1)
                    elif p == 2:
                        mem.write_byte(cfg['progress'], 0)
                else:
                    mem.write_byte(cfg['unlock'], 1)
            log.debug("CheckSideQuestDialogue: fishing NPC %d", npc_id)

    def _check_building(self, mem, area):
        """Check georama building completion for ally entry."""
        house_id = mem.read_byte(HOUSE_ID)
        if house_id != 255:
            completion_addr = 0xE8 * house_id + 0x21D19C58
            if mem.read_byte(completion_addr) == 0:
                parts = 4
                check_addr = 0xE8 * house_id + 0x21D19C80
                # Special 5-part houses
                if area == 0 and house_id == 4:
                    parts = 5
                elif area == 1 and house_id == 1:
                    parts = 5
                collected = sum(mem.read_byte(check_addr + i * 0x20) for i in range(parts))
                mem.write_byte(0x202A282C, 0 if collected == parts else 128)
            else:
                mem.write_byte(0x202A282C, 128)
        else:
            mem.write_byte(0x202A282C, 128)


# ── Utility functions ported from TownCharacter.cs ─────────────

def fix_broken_dagger(mem):
    """Clear shop data region to fix broken dagger glitch."""
    a = 0x21839528
    for i in range(18000):
        mem.write_byte(a + i, 0)
    log.info("Broken dagger fix finished")


def check_clock_advancement(mem, area):
    """Enable clock for areas that don't normally have one."""
    if area in (23, 40, 38):
        clock = mem.read_float(0x21CD4310)
        mem.write_byte(0x21F1001C, 1)
        time.sleep(0.01)
        mem.write_byte(0x203A3920, 0)
        mem.write_float(0x202A28F4, clock)
        log.info("Enabled clock for area %d", area)


def check_mardan_sword(mem):
    """Check if player has a Mardan fishing rod equipped."""
    from data.player import Toan
    slot = mem.read_byte(Toan.currentWeaponSlot)
    wep_id = mem.read_short(0x21CDDA58 + slot * 0xF8)
    if wep_id == 278:
        return True, 2  # Mardan Eins
    elif wep_id == 279:
        return True, 3  # Mardan Twei
    elif wep_id == 280:
        return True, 5  # Arise Mardan
    return False, 1


def demon_shaft_unlock_check(mem, unlocked_flag):
    """Prevent Demon Shaft access before game completion."""
    if unlocked_flag:
        return True
    if mem.read_byte(0x21CE448B) == 1:
        return True
    if mem.read_byte(SELECTED_MENU) == 13:  # World map open
        if mem.read_byte(0x21CE448B) == 0:
            mem.write_byte(0x21CE70A0, 0)
    return False


def check_credits_scene(mem, player_at_credits):
    """Detect credits scene, set game-cleared flag, fix save menu.

    Returns updated player_at_credits flag.
    """
    area = mem.read_int(0x202A2518)
    if area == -1 and not player_at_credits:
        # Entered credits
        mem.write_byte(0x21CE448B, 1)  # game cleared flag
        if mem.read_byte(0x21CE70A0) == 0:
            mem.write_byte(0x21CE70A0, 1)  # demon shaft visit count
        log.info("Game beaten, entered credits!")
        return True
    elif area != 51 and player_at_credits:
        mem.write_int(0x202A2518, 60)
        if mem.read_byte(0x21DA8AD0) == 2 and mem.read_byte(0x21DA8AE3) < 255:
            mem.write_byte(0x21DA8AD0, 1)  # fix save menu
            return False
    return player_at_credits
