"""Weapon systems. Ported from Weapons.cs.

Three subsystems:
1. WeaponsMod — one-time balance writes to weapon database table
2. SynthSphereMod — monitors customize menu for empty synth sphere → auto +5
3. WeaponRerollMod — periodic random reroll of special effects on certain weapons
"""

import logging
import random
import time
from mods.base import ModBase
from game import addresses as addr
from data.weapons import (
    BALANCE_CHANGES, LAMB_CHANGES, BALANCE_CHECK_ADDR, BALANCE_CHECK_VALUE,
    db_addr, weaponoffset, attack, maxattack, endurance, effect, effect2,
    buildup, xiaooffset, gorooffset, rubyoffset, ungagaoffset, osmondoffset,
    daggerid, woodenid, malletid, goldringid, stickid, machinegunid,
    UNGAGA_WEAPON_RANGE, UNGAGA_SKIP_ID, UNGAGA_BUFFS,
    OSMOND_WEAPON_RANGE, OSMOND_BUFFS,
    lambTransformThreshold, lambStatsThreshold,
)
from data.player import weapon_slot_addr
from data.items import (
    synthsphere, heavenscloud, darkcloud, bigbang, atlamilliasword, dusack,
    goddessring, destructionring, satansring, skunk, swallow,
)

log = logging.getLogger(__name__)

# Write type dispatch
_WRITERS = {
    'u8':  lambda mem, a, v: mem.write_byte(a, v),
    'u16': lambda mem, a, v: mem.write_short(a, v),
    'u32': lambda mem, a, v: mem.write_int(a, v),
    'i32': lambda mem, a, v: mem.write_int(a, v),
    'f32': lambda mem, a, v: mem.write_float(a, v),
    'f64': lambda mem, a, v: mem.write_int(a, v),  # WriteDouble not in PINE; use 2x int if needed
}


class WeaponsMod(ModBase):
    """One-time weapon balance changes from WeaponsBalanceChanges()."""
    name = "Weapon Balance"

    def run(self):
        self.apply_once()

    def apply_once(self):
        # Check if already applied
        try:
            val = self.mem.read_short(BALANCE_CHECK_ADDR)
            if val == BALANCE_CHECK_VALUE:
                log.info("Weapon balance already applied")
                self._applied = True
                return
        except Exception:
            pass

        log.info("Applying weapon balance changes...")

        # Static balance table
        for entry in BALANCE_CHANGES:
            stat_addr, char_off, wep_id, base_id, value, wtype = entry
            addr_final = db_addr(stat_addr, char_off, wep_id, base_id)
            try:
                _WRITERS[wtype](self.mem, addr_final, value)
            except Exception as e:
                log.debug("Balance write failed at %s: %s", hex(addr_final), e)

        # Lamb sword thresholds
        for addr_val, value, wtype in LAMB_CHANGES:
            try:
                if wtype == 'f64':
                    # PINE doesn't have write_double; write as two 32-bit
                    import struct
                    raw = struct.pack('<d', value)
                    lo, hi = struct.unpack('<II', raw)
                    self.mem.write_int(addr_val, lo)
                    self.mem.write_int(addr_val + 4, hi)
                else:
                    _WRITERS[wtype](self.mem, addr_val, int(value * (2**31 - 1)) if wtype == 'f32' else value)
                    # Actually just use write_float properly
                    if wtype == 'f32':
                        self.mem.write_float(addr_val, value)
            except Exception as e:
                log.debug("Lamb write failed: %s", e)

        # Ungaga loop: +10 atk, +10 maxatk, +15 endurance (skip id 357)
        lo, hi = UNGAGA_WEAPON_RANGE
        for wid in range(lo, hi + 1):
            if wid == UNGAGA_SKIP_ID:
                continue
            try:
                for stat_name, stat_addr_base, buff in [
                    ('attack', attack, UNGAGA_BUFFS['attack']),
                    ('maxattack', maxattack, UNGAGA_BUFFS['maxattack']),
                    ('endurance', endurance, UNGAGA_BUFFS['endurance']),
                ]:
                    a = db_addr(stat_addr_base, ungagaoffset, wid, stickid)
                    cur = self.mem.read_short(a)
                    self.mem.write_short(a, cur + buff)
            except Exception as e:
                log.debug("Ungaga buff failed for %d: %s", wid, e)

        # Osmond loop: +15 atk, +15 maxatk
        lo, hi = OSMOND_WEAPON_RANGE
        for wid in range(lo, hi + 1):
            try:
                for stat_addr_base, buff in [
                    (attack, OSMOND_BUFFS['attack']),
                    (maxattack, OSMOND_BUFFS['maxattack']),
                ]:
                    a = db_addr(stat_addr_base, osmondoffset, wid, machinegunid)
                    cur = self.mem.read_short(a)
                    self.mem.write_short(a, cur + buff)
            except Exception as e:
                log.debug("Osmond buff failed for %d: %s", wid, e)

        self._applied = True
        log.info("Weapon balance changes applied (%d entries)", len(BALANCE_CHANGES))


class SynthSphereMod(ModBase):
    """Monitors weapon customize menu for empty synth sphere → auto level to +5.
    Ported from Weapons.WeaponListenForSynthSphere().
    The C# version is 3000+ lines of copy-paste switch cases; we use offset math.
    """
    name = "Synth Sphere"

    def run(self):
        log.info("Synth sphere listener started")
        while self._running:
            if not self._in_customize_menu():
                time.sleep(0.1)
                continue
            self._check_synth()
            time.sleep(0.064)  # 64ms — matches C# WeaponListenForSynthSphere

    def _in_customize_menu(self):
        try:
            menu = self.mem.read_byte(addr.SELECTED_MENU)
            wmode = self.mem.read_byte(addr.WEAPONS_MODE)
            return menu == 2 and 8 <= wmode <= 11
        except Exception:
            return False

    def _check_synth(self):
        try:
            char_idx = self.mem.read_byte(addr.WEAPON_MENU_CHAR_HOVER)
            slot_num = self.mem.read_byte(addr.WEAPON_MENU_WEAPON_HOVER)
        except Exception:
            return

        if char_idx > 5 or slot_num > 9:
            return

        try:
            atk = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'attack'))
            end = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'endurance'))
            spd = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'speed'))
            mag = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'magic'))
            changed = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'hasChangedBySynth'))
            level = self.mem.read_byte(weapon_slot_addr(char_idx, slot_num, 'level'))
            diff = 5 - level

            item_id = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'slot1_itemId'))
            synth_id = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'slot1_synthesisedItemId'))

            if item_id == synthsphere and synth_id == 0:
                # Empty synth sphere socketed — boost to +5
                if diff > 0 and changed == 0:
                    self.mem.write_byte(weapon_slot_addr(char_idx, slot_num, 'level'), 5)
                    self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'attack'), atk + diff)
                    self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'endurance'), end + diff)
                    self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'speed'), spd + diff)
                    self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'magic'), mag + diff)
                    self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'weaponFormerStatsValue'), diff)
                    self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'hasChangedBySynth'), 1)
                    log.info("Synth sphere: boosted char %d slot %d to +5", char_idx, slot_num)
            elif diff == 0 and changed == 1:
                # Synth sphere removed at +5 — revert
                former = self.mem.read_short(weapon_slot_addr(char_idx, slot_num, 'weaponFormerStatsValue'))
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'level'), 5 - former)
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'attack'), atk - former)
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'endurance'), end - former)
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'speed'), spd - former)
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'magic'), mag - former)
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'weaponFormerStatsValue'), 0)
                self.mem.write_short(weapon_slot_addr(char_idx, slot_num, 'hasChangedBySynth'), 0)
                log.info("Synth sphere: reverted char %d slot %d", char_idx, slot_num)
        except Exception as e:
            log.debug("Synth check error: %s", e)


class WeaponRerollMod(ModBase):
    """Periodic random reroll of special effects on certain weapons.
    Ported from Weapons.RerollWeaponSpecialAttributes().
    """
    name = "Weapon Reroll"

    # (effect_addr_base, char_offset, weapon_id, base_id, options)
    # options: list of (effect1_val, effect2_val) tuples, 50% chance of getting one
    REROLL_TABLE = [
        # Heaven's Cloud: 50% chance → (poison OR critical)
        {'e1': (0, heavenscloud, daggerid), 'e2': (0, heavenscloud, daggerid),
         'opts': [(32, 0), (0, 16)]},
        # Dark Cloud: 50% chance → (poison OR stop)
        {'e1': (0, darkcloud, daggerid), 'e2': None,
         'opts': [(32,), (64,)]},
        # Big Bang: 50% chance → (critical OR stop)
        {'e1': (0, bigbang, daggerid), 'e2': (0, bigbang, daggerid),
         'opts': [(0, 16), (64, 0)]},
        # Atlamillia Sword: 50% chance → (heal OR stop)
        {'e1': (0, atlamilliasword, daggerid), 'e2': (0, atlamilliasword, daggerid),
         'opts': [(0, 8), (64, 0)]},
    ]

    def run(self):
        log.info("Weapon reroll effects started")
        while self._running:
            # Exit if not in-game
            try:
                mode = self.mem.read_byte(addr.MODE)
                if mode in (0, 1):
                    time.sleep(0.1)
                    if self.mem.read_byte(addr.MODE) in (0, 1):
                        log.info("Not in-game, stopping reroll")
                        break
            except Exception:
                time.sleep(1)
                continue

            self._do_rerolls()
            time.sleep(1)

    def _do_rerolls(self):
        rnd = random.random
        wo = weaponoffset

        try:
            # Heaven's Cloud
            if rnd() < 0.5:
                if rnd() < 0.5:
                    self.mem.write_byte(db_addr(effect, 0, heavenscloud, daggerid), 32)
                    self.mem.write_byte(db_addr(effect2, 0, heavenscloud, daggerid), 0)
                else:
                    self.mem.write_byte(db_addr(effect2, 0, heavenscloud, daggerid), 16)
                    self.mem.write_byte(db_addr(effect, 0, heavenscloud, daggerid), 0)
            else:
                self.mem.write_byte(db_addr(effect, 0, heavenscloud, daggerid), 0)
                self.mem.write_byte(db_addr(effect2, 0, heavenscloud, daggerid), 0)

            # Dark Cloud
            if rnd() < 0.5:
                val = 32 if rnd() < 0.5 else 64
                self.mem.write_byte(db_addr(effect, 0, darkcloud, daggerid), val)
            else:
                self.mem.write_byte(db_addr(effect, 0, darkcloud, daggerid), 0)

            # Big Bang
            if rnd() < 0.5:
                if rnd() < 0.5:
                    self.mem.write_byte(db_addr(effect2, 0, bigbang, daggerid), 16)
                    self.mem.write_byte(db_addr(effect, 0, bigbang, daggerid), 0)
                else:
                    self.mem.write_byte(db_addr(effect, 0, bigbang, daggerid), 64)
                    self.mem.write_byte(db_addr(effect2, 0, bigbang, daggerid), 0)
            else:
                self.mem.write_byte(db_addr(effect, 0, bigbang, daggerid), 0)
                self.mem.write_byte(db_addr(effect2, 0, bigbang, daggerid), 0)

            # Atlamillia Sword
            if rnd() < 0.5:
                if rnd() < 0.5:
                    self.mem.write_byte(db_addr(effect2, 0, atlamilliasword, daggerid), 8)
                    self.mem.write_byte(db_addr(effect, 0, atlamilliasword, daggerid), 0)
                else:
                    self.mem.write_byte(db_addr(effect, 0, atlamilliasword, daggerid), 64)
                    self.mem.write_byte(db_addr(effect2, 0, atlamilliasword, daggerid), 0)
            else:
                self.mem.write_byte(db_addr(effect, 0, atlamilliasword, daggerid), 0)
                self.mem.write_byte(db_addr(effect2, 0, atlamilliasword, daggerid), 0)

            # Dusack: 50% steal
            if rnd() < 0.5:
                self.mem.write_byte(db_addr(effect, 0, dusack, daggerid), 128)
            else:
                self.mem.write_byte(db_addr(effect, 0, dusack, daggerid), 0)

            # Goddess Ring: 50% heal
            if rnd() < 0.5:
                self.mem.write_byte(db_addr(effect2, rubyoffset, goddessring, goldringid), 8)
            else:
                self.mem.write_byte(db_addr(effect2, rubyoffset, goddessring, goldringid), 0)

            # Destruction Ring: 50% critical
            if rnd() < 0.5:
                self.mem.write_byte(db_addr(effect2, rubyoffset, destructionring, goldringid), 16)
            else:
                self.mem.write_byte(db_addr(effect2, rubyoffset, destructionring, goldringid), 0)

            # Satan's Ring: 50% drain
            if rnd() < 0.5:
                self.mem.write_byte(db_addr(effect2, rubyoffset, satansring, goldringid), 4)
            else:
                self.mem.write_byte(db_addr(effect2, rubyoffset, satansring, goldringid), 0)

            # Skunk: 50% poison
            if rnd() < 0.5:
                self.mem.write_byte(db_addr(effect, osmondoffset, skunk, machinegunid), 32)
            else:
                self.mem.write_byte(db_addr(effect, osmondoffset, skunk, machinegunid), 0)

            # Swallow: 50% steal
            if rnd() < 0.5:
                self.mem.write_byte(db_addr(effect, osmondoffset, swallow, machinegunid), 128)
            else:
                self.mem.write_byte(db_addr(effect, osmondoffset, swallow, machinegunid), 0)

        except Exception as e:
            log.debug("Reroll error: %s", e)


class AttachmentOverlayMod(ModBase):
    """Shows attachment stats overlay when hovering items in customize menu or FP shop."""
    name = "Attachment Overlay"

    def run(self):
        self._last_id = -1
        from core.settings import get as get_setting
        while self._running:
            if not get_setting("overlay_attachments"):
                time.sleep(0.5)
                continue
            item_id = self._get_hovered_item()
            if item_id is None:
                if self._last_id != -1:
                    self._hide()
                    self._last_id = -1
                time.sleep(0.1)
                continue
            if item_id != self._last_id:
                self._last_id = item_id
                self._show_stats(item_id)
            time.sleep(0.064)

    def _get_hovered_item(self):
        """Return item ID if hovering an attachment in customize menu or FP shop."""
        try:
            menu = self.mem.read_byte(addr.SELECTED_MENU)
            wmode = self.mem.read_byte(addr.WEAPONS_MODE)
            # Customize menu: cursor on attachment bag
            if menu == 2 and wmode == 10:
                slot = self.mem.read_byte(addr.WEAPON_MENU_LIST_INDEX)
                return self.mem.read_short(addr.FIRST_BAG_ATTACHMENT + slot * 0x20)
            # Regular shop: read hovered item from display slots
            if self.mem.read_byte(0x21DA52E4) == 1 and self.mem.read_byte(0x21DA52E8) == 11:
                idx = self.mem.read_int(0x21D900E4)
                item = self.mem.read_short(0x218377A0 + idx * 0xFC)
                if item > 0:
                    return item
            # FP Exchange: a6 state=3 when browsing, cursor at 0x21D90394, item table at 0x202929D0
            if self.mem.read_short(0x21D903A6) == 3:
                idx = self.mem.read_short(0x21D903A4)
                item = self.mem.read_short(0x202929D0 + idx * 4)
                if item > 0:
                    return item
        except Exception:
            pass
        return None

    def _show_stats(self, item_id):
        from data.attachments import get_attachment_info
        info = get_attachment_info(item_id)
        if not info:
            self._hide()
            return
        name, stats = info
        lines = ["^Y" + name]
        for sn, sv in stats:
            lines.append(f"^W{sn}: ^G+{sv}")
        from ui.overlay import show_text
        show_text("\n".join(lines))

    def _hide(self):
        try:
            from ui.overlay import hide_text
            hide_text()
        except Exception:
            pass
