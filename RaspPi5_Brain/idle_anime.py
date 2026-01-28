# idle_anim.py
import time
import random

class IdleAnimator:
    def __init__(
        self,
        serial_ctrl,
        blink_min_s=2.5,
        blink_max_s=4.0,
        idle_min_s=0.6,
        idle_max_s=1.4,
        blink_sync_delay_ms=80
    ):
        self.ser = serial_ctrl

        self.blink_min_s = blink_min_s
        self.blink_max_s = blink_max_s
        self.idle_min_s = idle_min_s
        self.idle_max_s = idle_max_s
        self.blink_sync_delay_ms = blink_sync_delay_ms

        self.gaze_states = ["C", "L", "R", "U", "D"]

        now = time.monotonic()
        self.next_blink = now + random.uniform(self.blink_min_s, self.blink_max_s)
        self.next_idle  = now + random.uniform(self.idle_min_s, self.idle_max_s)

    def reset(self):
        """Call when switching modes so timing feels natural."""
        now = time.monotonic()
        self.next_blink = now + random.uniform(self.blink_min_s, self.blink_max_s)
        self.next_idle  = now + random.uniform(self.idle_min_s, self.idle_max_s)

    def update(self, enable_blink=True, enable_idle=True):
        """Call frequently (e.g. every 10–20ms) from main loop."""
        now = time.monotonic()

        if enable_blink and now >= self.next_blink:
            # scheduled blink for better sync between two ESPs
            self.ser.send(f"B {self.blink_sync_delay_ms}")
            self.next_blink = now + random.uniform(self.blink_min_s, self.blink_max_s)

        if enable_idle and now >= self.next_idle:
            cmd = random.choice(self.gaze_states)
            self.ser.send(cmd)
            self.next_idle = now + random.uniform(self.idle_min_s, self.idle_max_s)
