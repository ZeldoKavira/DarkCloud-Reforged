"""Game state tracker. Polls memory and maintains a snapshot of current state.
Equivalent to MainMenuThread.cs logic.
"""

import logging
import time
from dataclasses import dataclass, field
from core.memory import Memory
from game import addresses as addr

log = logging.getLogger(__name__)


@dataclass
class PlayerInfo:
    character_id: int = 0
    character_name: str = "Toan"
    gilda: int = 0
    hp: int = 0
    ally_count: int = 0
    pos_x: float = 0.0
    pos_y: float = 0.0
    pos_z: float = 0.0
    animation_id: int = 0
    godmode: bool = False


@dataclass
class DungeonInfo:
    dungeon_id: int = 0
    dungeon_name: str = ""
    floor: int = 0
    in_floor: bool = False
    mode: int = 0  # 1=Walking, 2=Menu, 3=Door, 5=Ally select, 7=Next floor
    is_paused: bool = False
    is_cleared: bool = False
    back_floor: bool = False


@dataclass
class TownInfo:
    area_id: int = 0
    area_name: str = ""
    mode: int = 0
    building_id: int = 0
    is_inside: bool = False
    camera: int = 0
    time_of_day: int = 0
    current_day: int = 0


@dataclass
class ModFlags:
    pnach_active: bool = False
    mod_active: bool = False
    enhanced_save: bool = False
    cheats_used: bool = False
    game_beaten: bool = False
    option_beep: bool = False
    option_battle_music: bool = False
    option_widescreen: bool = False
    option_graphics: bool = False


@dataclass
class ModStatus:
    """Status of each mod subsystem thread."""
    town_thread: bool = False
    dungeon_thread: bool = False
    weapons_thread: bool = False
    shop_applied: bool = False
    weapon_balance_applied: bool = False
    side_quests_active: bool = False
    custom_chests_active: bool = False
    custom_effects_active: bool = False
    dialogues_loaded: bool = False
    enemies_modified: bool = False


@dataclass
class GameSnapshot:
    """Complete snapshot of game state at a point in time."""
    connected: bool = False
    emu_status: int = 2  # 0=Running, 1=Paused, 2=Shutdown
    dc1_detected: bool = False
    game_mode: int = 0
    game_mode_name: str = "Unknown"
    sub_mode: int = 0
    session_timer: int = 0
    ingame_timer: int = 0
    player: PlayerInfo = field(default_factory=PlayerInfo)
    dungeon: DungeonInfo = field(default_factory=DungeonInfo)
    town: TownInfo = field(default_factory=TownInfo)
    flags: ModFlags = field(default_factory=ModFlags)
    mod_status: ModStatus = field(default_factory=ModStatus)
    frame_counter: int = 0
    prev_frame_counter: int = 0
    error: str = ""


MODE_NAMES = {
    0: "Main Title", 1: "Intro", 2: "Town", 3: "Dungeon",
    4: "Unknown (4)", 5: "Cutscene", 7: "Debug Menu",
}


class GameState:
    """Continuously polls PCSX2 memory and builds GameSnapshot."""

    def __init__(self, mem: Memory):
        self.mem = mem
        self.snapshot = GameSnapshot()
        self._callbacks = []

    def on_update(self, cb):
        """Register a callback for state changes."""
        self._callbacks.append(cb)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb(self.snapshot)
            except Exception as e:
                log.error("Callback error: %s", e)

    def poll(self):
        """Single poll cycle. Updates snapshot and notifies listeners."""
        snap = self.snapshot

        # Connection check
        if not self.mem.connected:
            if not self.mem.connect():
                snap.connected = False
                snap.error = "PCSX2 not found — is PINE/IPC enabled?"
                self._notify()
                return
        snap.connected = True
        snap.error = ""

        try:
            self._poll_core(snap)
        except Exception as e:
            log.debug("Poll error: %s", e)
            self.mem.disconnect()
            snap.connected = False
            snap.error = f"Connection lost: {e}"

        self._notify()

    def _poll_core(self, snap: GameSnapshot):
        mem = self.mem

        # Emulator status
        snap.emu_status = mem.status()
        if snap.emu_status == 2:
            snap.dc1_detected = False
            snap.error = "No game running"
            return

        # DC1 detection
        dc1_check = mem.read_int(addr.DC1_CHECK)
        snap.dc1_detected = (dc1_check == addr.DC1_MAGIC)
        if not snap.dc1_detected:
            snap.error = "Dark Cloud not detected"
            return

        # Frame counter (for save state detection)
        snap.prev_frame_counter = snap.frame_counter
        snap.frame_counter = mem.read_int(addr.SESSION_TIMER)

        # Game mode
        snap.game_mode = mem.read_byte(addr.MODE)
        snap.game_mode_name = MODE_NAMES.get(snap.game_mode, f"Unknown ({snap.game_mode})")
        snap.sub_mode = mem.read_byte(addr.SUB_MODE)
        snap.session_timer = mem.read_int(addr.SESSION_TIMER)
        snap.ingame_timer = mem.read_int(addr.INGAME_TIMER)

        # Mod flags
        snap.flags.pnach_active = mem.read_byte(addr.PNACH_FLAG) == 1
        snap.flags.mod_active = mem.read_byte(addr.MOD_FLAG) == 1
        snap.flags.enhanced_save = mem.read_byte(addr.ENHANCED_MOD_SAVE_FLAG) == 1
        snap.flags.cheats_used = mem.read_byte(addr.CHEATS_USED_FLAG) == 1
        snap.flags.game_beaten = mem.read_byte(addr.GAME_BEATEN_FLAG) == 1
        snap.flags.option_beep = mem.read_byte(addr.OPTION_BEEP) == 1
        snap.flags.option_battle_music = mem.read_byte(addr.OPTION_BATTLE_MUSIC) == 1
        snap.flags.option_widescreen = mem.read_byte(addr.OPTION_WIDESCREEN) == 1
        snap.flags.option_graphics = mem.read_byte(addr.OPTION_GRAPHICS) == 1

        # Player info
        char_id = mem.read_byte(addr.CURRENT_CHARACTER)
        snap.player.character_id = char_id
        snap.player.character_name = addr.CHARACTER_NAMES.get(char_id, "Unknown")
        snap.player.gilda = mem.read_short(addr.GILDA)
        snap.player.ally_count = mem.read_byte(addr.ALLY_COUNT)
        snap.player.animation_id = mem.read_int(addr.ANIMATION_ID)
        snap.player.godmode = mem.read_int(addr.ULTRAMAN) != 0

        # Position depends on mode
        if snap.game_mode == addr.Mode.DUNGEON:
            snap.player.pos_x = mem.read_float(addr.DUN_POS_X)
            snap.player.pos_y = mem.read_float(addr.DUN_POS_Y)
            snap.player.pos_z = mem.read_float(addr.DUN_POS_Z)
        else:
            snap.player.pos_x = mem.read_float(addr.TOWN_POS_X)
            snap.player.pos_y = mem.read_float(addr.TOWN_POS_Y)
            snap.player.pos_z = mem.read_float(addr.TOWN_POS_Z)

        # Town info
        if snap.game_mode == addr.Mode.TOWN:
            snap.town.area_id = mem.read_byte(addr.TOWN_AREA)
            snap.town.area_name = addr.TOWN_NAMES.get(snap.town.area_id, f"Area {snap.town.area_id}")
            snap.town.mode = mem.read_short(addr.TOWN_MODE)
            snap.town.building_id = mem.read_int(addr.TOWN_BUILDING)
            snap.town.is_inside = mem.read_byte(addr.TOWN_INSIDE) == 1
            snap.town.camera = mem.read_short(addr.TOWN_CAMERA)
            snap.town.time_of_day = mem.read_int(addr.TIME_OF_DAY_READ)
            snap.town.current_day = mem.read_int(addr.CURRENT_DAY)

        # Dungeon info
        if snap.game_mode == addr.Mode.DUNGEON:
            snap.dungeon.dungeon_id = mem.read_byte(addr.DUNGEON_ID)
            snap.dungeon.dungeon_name = addr.DUNGEON_NAMES.get(
                snap.dungeon.dungeon_id, f"Dungeon {snap.dungeon.dungeon_id}")
            snap.dungeon.floor = mem.read_byte(addr.DUNGEON_FLOOR)
            snap.dungeon.in_floor = mem.read_byte(addr.DUNGEON_FLOOR_CHECK) != 255
            snap.dungeon.mode = mem.read_byte(addr.DUNGEON_MODE)
            snap.dungeon.back_floor = mem.read_byte(addr.BACK_FLOOR_FLAG) != 0
            snap.dungeon.is_cleared = mem.read_int(addr.DUNGEON_CLEAR) == 4294967281
            # Pause check
            pause_title = mem.read_byte(addr.DUN_PAUSE_TITLE)
            pause_player = mem.read_byte(addr.DUN_PAUSE_PLAYER)
            pause_enemy = mem.read_byte(addr.DUN_PAUSE_ENEMY)
            snap.dungeon.is_paused = (pause_title == 1 and pause_player == 1 and pause_enemy == 1)
