"""Dungeon thread. Ported from Dungeon.cs InsideDungeonThread().

Monitors dungeon state and orchestrates:
- Floor change detection → spawn check → mini-boss → chest randomization
- Custom weapon effect activation per equipped weapon
- Monster quest kill tracking
- Side quest checks (Samba challenge, Mayor quest)
- Clown loot table swap
- Ungaga door fix, escape powder, repair powder
- Weapon level-up monitoring (Sword of Zeus effect)
- Floor selection screen (back-floor access)
"""

import logging
import random
import struct
import threading
import time
from mods.base import ModBase
from game import addresses as addr
from data.enemies import Enemy, ENEMY_OFFSET, enemiesNormal
from data.player import weapon_slot_addr, Toan
from data import items
from data.customchests import *
from data.miniboss import *

log = logging.getLogger(__name__)

# Dungeon event/boss floors (no mini-boss spawns)
EVENT_FLOORS = {
    0: [3, 7, 14],      # Divine Beast Cave
    1: [8, 16],          # Wise Owl
    2: [8, 17],          # Shipwreck
    3: [8, 17],          # Sun & Moon
    4: [7, 14],          # Moon Sea
    5: [24],             # Gallery of Time
    6: [99],             # Demon Shaft (effectively none)
}

# Dungeon gate keys
GATE_KEYS = {
    0: [items.dranscrest],
    1: [items.shinystone, items.redberry, items.pointychestnut],
    2: [items.hook],
    3: [items.kingsslate],
    4: [items.gunpowder],
    5: [items.clockhands],
    6: [items.blackknightcrest],
}

# Back-floor keys
BACK_FLOOR_KEYS = {
    0: items.tramoil, 1: items.sundew, 2: items.flappingfish,
    3: items.secretpathkey, 4: items.braverylaunch, 5: items.flappingduster,
    6: items.crystaleyeball,
}

# Ungaga door fix addresses per dungeon
UNGAGA_DOORS = {
    3: (0x20928670, 150, [(0x20985E0, 30), (0x20928670, 50.0), (0x20928928, 50.0),
                           (0x20928B14, 30), (0x20928AE4, 30)]),
    4: (0x2092FA08, 150, [(0x2092F978, 30), (0x2092FA08, 50.0), (0x2092FCC0, 50.0),
                           (0x2092FEAC, 30), (0x2092FE7C, 30)]),
    5: (0x209244AC, 150, [(0x2092441C, 30), (0x209244AC, 50.0), (0x20924764, 50.0),
                           (0x20924920, 30), (0x20924950, 30)]),
}

# Sword of Zeus weapon ID
SOZ_ID = 296


class DungeonMod(ModBase):
    name = "Dungeon"

    def __init__(self, mem):
        super().__init__(mem)
        self._r3_held = False
        self.prev_floor = 200
        self.current_floor = 0
        self.current_dungeon = 0
        self.current_weapon = 0
        self.clown_on_screen = False
        self.chronicle2 = False
        self.has_mini_boss = False
        self.enemies_spawn = False
        self.magic_circle_changed = False
        self.has_clear_msg_shown = False
        self.event_floor = False
        self.monsters_dead = [False] * 15
        self.monster_quest_active = False
        self.prev_char_cursor = 0
        self.wep_level_array = [0] * 10
        self.wep_menu_open = False
        self.pp_menu_open = False
        self.square_active = False
        self.dun_escape_confirm = False
        self.dun_escape_spam_check = False
        self.dun_used_active_escape = False
        self.dun_used_escape_check = False
        self.circle_pressed = False
        self._effect_threads = {}
        self.chronicle_whp = 0.0
        self.chronicle_hp = [0] * 16
        self.mini_boss_num = -1
        # Side quest state
        self.samba_quest = False
        self.samba_quest_active = False
        self.samba_quest_check = False
        self.mayor_quest = False
        self.mayor_quest_active = False
        self.mayor_quest_check = False

    def run(self):
        log.info("Dungeon thread activated")
        while self._running:
            try:
                self._tick()
            except Exception as e:
                log.debug("Dungeon tick error: %s", e)
            time.sleep(0.01)  # 10ms poll

    def _tick(self):
        if self._in_dungeon_floor():
            # L3 toggle: always-run (2x movement speed)
            _FEATHER_FLAG = 0x202A35C0
            btn = self.mem.read_short(addr.BUTTON_INPUTS)
            l3_now = bool(btn & 0x0200)
            if l3_now and not getattr(self, '_l3_held', False):
                self._run_mode = not getattr(self, '_run_mode', False)
                self.mem.write_int(_FEATHER_FLAG, 1 if self._run_mode else 0)
                log.info("Run mode %s", "ON" if self._run_mode else "OFF")
            self._l3_held = l3_now

            # Disable limited floor restrictions if option enabled
            if self.mem.read_byte(addr.OPTION_SAVE_NO_LIMIT_ZONES) == 1:
                if self.mem.read_int(addr.LIMIT_ZONE_FLAG) != 0:
                    self.mem.write_int(addr.LIMIT_ZONE_FLAG, 0)

            # Force all magic circles to positive effects (0-4)
            if self.mem.read_byte(addr.OPTION_SAVE_GOOD_CIRCLES) == 1:
                for s, e in [(addr.CIRCLE_SPAWN_1, addr.CIRCLE_EFFECT_1),
                             (addr.CIRCLE_SPAWN_2, addr.CIRCLE_EFFECT_2),
                             (addr.CIRCLE_SPAWN_3, addr.CIRCLE_EFFECT_3),
                             (addr.BF_CIRCLE_SPAWN_1, addr.BF_CIRCLE_EFFECT_1),
                             (addr.BF_CIRCLE_SPAWN_2, addr.BF_CIRCLE_EFFECT_2),
                             (addr.BF_CIRCLE_SPAWN_3, addr.BF_CIRCLE_EFFECT_3)]:
                    if self.mem.read_int(s) != 0 and self.mem.read_byte(e) > 4:
                        self.mem.write_byte(e, self.mem.read_byte(e) % 5)

            if not self._is_paused() and self._is_walking():
                self._weapon_effects()
                self._check_active_items()

            # Synth sphere listener is handled by SynthSphereMod

            # All enemies killed message
            if self._all_enemies_killed() and not self.has_clear_msg_shown:
                self._display_message("DUMMY", 0, 0, 4000, True)
                self.has_clear_msg_shown = True

            self.current_dungeon = self.mem.read_byte(addr.DUNGEON_ID)
            self.current_floor = self.mem.read_byte(addr.DUNGEON_FLOOR)

            # Floor change
            if self.current_floor != self.prev_floor:
                log.info("Floor changed to %d", self.current_floor)
                time.sleep(0.12)  # Brief wait to confirm still in dungeon
                if self._in_dungeon_floor():
                    self._on_floor_enter()
                    self.prev_floor = self.current_floor

            self._check_ungaga_swap()
            self._check_wep_lvl_up()
            self._check_clown()
            self._check_current_sidequests()
            self._check_dungeon_leaving()
            self._check_mini_boss_stamina()

            if self._check_weapon_change():
                self._clear_recent_damage()
                self.current_weapon = self.mem.read_short(addr.DUN_POS_X)  # placeholder
                try:
                    self.current_weapon = self._get_current_weapon_id()
                except Exception:
                    pass
        else:
            self.prev_floor = 200

        # Floor selection screen
        if self.mem.read_byte(addr.DUNGEON_MODE) == 4:
            self._floor_selection_screen()

        # Exit check
        mode = self.mem.read_byte(addr.MODE)
        if mode in (0, 1):
            time.sleep(0.1)
            if self.mem.read_byte(addr.MODE) in (0, 1):
                log.info("Not in-game, exiting dungeon thread")
                self._running = False

    def _in_dungeon_floor(self):
        try:
            return self.mem.read_byte(addr.DUNGEON_FLOOR_CHECK) != 255
        except Exception:
            return False

    def _is_paused(self):
        try:
            return (self.mem.read_short(addr.DUN_PAUSE_PLAYER) == 1 and
                    self.mem.read_short(addr.DUN_PAUSE_ENEMY) == 1 and
                    self.mem.read_short(addr.DUN_PAUSE_TITLE) == 1 and
                    self.mem.read_short(addr.DUN_CAMERA) == 155)
        except Exception:
            return True

    def _is_walking(self):
        try:
            return self.mem.read_short(addr.DUNGEON_MODE) == 1
        except Exception:
            return False

    def _get_current_weapon_id(self):
        # Read from the weapon HUD address
        return self.mem.read_short(0x21EA7590)

    def _all_enemies_killed(self):
        try:
            for i in range(15):
                if self.mem.read_short(Enemy.addr(i, 'hp')) > 0:
                    return False
            return self.mem.read_byte(Enemy.addr(0, 'renderStatus')) > 0
        except Exception:
            return False

    def _on_floor_enter(self):
        """Called when player enters a new dungeon floor."""
        log.info("Player entered floor %d of dungeon %d", self.current_floor, self.current_dungeon)

        # Reset floor state
        self.magic_circle_changed = False
        self.dun_used_active_escape = False
        self.dun_used_escape_check = False
        self.has_clear_msg_shown = False
        self.clown_on_screen = False
        self.has_mini_boss = False

        event_floors = EVENT_FLOORS.get(self.current_dungeon, [])

        if self.current_floor not in event_floors:
            self.event_floor = False
            # Spawn check in background thread
            t = threading.Thread(target=self._check_spawns, daemon=True)
            t.start()
        else:
            self.event_floor = True
            log.info("Event floor — skipping mini-boss")

        # Fix Ungaga doors
        self._fix_ungaga_doors(self.current_dungeon)

        # Init chronicle sword floating numbers
        from mods.custom_effects import chronicle_sword_init
        try:
            chronicle_sword_init(self.mem)
            self.chronicle_whp = 0.0
            self.chronicle_hp = [0] * 16
        except Exception:
            pass

        # Save current weapon
        try:
            self.current_weapon = self._get_current_weapon_id()
        except Exception:
            pass

    def _check_spawns(self):
        """Wait for enemies to spawn, then trigger mini-boss + chest randomization."""
        log.info("Checking spawns...")
        ms = 0

        if self.prev_floor == 200:
            # First floor entry — wait for render status
            while ms < 10000:
                try:
                    if self.mem.read_byte(Enemy.addr(14, 'renderStatus')) != 255:
                        break
                except Exception:
                    pass
                time.sleep(0.1)
                ms += 100
        else:
            # Subsequent floors — wait for HP sentinel
            try:
                self.mem.write_int(Enemy.addr(14, 'hp'), 1)
            except Exception:
                pass
            while ms < 10000:
                try:
                    if self.mem.read_byte(Enemy.addr(14, 'hp')) != 1:
                        break
                except Exception:
                    pass
                time.sleep(0.1)
                ms += 100

        try:
            if self.mem.read_byte(Enemy.addr(0, 'renderStatus')) > 0:
                self.enemies_spawn = True
        except Exception:
            pass

        # Count normal (non-flying) enemies
        normal_count = 0
        for i in range(15):
            try:
                eid = self.mem.read_short(Enemy.addr(i, 'id'))
                if eid in enemiesNormal:
                    normal_count += 1
            except Exception:
                pass

        # Need >3 normal enemies for mini-boss (to avoid Wise Owl 3-key floors)
        if normal_count > 3:
            self._do_miniboss_spawn()
        else:
            log.info("Not enough normal enemies (%d) for mini-boss", normal_count)

        # Chest randomization
        self._chest_randomizer()

        # Reset monster tracking
        self.monsters_dead = [False] * 15
        self._clear_recent_damage()

        log.info("Spawn check complete")

    def _do_miniboss_spawn(self):
        """Roll for mini-boss spawn. Ported from MiniBoss.MiniBossSpawn()."""
        from mods.miniboss import miniboss_spawn
        spawned, num = miniboss_spawn(self.mem, dungeon=self.current_dungeon, floor=self.current_floor)
        if spawned:
            self.has_mini_boss = True
            self.mini_boss_num = num
            log.info("Mini-boss spawned at enemy slot %d", num)
            def _msg():
                ms = 0
                while ms < 8000:
                    try:
                        if self.mem.read_byte(addr.HIDE_HUD) == 0:
                            break
                    except Exception:
                        pass
                    time.sleep(0.1); ms += 100
                self._display_message("A mysterious enemy lurks\naround. Be careful!", 2, 24, 4000)
            threading.Thread(target=_msg, daemon=True).start()
        else:
            log.info("Mini-boss roll: no spawn")

    def _chest_randomizer(self):
        """Randomize chest contents. Ported from CustomChests.ChestRandomizer()."""
        from mods.chests import chest_randomizer
        chest_randomizer(self.mem, self.current_dungeon, self.current_floor, self.chronicle2)

    def _weapon_effects(self):
        """Check equipped weapon and trigger custom effects.
        Ported from the big switch statement in InsideDungeonThread().
        """
        from mods import custom_effects as fx
        char = self.mem.read_byte(addr.CURRENT_CHARACTER)
        wid = self._get_current_weapon_id()

        # Reset bone rapier if not equipped
        if wid != items.bonerapier:
            fx.bone_rapier_effect(self.mem, False)

        # Secret armlet disable on character switch
        if char != 3 and self.magic_circle_changed:
            fx.secret_armlet_disable(self.mem)
            self.magic_circle_changed = False

        # Dispatch per character/weapon
        if char == 0:  # Toan
            if wid == items.bonerapier:
                fx.bone_rapier_effect(self.mem, True)
                self._start_effect_thread('bone_door', fx.bone_door_trigger, self.mem, self)
            elif wid == items.seventhheaven:
                self._start_effect_thread('seventh_heaven', fx.seventh_heaven, self.mem)
            elif wid == items.chroniclesword:
                self._start_effect_thread('chronicle', self._chronicle_tick)
        elif char == 1:  # Xiao
            if wid == items.angelgear:
                self._start_effect_thread('angel_gear', fx.angel_gear, self.mem)
        elif char == 2:  # Goro
            if wid == items.tallhammer:
                self._start_effect_thread('tall_hammer', fx.tall_hammer, self.mem)
            elif wid == items.inferno:
                self._start_effect_thread('inferno', fx.inferno, self.mem)
        elif char == 3:  # Ruby
            if wid == items.mobiusring:
                if self.magic_circle_changed:
                    fx.secret_armlet_disable(self.mem)
                    self.magic_circle_changed = False
                self._start_effect_thread('mobius', fx.mobius_ring, self.mem)
            elif wid == items.secretarmlet:
                if not self.magic_circle_changed:
                    if fx.secret_armlet_enable(self.mem):
                        self.magic_circle_changed = True
            else:
                if self.magic_circle_changed:
                    fx.secret_armlet_disable(self.mem)
                    self.magic_circle_changed = False
        elif char == 4:  # Ungaga
            if wid == items.herculeswrath:
                self._start_effect_thread('hercules', fx.hercules_wrath, self.mem)
            elif wid == items.babelsspear:
                self._start_effect_thread('babel', fx.babel_spear, self.mem)
        elif char == 5:  # Osmond
            if wid == items.supernova:
                self._start_effect_thread('supernova', fx.supernova, self.mem)
            elif wid == items.starbreaker:
                self._start_effect_thread('star_breaker', fx.star_breaker, self.mem)

    def _start_effect_thread(self, name, target, *args):
        """Start an effect thread if not already running."""
        t = self._effect_threads.get(name)
        if t is None or not t.is_alive():
            t = threading.Thread(target=target, args=args, daemon=True)
            t.start()
            self._effect_threads[name] = t

    def _chronicle_tick(self):
        """Run one Chronicle Sword AoE check cycle."""
        from mods.custom_effects import chronicle_sword
        self.chronicle_whp, self.chronicle_hp = chronicle_sword(
            self.mem, self.chronicle_whp, self.chronicle_hp)

    def _check_weapon_change(self):
        try:
            current = self._get_current_weapon_id()
            return current != self.current_weapon
        except Exception:
            return False

    def _check_clown(self):
        """Check if clown appeared and swap loot table."""
        try:
            clown_val = self.mem.read_int(addr.CLOWN_CHECK)
            if clown_val == 30707852 and not self.clown_on_screen and not self.event_floor:
                log.info("Clown appeared — swapping loot table")
                from mods.chests import clown_randomizer
                clown_randomizer(self.mem, self.chronicle2)
                self.clown_on_screen = True
            elif self.clown_on_screen and clown_val != 30707852:
                self.clown_on_screen = False
        except Exception:
            pass

    def _check_ungaga_swap(self):
        """Fix Ungaga's model size when swapping to him."""
        try:
            cur = self.mem.read_byte(0x202A2DE8)
            if cur != self.prev_char_cursor and cur == 4:
                ms = 0
                while ms < 1000:
                    time.sleep(0.1)
                    ms += 100
                    menu_mode = self.mem.read_byte(0x202A2010)
                    if menu_mode == 3:
                        if self.mem.read_short(0x2193A013) == 12850:
                            break
                    else:
                        if self.mem.read_short(0x217E5453) == 12850:
                            break

                menu_mode = self.mem.read_byte(0x202A2010)
                if menu_mode == 3:
                    self.mem.write_byte(0x2193A013, 52)
                    self.mem.write_byte(0x2193A014, 52)
                else:
                    self.mem.write_byte(0x217E5453, 52)
                    self.mem.write_byte(0x217E5454, 52)
            self.prev_char_cursor = cur
        except Exception:
            pass

    def _fix_ungaga_doors(self, dungeon):
        """Fix door collision for Ungaga in certain dungeons."""
        if dungeon not in UNGAGA_DOORS:
            return
        check_addr, check_val, writes = UNGAGA_DOORS[dungeon]
        try:
            if self.mem.read_float(check_addr) == check_val:
                for a, v in writes:
                    if isinstance(v, float):
                        self.mem.write_float(a, v)
                    else:
                        self.mem.write_byte(a, v)
                log.info("Fixed Ungaga doors for dungeon %d", dungeon)
        except Exception:
            pass

    def _check_wep_lvl_up(self):
        """Monitor weapon level-ups for Sword of Zeus thunder absorption effect."""
        try:
            menu_mode = self.mem.read_byte(0x202A2010)
        except Exception:
            return

        if menu_mode in (1, 2):
            if not self.wep_menu_open:
                # Snapshot current levels
                for i in range(10):
                    try:
                        self.wep_level_array[i] = self.mem.read_byte(
                            weapon_slot_addr(0, i, 'level'))
                    except Exception:
                        pass
                self.wep_menu_open = True
            else:
                # Check for level-ups
                for i in range(10):
                    try:
                        cur = self.mem.read_byte(weapon_slot_addr(0, i, 'level'))
                        if cur > self.wep_level_array[i]:
                            self._check_soz_effect(i)
                            self.wep_level_array[i] = cur
                    except Exception:
                        pass
        else:
            self.wep_menu_open = False

    def _check_soz_effect(self, slot):
        """Sword of Zeus: absorb thunder on level-up, scale max attack."""
        try:
            wep_id = self.mem.read_short(weapon_slot_addr(0, slot, 'id'))
            if wep_id != SOZ_ID:
                return

            cur_thunder = self.mem.read_byte(weapon_slot_addr(0, slot, 'thunder'))
            stored = self.mem.read_short(0x21CE446D) + cur_thunder
            stored = min(stored, 30000)

            self.mem.write_byte(weapon_slot_addr(0, slot, 'thunder'), 0)
            if self.mem.read_byte(weapon_slot_addr(0, slot, 'elementHUD')) == 2:
                self.mem.write_byte(weapon_slot_addr(0, slot, 'elementHUD'), 5)
            self.mem.write_short(0x21CE446D, stored)

            # Scale max attack based on stored thunder
            if stored > 2000:
                max_atk = 599 + (stored - 2000) // 20
            elif stored > 1000:
                max_atk = 499 + (stored - 1000) // 10
            elif stored > 500:
                max_atk = 399 + (stored - 500) // 5
            elif stored > 200:
                max_atk = 299 + (stored - 200) // 3
            else:
                max_atk = 199 + stored // 2

            self.mem.write_short(0x2027B298, max_atk)
            log.info("SoZ: absorbed %d thunder, max attack now %d", cur_thunder, max_atk)
        except Exception as e:
            log.debug("SoZ effect error: %s", e)

    def _check_current_sidequests(self):
        """Track monster quest kills and side quest progress."""
        if self.monster_quest_active and self.current_dungeon != 6:
            for i in range(15):
                try:
                    hp = self.mem.read_short(Enemy.addr(i, 'hp'))
                    if hp > 0:
                        self.monsters_dead[i] = False
                    elif not self.monsters_dead[i]:
                        self._check_enemy_kill(Enemy.addr(i, 'hp'))
                        self.monsters_dead[i] = True
                except Exception:
                    pass

        if self.samba_quest:
            self._samba_challenge()
        if self.mayor_quest:
            self._mayor_quest()

    def _check_enemy_kill(self, enemy_addr):
        """Check if killed enemy matches a quest target."""
        quest_data = [
            # (quest_active_flag, target_id_addr, kills_addr, status_addr, name)
            (0x21CE4402, 0x21CE4406, 0x21CE4405, 0x21CE4402, "Macho"),
            (0x21CE4407, 0x21CE440B, 0x21CE440A, 0x21CE4407, "Gob"),
            (0x21CE440C, 0x21CE4410, 0x21CE440F, 0x21CE440C, "Jake"),
            (0x21CE4411, 0x21CE4415, 0x21CE4414, 0x21CE4411, "Chief Bonka"),
        ]
        enemy_type_addr = enemy_addr + 0x1E

        for status_addr, target_addr, kills_addr, complete_addr, name in quest_data:
            try:
                status = self.mem.read_byte(status_addr)
                if status != 1:  # Not active
                    continue
                if self.mem.read_byte(enemy_type_addr) == self.mem.read_byte(target_addr):
                    kills = self.mem.read_byte(kills_addr) - 1
                    self.mem.write_byte(kills_addr, kills)
                    if kills == 0:
                        self._display_message(f"You completed {name}'s quest!\nWell done!", 2, 30, 4000)
                        self.mem.write_byte(complete_addr, 2)
                        log.info("%s quest complete!", name)
            except Exception:
                pass

    def _samba_challenge(self):
        """Samba's dagger-only challenge quest on Moon Sea floor 6."""
        try:
            weapon_id = self.mem.read_short(0x21EA7590)
            in_floor = self.mem.read_byte(0x202A34CC) == 1

            if not self.samba_quest_check and in_floor:
                if self.mem.read_byte(addr.HIDE_HUD) == 0:
                    ally = self.mem.read_byte(0x202A3570)
                    if ally == 0 and weapon_id in (257, 258):
                        self.mem.write_int(0x21CE205C, 0)
                        self._display_message(
                            "Samba's quest started!\nClear all enemies using only Dagger!\n"
                            "Using a throwable also\ncancels the mission.", 4, 40, 8000)
                        self.samba_quest_active = True
                        self.monsters_dead = [False] * 15
                    elif ally == 0:
                        self._display_message("Samba's quest did not start.\nRe-enter with Dagger equipped.", 2, 30, 4000)
                        self.samba_quest_active = False
                    self.samba_quest_check = True
            elif self.samba_quest_check and not in_floor:
                self.samba_quest_check = False
                self.samba_quest_active = False

            if self.samba_quest_active:
                anim = self.mem.read_byte(0x21DC4484)
                if (weapon_id not in (257, 258)) or anim in (26, 27):
                    time.sleep(0.5)
                    self._display_message("Samba's quest has been cancelled.\nRe-enter in order to activate it.", 2, 40, 4000)
                    self.samba_quest_active = False
                    return

                killed = sum(1 for i in range(8)
                             if self.mem.read_short(Enemy.addr(i, 'hp')) == 0)
                if killed == 8:
                    self._display_message("Samba's quest completed!\nWell done!", 2, 28, 4000)
                    self.mem.write_byte(0x21CE4462, 1)
                    self.samba_quest = False
        except Exception:
            pass

    def _mayor_quest(self):
        """Mayor's character-locked quest in Demon Shaft."""
        try:
            in_floor = self.mem.read_byte(0x202A34CC) == 1

            if not self.mayor_quest_check and in_floor:
                if self.mem.read_byte(addr.HIDE_HUD) == 0:
                    required_ally = self.mem.read_byte(0x21CE446A)
                    current_ally = self.mem.read_byte(0x202A3570)
                    if current_ally == required_ally:
                        self.mem.write_int(0x21CE205C, 0)
                        self._display_message(
                            "Mayor's quest started!\nClear all enemies.\n"
                            "Cannot change character.\nThrowables are not allowed.", 4, 26, 5000)
                        self.mayor_quest_active = True
                        self.monsters_dead = [False] * 15
                    else:
                        self._display_message("Mayor's quest did not start.\nRe-enter with correct ally.", 2, 30, 4000)
                        self.mayor_quest_active = False
                    self.mayor_quest_check = True
            elif self.mayor_quest_check and not in_floor:
                self.mayor_quest_check = False
                self.mayor_quest_active = False

            if self.mayor_quest_active:
                anim = self.mem.read_byte(0x21DC4484)
                if anim in (26, 27):
                    time.sleep(0.5)
                    self._display_message("Mayor's quest has been cancelled.\nRe-enter in order to re-attempt it.", 2, 40, 4000)
                    self.mayor_quest_active = False
                    return

                killed = sum(1 for i in range(8)
                             if self.mem.read_short(Enemy.addr(i, 'hp')) == 0)
                if killed == 8:
                    self._display_message("Mayor's quest completed!\nWell done!", 2, 28, 4000)
                    self.mem.write_byte(0x21CE4468, 2)
                    self.mayor_quest = False
        except Exception:
            pass

    def _floor_selection_screen(self):
        """Allow back-floor access from floor selection. Ported from FloorSelectionScreen()."""
        try:
            btn = self.mem.read_short(addr.BUTTON_INPUTS)
            if not self.circle_pressed:
                if btn == 0x0020:  # Circle
                    self.circle_pressed = True
            else:
                if btn != 0x0020:
                    self.mem.write_short(addr.DUNGEON_DEBUG_MENU, 170)
                    self.mem.write_byte(addr.DUNGEON_MODE, 1)
                    self.circle_pressed = False
        except Exception:
            pass

    def _check_active_items(self):
        """Handle escape powder consumption from active item slots."""
        if not self.dun_used_active_escape and not self.dun_used_escape_check:
            try:
                if self.mem.read_byte(addr.DUNGEON_DEBUG_MENU) == 171:
                    from mods.custom_effects import check_escape_powders
                    check_escape_powders(self.mem)
                    self.dun_used_escape_check = True
            except Exception:
                pass

    def _check_dungeon_leaving(self):
        """Reset escape tracking when leaving dungeon."""
        try:
            if self.mem.read_byte(addr.DUNGEON_MODE) != 1:
                self.dun_used_active_escape = False
                self.dun_used_escape_check = False
        except Exception:
            pass

    def _check_mini_boss_stamina(self):
        """Keep mini-boss stamina high so it can't be stunned."""
        if self.has_mini_boss and self.mini_boss_num >= 0:
            try:
                st = self.mem.read_int(Enemy.addr(self.mini_boss_num, 'staminaTimer'))
                if st < 60:
                    self.mem.write_int(Enemy.addr(self.mini_boss_num, 'staminaTimer'), 60000)
            except Exception:
                pass
            # Disable on backfloor
            try:
                if self.mem.read_byte(addr.DUN_BACKFLOOR_FLAG) != 0:
                    self.has_mini_boss = False
            except Exception:
                pass

    def _display_message(self, text, lines, width, duration, clear=False):
        """Write a message to the dungeon HUD using full encoding."""
        from game.display import display_message
        display_message(self.mem, text, lines, width, duration, clear)

    def _clear_recent_damage(self):
        """Reset damage tracking addresses."""
        try:
            self.mem.write_int(addr.MOST_RECENT_DAMAGE, 0)
            self.mem.write_int(addr.DAMAGE_SOURCE, 0)
        except Exception:
            pass
