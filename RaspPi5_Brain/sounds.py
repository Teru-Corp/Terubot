# sounds.py
import random
import subprocess
from pathlib import Path

class SoundPlayer:
    def __init__(self,
                 sound_dir: str = "/home/terubot/terubot_brain/sounds",
                 device: str = "plughw:2,0"):
        self.sound_dir = Path(sound_dir)
        self.device = device

        # Map command -> list of wav files
        self.map = {
            "HAPPY": ["Happy1.wav"],
            "SAD": ["Sad1.wav"],
            "YES": ["Yes1.wav", "Yes2.wav"],
            "NO": ["No1.wav"],
            "QUESTION": ["Question2.wav"],
            "V": ["VICTOR.wav"],
        }

    def play(self, filename: str):
        """Play a specific wav file (non-blocking)."""
        wav_path = self.sound_dir / filename
        if not wav_path.exists():
            print(f"[SOUND] Missing file: {wav_path}")
            return

        subprocess.Popen(
            ["aplay", "-D", self.device, str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def play_for_cmd(self, cmd: str):
        """Play sound mapped to a command letter (non-blocking)."""
        if not cmd:
            return
        key = cmd.strip().upper()[:1]
        if key not in self.map:
            return
        self.play(random.choice(self.map[key]))

    def set_mapping(self, cmd: str, files: list[str]):
        """Optional: change mapping at runtime."""
        self.map[cmd.strip().upper()[:1]] = files
