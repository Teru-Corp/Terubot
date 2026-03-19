# idle_anim.py
# Calm idle gaze + frequent synced blink (eyes only)
# - Works with SerialController that has: send_char(), send_raw_line()
# - Has notify_manual() so idle won't fight your manual commands
# - Designed to run in a background daemon thread

import time
import random
import threading


class IdleAnimator:
    def __init__(
        self,
        eyes_serial,                 # SerialController for EYES only
        blink_min_s: float = 1.2,
        blink_max_s: float = 6.2,
        idle_min_s: float = 2.0,
        idle_max_s: float = 5.0,
        blink_sync_delay_ms: int = 80,
        blink_with_delay: bool = False,
        pause_after_blink_s: float = 0.6,
        weights=(70, 10, 10, 5, 5),  # C, L, R, U, D
    ):
        self.ser = eyes_serial

        # timing
        self.blink_min_s = blink_min_s
        self.blink_max_s = blink_max_s
        self.idle_min_s = idle_min_s
        self.idle_max_s = idle_max_s
        self.pause_after_blink_s = pause_after_blink_s

        self.blink_sync_delay_ms = blink_sync_delay_ms
        self.blink_with_delay = blink_with_delay

        # weighted gaze distribution
        self._pop = ["CENTER", "LEFT", "RIGHT", "UP", "DOWN"]
        self._w = list(weights)

        # toggles
        self.enable_idle = True
        self.enable_blink = True

        # manual override windows
        self._pause_idle_until = 0.0
        self._pause_blink_until = 0.0

        # threading
        self._stop = threading.Event()
        self._lock = threading.Lock()

        self._reset_timers()

    def _reset_timers(self):
        now = time.monotonic()
        self._next_blink = now + random.uniform(self.blink_min_s, self.blink_max_s)
        self._next_idle  = now + random.uniform(self.idle_min_s, self.idle_max_s)

    def set_mode(self, *, idle: bool | None = None, blink: bool | None = None):
        """Enable/disable idle and blink."""
        with self._lock:
            if idle is not None:
                self.enable_idle = idle
            if blink is not None:
                self.enable_blink = blink
            self._reset_timers()

    def pause(self, seconds: float, *, idle: bool = True, blink: bool = False):
        """Temporarily stop idle/blink so manual commands remain visible."""
        until = time.monotonic() + max(0.0, seconds)
        with self._lock:
            if idle:
                self._pause_idle_until = max(self._pause_idle_until, until)
            if blink:
                self._pause_blink_until = max(self._pause_blink_until, until)
            self._reset_timers()

    def notify_manual(self, cmd: str):
        """
        Call this when the user types a command.
        - If user changes gaze: hold it longer (so idle doesn't move immediately)
        - If user changes expression: pause idle a bit (so expression reads)
        - Blink: tiny pause is fine
        """
        s = cmd.strip().upper()
        if not s:
            return

        # if user sends blink like "B" or "B 80"
        if s.startswith("BLINK"):
            self.pause(0.4, idle=True, blink=False)
            return

        # gaze commands (eyes-only)
        if s in ("LEFT", "RIGHT", "UP", "DOWN", "CENTER"):
            self.pause(2.0, idle=True, blink=False)
            return

        # expression commands that affect eyes too (H/S/N/...)
        if s in ("HAPPY", "SAD", "NO", "QUESTION", "YES","LEFT", "RIGHT", "UP", "DOWN", "CENTER"):
            self.pause(6.0, idle=True, blink=False)
            return

        # default
        self.pause(1.0, idle=True, blink=False)

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            now = time.monotonic()

            with self._lock:
                do_idle = self.enable_idle and (now >= self._pause_idle_until)
                do_blink = self.enable_blink and (now >= self._pause_blink_until)

            # --- Blink (synced) ---
            if do_blink and now >= self._next_blink:
                # Many firmwares accept plain BLINK but not parameterized BLINK.
                # Keep parameterized mode optional for setups that need it.
                blink_cmd = (
                    f"BLINK {self.blink_sync_delay_ms}"
                    if self.blink_with_delay
                    else "BLINK"
                )
                self.ser.send_raw_line(blink_cmd)
                # Center gaze to make blink more readable
                self.ser.send_raw_line("CENTER")

                self._next_blink = now + random.uniform(self.blink_min_s, self.blink_max_s)

                # short pause after blink so it doesn't look twitchy
                with self._lock:
                    self._pause_idle_until = max(self._pause_idle_until, now + self.pause_after_blink_s)

            # --- Idle gaze (slow, mostly center) ---
            if do_idle and now >= self._next_idle:
                cmd = random.choices(self._pop, weights=self._w, k=1)[0]
                self.ser.send_raw_line(cmd)
                self._next_idle = now + random.uniform(self.idle_min_s, self.idle_max_s)

            time.sleep(0.01)
