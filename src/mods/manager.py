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
from mods.weapons import WeaponsMod, SynthSphereMod, WeaponRerollMod, AttachmentOverlayMod
from mods.dungeon import DungeonMod
from mods.town import TownMod, ElementSwapMod
from mods.cheatcodes import CheatCodesMod
from mods.custom_effects import check_chronicle2

log = logging.getLogger(__name__)

# Option: (save_addr, runtime_addr) — None runtime means special handling
_OPTIONS = [
    (addr.OPTION_SAVE_GRAPHICS, addr.OPTION_GRAPHICS),
    (addr.OPTION_SAVE_WIDESCREEN, addr.OPTION_WIDESCREEN),
    (addr.OPTION_SAVE_BEEP, addr.OPTION_BEEP),
    (addr.OPTION_SAVE_BATTLE_MUSIC, addr.OPTION_BATTLE_MUSIC),
]


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
        self.attach_overlay = AttachmentOverlayMod(mem)
        self.dungeon = DungeonMod(mem)
        self.town = TownMod(mem)
        self.element_swap = ElementSwapMod(mem)
        self.cheat_codes = CheatCodesMod(mem)

        self.all_mods = [
            self.shop, self.weapons, self.synth_sphere, self.weapon_reroll,
            self.attach_overlay,
            self.dungeon, self.town,
            self.element_swap, self.cheat_codes,
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

    def stop_nowait(self):
        """Signal all threads to stop without waiting."""
        self._running = False
        for mod in self.all_mods:
            mod._running = False

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
                time.sleep(0.1)
                game_mode = self.mem.read_byte(addr.MODE)
                if game_mode == addr.Mode.CUTSCENE:
                    # New game — set enhanced save flag + intro text
                    time.sleep(0.8)
                    self.mem.write_byte(addr.ENHANCED_MOD_SAVE_FLAG, 1)
                    time.sleep(0.2)
                    from mods.dialogues import intro_text_at_norune
                    intro_text_at_norune(self.mem)
                    log.info("New game detected, set enhanced save flag")

                # Check flag (may have just been set above for new game)
                if self.mem.read_byte(addr.ENHANCED_MOD_SAVE_FLAG) == 1:
                    log.info("Entering in-game, starting mod subsystems")
                    self._apply_saved_options()
                    self._start_mods()
                    self._ingame = True
                else:
                    log.warning("Not a Reforged Mod save file!")
                    if self.mem.read_byte(addr.DUNGEON_FLOOR_CHECK) != 255:
                        self.mem.write_int(addr.DUNGEON_DEBUG_MENU, 151)
                    else:
                        self.mem.write_byte(addr.MODE, 1)

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

    def _apply_saved_options(self):
        """Copy saved option flags to runtime addresses (C# ModWindowSettingsCheck)."""
        for save_addr, runtime_addr in _OPTIONS:
            val = self.mem.read_byte(save_addr)
            self.mem.write_byte(runtime_addr, 1 if val == 1 else 0)
        # Attack sounds
        if self.mem.read_byte(addr.OPTION_SAVE_ATTACK_SOUNDS) == 1:
            for a in addr.ATTACK_SOUND_ADDRS:
                self.mem.write_byte(a, 0)
        else:
            for i, a in enumerate(addr.ATTACK_SOUND_ADDRS):
                self.mem.write_byte(a, addr.ATTACK_SOUND_DEFAULTS[i])
        # Mute music
        if self.mem.read_byte(addr.OPTION_SAVE_MUTE_MUSIC) == 1:
            self.mem.write_short(addr.MUSIC_VOLUME_ADDR, 0)
        else:
            self.mem.write_short(addr.MUSIC_VOLUME_ADDR, addr.MUSIC_VOLUME_DEFAULT)
        # Instant fishing — default ON for new saves
        if self.mem.read_byte(addr.OPTION_SAVE_INSTANT_FISH) == 0:
            self.mem.write_byte(addr.OPTION_SAVE_INSTANT_FISH, 1)
        # No limit zones — default ON for new saves
        if self.mem.read_byte(addr.OPTION_SAVE_NO_LIMIT_ZONES) == 0:
            self.mem.write_byte(addr.OPTION_SAVE_NO_LIMIT_ZONES, 1)
        # Good magic circles — default ON for new saves
        if self.mem.read_byte(addr.OPTION_SAVE_GOOD_CIRCLES) == 0:
            self.mem.write_byte(addr.OPTION_SAVE_GOOD_CIRCLES, 1)
        # Repair powder fallback — default ON for new saves
        if self.mem.read_byte(addr.OPTION_SAVE_REPAIR_FALLBACK) == 0:
            self.mem.write_byte(addr.OPTION_SAVE_REPAIR_FALLBACK, 1)

    def _stop_mods(self):
        for mod in self.all_mods:
            mod.stop()
        self._mods_started = False
        self._ingame = False
