"""Dark Cloud Enhanced Mod - Python Edition
Entry point. Launches the mod window and connects to PCSX2 via PINE IPC.
"""

import sys
import threading
from core.pine_ipc import PineIPC
from core.memory import Memory
from game.game_state import GameState
from ui.app import App


def main():
    from mods.ruby_tex import load_textures
    load_textures()

    ipc = PineIPC()
    mem = Memory(ipc)
    state = GameState(mem)

    app = App(state)
    app.run()


if __name__ == "__main__":
    main()
