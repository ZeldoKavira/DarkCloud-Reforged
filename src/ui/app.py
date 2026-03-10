"""Main application window with detailed mod status dashboard."""

import logging
import tkinter as tk
from tkinter import ttk
from game.game_state import GameState, GameSnapshot
from mods.manager import ModManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Colors
BG = "#1a1a2e"
BG_PANEL = "#16213e"
FG = "#e0e0e0"
FG_DIM = "#888888"
ACCENT = "#0f3460"
GREEN = "#4ecca3"
ORANGE = "#f0a500"
RED = "#e74c3c"
BLUE = "#3498db"


class App:
    def __init__(self, state: GameState):
        self.state = state
        self.manager = ModManager(state.mem, state)

        self.root = tk.Tk()
        self.root.title("Dark Cloud Reforged")
        self.root.geometry("720x620")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG, foreground=FG, font=("Helvetica", 10))
        style.configure("Header.TLabel", background=BG, foreground=FG, font=("Helvetica", 14, "bold"))
        style.configure("Sub.TLabel", background=BG_PANEL, foreground=FG, font=("Helvetica", 10))
        style.configure("Dim.TLabel", background=BG_PANEL, foreground=FG_DIM, font=("Helvetica", 9))
        style.configure("Status.TLabel", background=BG, foreground=GREEN, font=("Helvetica", 11, "bold"))

        self._build_ui()
        self.state.on_update(self._on_state_update)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Header (fixed at top)
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(header, text="Dark Cloud Reforged", style="Header.TLabel").pack(side=tk.LEFT)
        self.status_dot = tk.Label(header, text="●", font=("Helvetica", 16), bg=BG, fg=RED)
        self.status_dot.pack(side=tk.RIGHT, padx=5)
        self.status_label = ttk.Label(header, text="Connecting...", style="Status.TLabel")
        self.status_label.pack(side=tk.RIGHT)

        # Scrollable container for everything else
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas)

        self._scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel scrolling
        def _on_mousewheel(event):
            if event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5 or event.delta < 0:
                canvas.yview_scroll(3, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        # Make scroll frame expand to canvas width
        def _on_canvas_resize(event):
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        sf = self._scroll_frame  # shorthand

        # Main content — two columns
        content = ttk.Frame(sf)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        # Left column
        left = ttk.Frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.conn_panel = self._panel(left, "Connection")
        self.conn_fields = self._add_fields(self.conn_panel, [
            "PCSX2", "PINE Status", "Game ID", "DC1 Detected",
        ])

        self.game_panel = self._panel(left, "Game State")
        self.game_fields = self._add_fields(self.game_panel, [
            "Mode", "Sub Mode", "Session Timer", "In-Game Timer", "Frame Counter",
        ])

        self.flags_panel = self._panel(left, "Mod Flags")
        self.flags_fields = self._add_fields(self.flags_panel, [
            "PNACH", "Mod Flag", "Enhanced Save", "Cheats Used", "Game Beaten",
        ])

        # Right column
        right = ttk.Frame(content)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.player_panel = self._panel(right, "Player")
        self.player_fields = self._add_fields(self.player_panel, [
            "Character", "Gilda", "Allies", "Position", "Godmode",
        ])

        self.loc_panel = self._panel(right, "Location")
        self.loc_fields = self._add_fields(self.loc_panel, [
            "Area", "Floor", "Dungeon Mode", "Back Floor", "Paused", "Cleared", "Limit Zone",
            "Time of Day", "Day", "House ID",
        ])

        self.mod_panel = self._panel(right, "Mod Subsystems")
        self.mod_fields = self._add_fields(self.mod_panel, [
            "Town Thread", "Dungeon Thread", "Weapon Effects", "Shop Prices", "Weapon Balance",
        ])

        # Options row — interactive checkboxes
        self.opt_panel = self._panel(sf, "Options")
        self.opt_checks = self._add_checkboxes(self.opt_panel, [
            "Disable Beep", "Disable Battle Music", "Widescreen",
            "Graphics Enhance", "Disable Attack Sounds", "Mute All Music",
            "Instant Fishing", "Disable Dungeon Limited Zones", "Disable Bad Magic Circles",
            "Repair Powder is Automatic", "Disable Character Doors",
            "Start with Map", "Start with Magical Crystal",
        ])

        # Overlay toggles
        self.overlay_panel = self._panel(sf, "Overlays")
        self.overlay_checks = self._add_checkboxes(self.overlay_panel, [
            "Fishing Overlay", "Attachment Stats Overlay", "Georama Overlay",
        ])
        # Init from settings
        from core.settings import get as get_setting
        _OVL_MAP = {
            "Fishing Overlay": "overlay_fishing",
            "Attachment Stats Overlay": "overlay_attachments",
            "Georama Overlay": "overlay_georama",
        }
        for label, key in _OVL_MAP.items():
            val = get_setting(key)
            self.overlay_checks[label][0].set(bool(val))
            self.overlay_checks[label][1].config(state=tk.NORMAL)
            self.overlay_checks[label][1].config(
                command=lambda l=label, v=self.overlay_checks[label][0]: self._on_overlay_toggle(l, v.get()))

        # Log area (fixed at bottom, outside scroll)
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        ttk.Label(log_frame, text="Log", style="Header.TLabel").pack(anchor=tk.W)
        self.log_text = tk.Text(
            log_frame, height=6, bg="#0d1117", fg="#8b949e",
            font=("Courier", 9), state=tk.DISABLED, wrap=tk.WORD,
            borderwidth=1, relief=tk.SOLID,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Hook logging to the text widget
        self._log_handler = TextHandler(self.log_text, self.root)
        logging.getLogger().addHandler(self._log_handler)

    def _panel(self, parent, title):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(frame, text=title, background=ACCENT, foreground=FG,
                  font=("Helvetica", 10, "bold"), padding=(8, 3)).pack(fill=tk.X)
        inner = ttk.Frame(frame, style="Panel.TFrame")
        inner.pack(fill=tk.X, padx=8, pady=4)
        return inner

    def _add_fields(self, parent, labels):
        fields = {}
        for label in labels:
            row = ttk.Frame(parent, style="Panel.TFrame")
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label, style="Dim.TLabel", width=18, anchor=tk.W).pack(side=tk.LEFT)
            val = ttk.Label(row, text="—", style="Sub.TLabel", anchor=tk.W)
            val.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fields[label] = val
        return fields

    def _add_checkboxes(self, parent, labels):
        from game import addresses as addr
        checks = {}
        for label in labels:
            var = tk.BooleanVar()
            cb = tk.Checkbutton(
                parent, text=label, variable=var, bg=BG_PANEL, fg=FG,
                selectcolor=ACCENT, activebackground=BG_PANEL, activeforeground=FG,
                font=("Helvetica", 10), anchor=tk.W, state=tk.DISABLED,
                disabledforeground=FG_DIM,
                command=lambda l=label, v=var: self._on_option_toggle(l, v.get()),
            )
            cb.pack(fill=tk.X, pady=1)
            checks[label] = (var, cb)
        return checks

    def _on_overlay_toggle(self, label, checked):
        from core.settings import set as set_setting
        _OVL_MAP = {
            "Fishing Overlay": "overlay_fishing",
            "Attachment Stats Overlay": "overlay_attachments",
            "Georama Overlay": "overlay_georama",
        }
        key = _OVL_MAP.get(label)
        if key:
            set_setting(key, checked)

    def _on_option_toggle(self, label, checked):
        from game import addresses as addr
        mem = self.state.mem
        val = 1 if checked else 0
        if label == "Disable Beep":
            mem.write_byte(addr.OPTION_BEEP, val)
            mem.write_byte(addr.OPTION_SAVE_BEEP, val)
        elif label == "Disable Battle Music":
            mem.write_byte(addr.OPTION_BATTLE_MUSIC, val)
            mem.write_byte(addr.OPTION_SAVE_BATTLE_MUSIC, val)
        elif label == "Widescreen":
            mem.write_byte(addr.OPTION_WIDESCREEN, val)
            mem.write_byte(addr.OPTION_SAVE_WIDESCREEN, val)
        elif label == "Graphics Enhance":
            mem.write_byte(addr.OPTION_GRAPHICS, val)
            mem.write_byte(addr.OPTION_SAVE_GRAPHICS, val)
        elif label == "Disable Attack Sounds":
            mem.write_byte(addr.OPTION_SAVE_ATTACK_SOUNDS, val)
            for i, a in enumerate(addr.ATTACK_SOUND_ADDRS):
                mem.write_byte(a, 0 if checked else addr.ATTACK_SOUND_DEFAULTS[i])
        elif label == "Mute All Music":
            mem.write_byte(addr.OPTION_SAVE_MUTE_MUSIC, val)
            mem.write_short(addr.MUSIC_VOLUME_ADDR, 0 if checked else addr.MUSIC_VOLUME_DEFAULT)
            if checked:
                # Muting all music also forces battle music off (matches C#)
                mem.write_byte(addr.OPTION_BATTLE_MUSIC, 1)
                mem.write_byte(addr.OPTION_SAVE_BATTLE_MUSIC, 1)
                self.opt_checks["Disable Battle Music"][0].set(True)
        elif label == "Instant Fishing":
            mem.write_byte(addr.OPTION_SAVE_INSTANT_FISH, val)
        elif label == "Disable Dungeon Limited Zones":
            mem.write_byte(addr.OPTION_SAVE_NO_LIMIT_ZONES, val)
        elif label == "Disable Bad Magic Circles":
            mem.write_byte(addr.OPTION_SAVE_GOOD_CIRCLES, val)
        elif label == "Repair Powder is Automatic":
            mem.write_byte(addr.OPTION_SAVE_REPAIR_FALLBACK, val)
        elif label == "Disable Character Doors":
            mem.write_byte(addr.OPTION_SAVE_NO_CHARA_DOORS, val)
        elif label == "Start with Map":
            mem.write_byte(addr.OPTION_SAVE_START_MAP, val)
        elif label == "Start with Magical Crystal":
            mem.write_byte(addr.OPTION_SAVE_START_MC, val)

    def _on_state_update(self, snap: GameSnapshot):
        """Called from poll thread — schedule UI update on main thread."""
        self.root.after(0, self._update_ui, snap)

    def _update_ui(self, snap: GameSnapshot):
        # Status bar
        if not snap.connected:
            self.status_label.config(text=snap.error or "Disconnected")
            self.status_dot.config(fg=RED)
        elif not snap.dc1_detected:
            self.status_label.config(text=snap.error or "Waiting for Dark Cloud")
            self.status_dot.config(fg=ORANGE)
        elif snap.game_mode in (0, 1):
            self.status_label.config(text=snap.game_mode_name)
            self.status_dot.config(fg=ORANGE)
        else:
            self.status_label.config(text=snap.game_mode_name)
            self.status_dot.config(fg=GREEN)

        # Connection
        emu_names = {0: "Running", 1: "Paused", 2: "Shutdown"}
        self._set(self.conn_fields, "PCSX2", "Connected" if snap.connected else "Disconnected",
                  GREEN if snap.connected else RED)
        self._set(self.conn_fields, "PINE Status", emu_names.get(snap.emu_status, "?"),
                  GREEN if snap.emu_status == 0 else ORANGE)
        self._set(self.conn_fields, "DC1 Detected", "Yes" if snap.dc1_detected else "No",
                  GREEN if snap.dc1_detected else RED)
        self._set(self.conn_fields, "Game ID", snap.error if snap.error else "SCUS-97111")

        # Game state
        self._set(self.game_fields, "Mode", f"{snap.game_mode} — {snap.game_mode_name}")
        sub_names = {9: "Save File Select"}
        self._set(self.game_fields, "Sub Mode", sub_names.get(snap.sub_mode, str(snap.sub_mode)))
        self._set(self.game_fields, "Session Timer", str(snap.session_timer))
        self._set(self.game_fields, "In-Game Timer", str(snap.ingame_timer))
        self._set(self.game_fields, "Frame Counter", str(snap.frame_counter))

        # Flags
        self._set_bool(self.flags_fields, "PNACH", snap.flags.pnach_active)
        self._set_bool(self.flags_fields, "Mod Flag", snap.flags.mod_active)
        self._set_bool(self.flags_fields, "Enhanced Save", snap.flags.enhanced_save)
        self._set_bool(self.flags_fields, "Cheats Used", snap.flags.cheats_used)
        self._set_bool(self.flags_fields, "Game Beaten", snap.flags.game_beaten)

        # Player
        p = snap.player
        self._set(self.player_fields, "Character", f"{p.character_name} ({p.character_id})")
        self._set(self.player_fields, "Gilda", str(p.gilda))
        self._set(self.player_fields, "Allies", str(p.ally_count))
        self._set(self.player_fields, "Position", f"{p.pos_x:.1f}, {p.pos_y:.1f}, {p.pos_z:.1f}")
        self._set_bool(self.player_fields, "Godmode", p.godmode)

        # Location
        if snap.game_mode == 2:  # Town
            t = snap.town
            self._set(self.loc_fields, "Area", t.area_name)
            self._set(self.loc_fields, "Floor", "—")
            self._set(self.loc_fields, "Dungeon Mode", "—")
            self._set(self.loc_fields, "Back Floor", "—")
            self._set(self.loc_fields, "Paused", "Yes" if t.mode == 9 else "No")
            self._set(self.loc_fields, "Cleared", "—")
            self._set(self.loc_fields, "Time of Day", str(t.time_of_day))
            self._set(self.loc_fields, "Day", str(t.current_day))
            self._set(self.loc_fields, "House ID", str(t.building_id))
        elif snap.game_mode == 3:  # Dungeon
            d = snap.dungeon
            self._set(self.loc_fields, "Area", d.dungeon_name)
            self._set(self.loc_fields, "Floor", f"B{d.floor}" if d.in_floor else "Lobby")
            dun_modes = {1: "Walking", 2: "Menu", 3: "Door", 5: "Ally Select", 7: "Next Floor"}
            self._set(self.loc_fields, "Dungeon Mode", dun_modes.get(d.mode, str(d.mode)))
            self._set_bool(self.loc_fields, "Back Floor", d.back_floor)
            self._set_bool(self.loc_fields, "Paused", d.is_paused)
            self._set_bool(self.loc_fields, "Cleared", d.is_cleared)
            lz = d.limit_zone
            if lz == -1 or lz == 0xFFFFFFFF:
                self._set(self.loc_fields, "Limit Zone", "None", FG_DIM)
            else:
                self._set(self.loc_fields, "Limit Zone", str(lz), RED)
            self._set(self.loc_fields, "Time of Day", "—")
            self._set(self.loc_fields, "Day", "—")
            self._set(self.loc_fields, "House ID", "—")
        else:
            for key in self.loc_fields:
                self._set(self.loc_fields, key, "—")

        # Mod subsystems
        ms = snap.mod_status
        self._set_active(self.mod_fields, "Town Thread", ms.town_thread)
        self._set_active(self.mod_fields, "Dungeon Thread", ms.dungeon_thread)
        self._set_active(self.mod_fields, "Weapon Effects", ms.weapons_thread)
        self._set_active(self.mod_fields, "Shop Prices", ms.shop_applied, is_oneshot=True)
        self._set_active(self.mod_fields, "Weapon Balance", ms.weapon_balance_applied, is_oneshot=True)

        # Options — sync checkboxes from memory (don't trigger callbacks)
        in_game = snap.game_mode in (2, 3)
        for _, (_, cb) in self.opt_checks.items():
            cb.config(state=tk.NORMAL if in_game else tk.DISABLED)
        self._sync_check("Disable Beep", snap.flags.option_beep)
        self._sync_check("Disable Battle Music", snap.flags.option_battle_music)
        self._sync_check("Widescreen", snap.flags.option_widescreen)
        self._sync_check("Graphics Enhance", snap.flags.option_graphics)
        self._sync_check("Disable Attack Sounds", snap.flags.option_attack_sounds)
        self._sync_check("Mute All Music", snap.flags.option_mute_music)
        self._sync_check("Instant Fishing", snap.flags.option_instant_fish)
        self._sync_check("Disable Dungeon Limited Zones", snap.flags.option_no_limit_zones)
        self._sync_check("Disable Bad Magic Circles", snap.flags.option_good_circles)
        self._sync_check("Repair Powder is Automatic", snap.flags.option_repair_fallback)

    def _set(self, fields, key, text, color=FG):
        if key in fields:
            fields[key].config(text=text, foreground=color)

    def _set_bool(self, fields, key, val):
        self._set(fields, key, "Yes" if val else "No", GREEN if val else FG_DIM)

    def _set_active(self, fields, key, val, is_oneshot=False):
        if is_oneshot:
            self._set(fields, key, "Applied" if val else "Pending", GREEN if val else ORANGE)
        else:
            self._set(fields, key, "Running" if val else "Stopped", GREEN if val else FG_DIM)

    def _sync_check(self, key, val):
        if key in self.opt_checks:
            self.opt_checks[key][0].set(val)

    def _on_close(self):
        self.manager.stop_nowait()
        self.state.mem.disconnect()
        self.root.destroy()

    def run(self):
        from ui.overlay import start_overlay
        start_overlay(self.root)
        self.manager.start()
        self.root.mainloop()


class TextHandler(logging.Handler):
    """Routes log messages to a tkinter Text widget."""

    def __init__(self, widget, root):
        super().__init__()
        self.widget = widget
        self.root = root
        self.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record):
        msg = self.format(record) + "\n"
        try:
            self.root.after(0, self._append, msg)
        except Exception:
            pass

    def _append(self, msg):
        self.widget.config(state=tk.NORMAL)
        self.widget.insert(tk.END, msg)
        self.widget.see(tk.END)
        # Keep last 200 lines
        lines = int(self.widget.index("end-1c").split(".")[0])
        if lines > 200:
            self.widget.delete("1.0", f"{lines - 200}.0")
        self.widget.config(state=tk.DISABLED)
