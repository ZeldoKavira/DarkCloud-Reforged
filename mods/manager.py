"""Mod orchestrator. Manages all mod subsystems and their lifecycle.
Equivalent to MainMenuThread.cs TitleMenu() thread management.
"""

import logging
import threading
import time
from core.memory import Memory
from game.game_state import GameState, GameSnapshot
from game import addresses as addr
from mods.shop import ShopMod
from mods.weapons import WeaponsMod, SynthSphereMod, WeaponRerollMod
from mods.dungeon import DungeonMod
from mods.town import TownMod, ElementSwapMod
from mods.cheatcodes import CheatCodesMod
from mods.custom_effects import check_chronicle2

log = logging.getLogger(__name__)


class ModManager:
    """Orchestrates all mod subsystems based on game state."""

    def __init__(self, mem: Memory, state: GameState):
        self.mem = mem
        self.state = state
        self._running = False
        self._thread = None
        self._ingame = False
        self._mods_started = False

        # Mod subsystems
        self.shop = ShopMod(mem)
        self.weapons = WeaponsMod(mem)
        self.synth_sphere = SynthSphereMod(mem)
        self.weapon_reroll = WeaponRerollMod(mem)
        self.dungeon = DungeonMod(mem)
        self.town = TownMod(mem)
        self.element_swap = ElementSwapMod(mem)
        self.cheat_codes = CheatCodesMod(mem)

        self.all_mods = [
            self.shop, self.weapons, self.synth_sphere, self.weapon_reroll,
            self.dungeon, self.town, self.element_swap, self.cheat_codes,
        ]

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._main_loop, daemon=True, name="ModManager")
        self._thread.start()

    def stop(self):
        self._running = False
        for mod in self.all_mods:
            mod.stop()
        if self._thread:
            self._thread.join(timeout=3)

    def _main_loop(self):
        """Main mod loop — mirrors MainMenuThread.CheckEmulatorAndGame + TitleMenu."""
        log.info("Mod manager started")

        while self._running:
            self.state.poll()
            snap = self.state.snapshot

            if not snap.connected or not snap.dc1_detected:
                if self._mods_started:
                    self._stop_mods()
                time.sleep(1)
                continue

            if not snap.flags.pnach_active:
                time.sleep(0.5)
                continue

            # Set mod flag so PNACH knows we're running
            self.mem.write_byte(addr.MOD_FLAG, 1)

            game_mode = snap.game_mode

            # Detect entering in-game
            if not self._ingame and game_mode in (addr.Mode.TOWN, addr.Mode.DUNGEON, addr.Mode.CUTSCENE):
                if snap.flags.enhanced_save or game_mode == addr.Mode.CUTSCENE:
                    log.info("Entering in-game, starting mod subsystems")
                    self._start_mods()
                    self._ingame = True

            # Detect returning to main menu
            if self._ingame and game_mode in (addr.Mode.TITLE, addr.Mode.INTRO):
                log.info("Returned to main menu")
                self._stop_mods()
                self._ingame = False

            # Save state detection
            if snap.frame_counter > 0 and snap.prev_frame_counter > 0:
                if (snap.frame_counter < snap.prev_frame_counter or
                        snap.frame_counter > snap.prev_frame_counter + 360):
                    log.warning("Save state detected!")

            # Update mod status in snapshot
            snap.mod_status.town_thread = self.town.active
            snap.mod_status.dungeon_thread = self.dungeon.active
            snap.mod_status.weapons_thread = self.synth_sphere.active
            snap.mod_status.shop_applied = self.shop.applied
            snap.mod_status.weapon_balance_applied = self.weapons.applied

            time.sleep(0.001)

        # Cleanup
        self.mem.write_byte(addr.MOD_FLAG, 0)

    def _start_mods(self):
        if self._mods_started:
            return
        for mod in self.all_mods:
            mod.start()
        self._mods_started = True

    def _stop_mods(self):
        for mod in self.all_mods:
            mod.stop()
        self._mods_started = False
        self._ingame = False
