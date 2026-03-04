"""Cheat code input buffer monitor. Ported from CheatCodes.cs.

Monitors button inputs during dungeon pause and checks for cheat code sequences.
"""

import logging
import time
from mods.base import ModBase
from game import addresses as addr
from data.cheatcodes import *
from data.player import Toan

log = logging.getLogger(__name__)

# Button flags (PS2 controller)
BTN_CIRCLE = 0x0020
BTN_SQUARE = 0x0080
BTN_SELECT = 0x0100
BTN_START = 0x0800
BTN_L1 = 0x0004
BTN_L2 = 0x0001
BTN_R1 = 0x0008
BTN_R2 = 0x0002
BTN_L3 = 0x0200
BTN_R3 = 0x0400

# Soft reset combo: L1+L2+R1+R2+Select+Start
SOFT_RESET = BTN_L1 | BTN_L2 | BTN_R1 | BTN_R2 | BTN_SELECT | BTN_START

# Broken dagger attachment values
BD_VALUES = [90, 0, 1, 0, 226, 54, 0, 0, 0, 3, 0, 3, 0, 3, 0, 3,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99]

# Floor unlock addresses per dungeon
FLOOR_UNLOCK = {
    0: (0x21CDD80B, 14), 1: (0x21CDD80C, 16), 2: (0x21CDD80D, 17),
    3: (0x21CDD80E, 17), 4: (0x21CDD80F, 14), 5: (0x21CDD810, 24),
    6: (0x21CDD811, 99),
}


class CheatCodesMod(ModBase):
    """Input buffer monitor for cheat codes during dungeon pause."""
    name = "Cheat Codes"

    def __init__(self, mem):
        super().__init__(mem)
        self.inputs = []
        self.prev_input = 0
        self.debug_part1 = False

    def run(self):
        log.info("Cheat code monitor started")
        while self._running:
            time.sleep(0.05)
            try:
                self._tick()
            except Exception as e:
                log.debug("Cheat tick error: %s", e)

    def _tick(self):
        # Check soft reset combo
        btn = self.mem.read_short(addr.BUTTON_INPUTS)
        if btn == SOFT_RESET:
            time.sleep(2)
            if self.mem.read_short(addr.BUTTON_INPUTS) == SOFT_RESET:
                try:
                    if self.mem.read_byte(addr.DUNGEON_FLOOR_CHECK) != 255:
                        self.mem.write_int(addr.DUNGEON_DEBUG_MENU, 151)
                    else:
                        self.mem.write_byte(addr.TOWN_SOFT_RESET, 1)
                except Exception:
                    pass
                return

        # Only process cheat inputs when paused in dungeon
        if not self._is_paused():
            return

        if btn != 0 and btn != self.prev_input:
            self._add(btn)
            self.prev_input = btn

        if not self.prev_input and btn == 0:
            return
        if btn == 0:
            self.prev_input = 0

        # Check sequences
        if self._check(cheatGodmode):
            self._toggle_godmode()
            self.mem.write_byte(addr.CHEATS_USED_FLAG, 1)

        if self._check(cheatBrokenDagger):
            log.info("Cheat: Broken Dagger")
            self.mem.write_byte(addr.CHEATS_USED_FLAG, 1)

        if self._check(cheatPowerupPowders):
            log.info("Cheat: Powerup Powders")
            self.mem.write_byte(addr.CHEATS_USED_FLAG, 1)

        if self._check(cheatMaxMoney):
            self.mem.write_short(addr.GILDA, 65535)
            log.info("Cheat: Max Gilda")
            self.mem.write_byte(addr.CHEATS_USED_FLAG, 1)

        if self._check(cheatDebugMenusPart1):
            if not self.debug_part1:
                self.debug_part1 = True
                log.info("Cheat: Debug Part 1")

        if self._check(cheatDebugMenusPart2):
            if self.debug_part1:
                log.info("Cheat: Debug Menus Unlocked")
                self.mem.write_byte(addr.CHEATS_USED_FLAG, 1)

        if self._check(cheatUnlockFloors):
            dng = self.mem.read_byte(addr.DUNGEON_ID)
            if dng in FLOOR_UNLOCK:
                a, v = FLOOR_UNLOCK[dng]
                self.mem.write_byte(a, v)
                log.info("Cheat: Unlocked floors for dungeon %d", dng)
            self.mem.write_byte(addr.CHEATS_USED_FLAG, 1)

    def _is_paused(self):
        try:
            return (self.mem.read_short(addr.DUN_PAUSE_PLAYER) == 1 and
                    self.mem.read_short(addr.DUN_PAUSE_ENEMY) == 1 and
                    self.mem.read_short(addr.DUN_PAUSE_TITLE) == 1)
        except Exception:
            return False

    def _add(self, button):
        if len(self.inputs) >= 10:
            self.inputs.pop(0)
        self.inputs.append(button)

    def _check(self, sequence):
        if self.inputs == list(sequence):
            self.inputs.clear()
            return True
        return False

    def _toggle_godmode(self):
        try:
            if self.mem.read_byte(addr.ULTRAMAN) == 0:
                self.mem.write_byte(addr.ULTRAMAN, 2)
                log.info("God mode ON")
            else:
                self.mem.write_byte(addr.ULTRAMAN, 0)
                log.info("God mode OFF")
        except Exception:
            pass
