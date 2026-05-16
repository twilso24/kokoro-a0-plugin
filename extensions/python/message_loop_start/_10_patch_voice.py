"""
Kokoro voice config patcher.

Reads the Kokoro plugin config and patches kokoro_tts globals
before each message loop, so synthesis uses the correct voice/speed.
"""
from __future__ import annotations

import json
from pathlib import Path

from helpers.extension import Extension

PLUGIN_DIR = Path(__file__).resolve().parent.parent.parent.parent


class KokoroPatchVoice(Extension):
    async def execute(self, loop_data=None, **kwargs):
        """Patch kokoro_tts globals from plugin config."""
        config_path = PLUGIN_DIR / "config.json"
        if not config_path.exists():
            return

        with open(config_path) as f:
            cfg = json.load(f)

        import helpers.kokoro_tts as kokoro_tts

        if "voice" in cfg:
            voice = cfg["voice"]
            if voice.startswith("voices/"):
                voice = str(PLUGIN_DIR / voice)
            kokoro_tts._voice = voice

        if "speed" in cfg:
            kokoro_tts._speed = float(cfg["speed"])
