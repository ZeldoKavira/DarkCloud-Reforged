"""Base class for all mod modules."""

import logging
import threading
from core.memory import Memory
from game.game_state import GameSnapshot

log = logging.getLogger(__name__)


class ModBase:
    """Base class for mod subsystems. Each mod runs on its own thread."""

    name = "unnamed"

    def __init__(self, mem: Memory):
        self.mem = mem
        self._thread = None
        self._running = False
        self._applied = False

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def applied(self):
        return self._applied

    def start(self):
        if self.active:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_wrapper, daemon=True, name=self.name)
        self._thread.start()
        log.info("%s started", self.name)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        log.info("%s stopped", self.name)

    def _run_wrapper(self):
        try:
            self.run()
        except Exception as e:
            log.error("%s crashed: %s", self.name, e)
        finally:
            self._running = False

    def run(self):
        """Override in subclass. Called on the mod's thread."""
        raise NotImplementedError

    def apply_once(self):
        """Override for one-time modifications (e.g., shop prices). Called from main thread."""
        self._applied = True
