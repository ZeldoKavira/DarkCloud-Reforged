"""Fishing quest tracking. Ported from TownCharacter.CheckFishingQuest().

Monitors fish catches during fishing mode and tracks quest progress.
The C# version duplicates the same logic 4 times per area — this
collapses it into a data-driven approach.
"""

import logging
import math
import time
from game import addresses as addr

log = logging.getLogger(__name__)

# Per-area fishing config: (fish_base_addr, fish_count, fp_base_addr,
#   quest_active_addr, quest_addrs_dict)
_AREA_CONFIG = {
    0: {  # Norune
        'fish_base': 0x214798D0, 'count': 4, 'fp_base': 0x214798E0,
        'active_addr': 0x21CE4416,
        'type_addr': 0x21CE4417, 'id_addr': 0x21CE4419,
        'counter_addr': 0x21CE441A,
        'min_size': 0x21CE441B, 'max_size': 0x21CE441C,
    },
    1: {  # Matataki
        'fish_base': 0x214D9910, 'count': 5, 'fp_base': 0x214D9920,
        'active_addr': 0x21CE441E,
        'type_addr': 0x21CE441F, 'id_addr': 0x21CE4421,
        'counter_addr': 0x21CE4422,
        'min_size': 0x21CE4423, 'max_size': 0x21CE4424,
    },
    19: {  # Queens
        'fish_base': 0x20DE0710, 'count': 5, 'fp_base': 0x20DE0720,
        'active_addr': 0x21CE4427,
        'type_addr': 0x21CE4428, 'id_addr': 0x21CE442A,
        'counter_addr': 0x21CE442B,
        'min_size': 0x21CE442C, 'max_size': 0x21CE442D,
        'complete_count': 0x21CE442F,
    },
    3: {  # Muska Racka
        'fish_base': 0x213C3150, 'count': 4, 'fp_base': 0x213C3160,
        'active_addr': 0x21CE4431,
        'type_addr': 0x21CE4432, 'id_addr': 0x21CE4434,
        'counter_addr': 0x21CE4435,
        'min_size': 0x21CE4436, 'max_size': 0x21CE4437,
    },
}

FISH_STRIDE = 0x2410
CATCH_CHECK = 0x202A26E8  # == 12 when fish is being reeled in
FISH_FLAG_BASE = 0x21CE4439

# Fish ID → name (matches C# allfish array)
_FISH_NAMES = [
    "Bobo", "Gobbler", "Nonky", "Kaiji", "Baku Baku", "Mardan Garayan",
    "Gummy", "Niler", None, "Umadakara", "Tarton", "Piccoly",
    "Bon", "Hamahama", "Negie", "Den", "Heela", "Baron Garayan",
]


def get_pond_fish(mem, area):
    """Read fish IDs from the pond and return list of fish names."""
    cfg = _AREA_CONFIG.get(area)
    if not cfg:
        return []
    names = []
    addr = cfg['fish_base']
    for _ in range(cfg['count']):
        fid = mem.read_byte(addr)
        if fid < len(_FISH_NAMES) and _FISH_NAMES[fid]:
            names.append(_FISH_NAMES[fid])
        addr += FISH_STRIDE
    return names


def get_pond_status(mem, area):
    """Return overlay text showing each fish and its current state."""
    cfg = _AREA_CONFIG.get(area)
    if not cfg:
        return None
    lines = ["^YFish in pond:"]
    base = cfg['fish_base']
    for i in range(cfg['count']):
        slot = base + i * FISH_STRIDE
        fid = mem.read_byte(slot)
        if fid == 255:
            continue  # caught / empty slot
        if fid >= len(_FISH_NAMES) or not _FISH_NAMES[fid]:
            continue
        name = _FISH_NAMES[fid]
        state = _read_state(mem, slot + _AI_STATE)
        if state == 8:
            lines.append(f"^R  !! {name} - BITE !!")
        elif state in (6, 7):
            lines.append(f"^Y  > {name} - interested")
        else:
            lines.append(f"^W  {name}")
    return "\n".join(lines) if len(lines) > 1 else "^WNo fish remaining"

# Fish AI object offsets (from Step__5CFishFv)
_AI_STATE = 0x50       # piVar6[0x14] — fish behavior state
_AI_MOVE_MODE = 0x4C   # piVar6[0x13] — 0=idle, 1=swim, 2=fast swim
_AI_TIMER1 = 0x54      # piVar6[0x15] — direction change timer
_AI_TIMER2 = 0x58      # piVar6[0x16] — state transition timer
_AI_BAIT_IDX = 0x88    # bait type index, <0 means fish ignores bait
_FISH_PTR = 0x202A2B58 # global Fish pointer
_FISH_AI_COUNT = 6     # max fish AI objects

# Bait radius — instruction at 0x20240364 (lui v0, imm16)
# PNACH writes 0x3C024000 (2.0f) every frame; we overwrite each tick
_BAIT_RADIUS_ADDR = 0x20240364
_LUI_V0 = 0x3C020000
_FISH_RADIUS_FLAG = 0x21F10050
# Progressive radius steps: 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0
_RADIUS_STEPS = [0x4000, 0x4040, 0x4080, 0x40A0, 0x40C0, 0x4100, 0x4140]
_BOOST_INTERVAL = 2.0


def progressive_attract(mem, area, last_boost_time, boost_idx):
    """Progressively increase bait detection radius if no fish is pursuing.
    Returns (updated_time, updated_idx)."""
    cfg = _AREA_CONFIG.get(area)
    if not cfg:
        mem.write_byte(_FISH_RADIUS_FLAG, 0)
        return last_boost_time, boost_idx

    base = cfg['fish_base']
    for i in range(cfg['count']):
        state = _read_state(mem, base + i * FISH_STRIDE + _AI_STATE)
        if state in (6, 7, 8):
            mem.write_byte(_FISH_RADIUS_FLAG, 0)
            return None, 0

    # Write current boost index — PNACH handles the actual radius
    mem.write_byte(_FISH_RADIUS_FLAG, boost_idx)

    now = time.time()
    if last_boost_time is None:
        return now, boost_idx

    if now - last_boost_time < _BOOST_INTERVAL:
        return last_boost_time, boost_idx

    new_idx = min(boost_idx + 1, len(_RADIUS_STEPS) - 1)
    mem.write_byte(_FISH_RADIUS_FLAG, new_idx)
    return now, new_idx


def fish_acquired_flag(mem, fish_id):
    """Set the caught-fish flag for collection tracking."""
    mem.write_byte(FISH_FLAG_BASE + fish_id, 1)


def _read_state(mem, addr):
    """Read fish AI state as signed int32."""
    v = mem.read_int(addr)
    return v if v < 0x80000000 else v - 0x100000000


def instant_bite_tick(mem):
    """Speed up fishing: rush idle fish, but once one is pursuing only help that one."""
    fish_base = mem.read_int(_FISH_PTR)
    if fish_base == 0:
        return
    # First pass: help any fish already pursuing
    for i in range(_FISH_AI_COUNT):
        obj = fish_base + i * FISH_STRIDE
        state = _read_state(mem, obj + _AI_STATE)
        if state in (6, 7):
            # Skip distance check — jump straight to biting
            log.info("Forcing fish %d to bite", i)
            mem.write_int(obj + _AI_STATE, 8)
            mem.write_int(obj + _AI_TIMER2, 0x7FFFFFFF)
            return
        if state == 8:
            # Biting — give infinite time to react
            mem.write_int(obj + _AI_TIMER2, 0x7FFFFFFF)
            return
    # No fish pursuing — rush all idle fish
    for i in range(_FISH_AI_COUNT):
        obj = fish_base + i * FISH_STRIDE
        if _read_state(mem, obj + _AI_STATE) == -1:
            mem.write_int(obj + _AI_TIMER1, 0)
            mem.write_int(obj + _AI_TIMER2, 0)


class FishingState:
    """Tracks fishing quest state for one fishing session."""

    def __init__(self):
        self.initialized = False
        self.fish_array = []
        self.fish_caught = []
        self.quest_active = False
        self.min_size = 0
        self.max_size = 0
        self.has_mardan = False
        self.mardan_mult = 1
        self.cfg = None

    def init_area(self, mem, area, has_mardan=False, mardan_mult=1):
        """Initialize fishing data for the current area."""
        self.cfg = _AREA_CONFIG.get(area)
        if not self.cfg:
            self.initialized = False
            return
        self.has_mardan = has_mardan
        self.mardan_mult = mardan_mult

        c = self.cfg
        self.fish_array = []
        self.fish_caught = []
        a = c['fish_base']
        for i in range(c['count']):
            self.fish_array.append(mem.read_byte(a))
            self.fish_caught.append(False)
            a += FISH_STRIDE

        # Check quest active
        self.quest_active = mem.read_byte(c['active_addr']) == 1
        if self.quest_active:
            self.min_size = mem.read_byte(c['min_size'])
            self.max_size = mem.read_byte(c['max_size'])
            log.info("Fishing quest active (area %d)", area)

        # Mardan sword FP multiplier
        if has_mardan:
            time.sleep(0.3)
            a = c['fp_base']
            for i in range(c['count']):
                fid = self.fish_array[i]
                if fid not in (5, 17):  # Skip Mardan/Baron
                    fp1 = mem.read_int(a)
                    mem.write_int(a, fp1 * mardan_mult)
                    fp2 = mem.read_int(a + 4)
                    mem.write_int(a + 4, fp2 * mardan_mult)
                    a += 8 + FISH_STRIDE - 8  # +4+0x240C
                    log.info("Mardan multiplied FP for fish %d", i)
                else:
                    a += FISH_STRIDE

        self.initialized = True

    def tick(self, mem):
        """Check for caught fish and update quest progress. Call every tick while fishing."""
        if not self.initialized or not self.cfg:
            return

        # Speed up fish AI if instant fishing is enabled
        try:
            if mem.read_byte(addr.OPTION_SAVE_INSTANT_FISH) == 1:
                instant_bite_tick(mem)
        except Exception:
            pass

        c = self.cfg
        a = c['fish_base']
        for i in range(c['count']):
            if (mem.read_byte(a) == 255 and
                    not self.fish_caught[i] and
                    mem.read_byte(CATCH_CHECK) == 12):
                self.fish_caught[i] = True
                fid = self.fish_array[i]
                log.info("Fish caught -> ID: %d", fid)
                fish_acquired_flag(mem, fid)

                if self.quest_active:
                    self._check_quest_progress(mem, a, fid)
            a += FISH_STRIDE

    def _check_quest_progress(self, mem, fish_addr, fish_id):
        """Check if caught fish advances the quest."""
        c = self.cfg
        quest_type = mem.read_byte(c['type_addr'])

        if quest_type == 0:  # Quest type 1: catch N of specific fish
            if fish_id == mem.read_byte(c['id_addr']):
                left = mem.read_byte(c['counter_addr']) - 1
                mem.write_byte(c['counter_addr'], left)
                log.info("Quest progress +1! (%d left)", left)
                if left == 0:
                    log.info("Quest complete!!")
                    mem.write_byte(c['active_addr'], 2)
                    self.quest_active = False
                    if 'complete_count' in c:
                        done = mem.read_byte(c['complete_count'])
                        if done < 4:
                            mem.write_byte(c['complete_count'], done + 1)
        else:  # Quest type 2: catch fish of specific size
            size_addr = fish_addr + 0x60
            size_f = mem.read_float(size_addr) * 10
            size_int = int(math.floor(size_f))
            if self.min_size <= size_int <= self.max_size:
                log.info("Quest complete!! (size %d)", size_int)
                mem.write_byte(c['active_addr'], 2)
                self.quest_active = False
                if 'complete_count' in c:
                    done = mem.read_byte(c['complete_count'])
                    if done < 4:
                        mem.write_byte(c['complete_count'], done + 1)
