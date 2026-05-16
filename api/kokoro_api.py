"""Kokoro TTS API - voice listing and blend creation."""
import os
import json
from pathlib import Path
from hashlib import sha1
from helpers.api import ApiHandler, Request, Response

_VOICES_DIR = Path(__file__).parent.parent / "voices"
_PLUGIN_DIR = Path(__file__).parent.parent
_CONFIG_PATH = _PLUGIN_DIR / "config.json"

ALL_VOICES = [
    {"id": "af_bella", "label": "Bella", "group": "American Female"},
    {"id": "af_nicole", "label": "Nicole", "group": "American Female"},
    {"id": "af_sarah", "label": "Sarah", "group": "American Female"},
    {"id": "af_sky", "label": "Sky", "group": "American Female"},
    {"id": "am_adam", "label": "Adam", "group": "American Male"},
    {"id": "am_michael", "label": "Michael", "group": "American Male"},
    {"id": "bf_emma", "label": "Emma", "group": "British Female"},
    {"id": "bf_isabella", "label": "Isabella", "group": "British Female"},
    {"id": "bm_george", "label": "George", "group": "British Male"},
    {"id": "bm_lewis", "label": "Lewis", "group": "British Male"},
]

VOICE_IDS = {v["id"] for v in ALL_VOICES}


def _validate_voices_path(filename):
    """Validate and resolve a blend filename to a safe path within voices/.

    Rejects:
      - empty filenames
      - absolute paths (leading /)
      - path traversal (.. components)
      - hidden files (leading dot in any component)
      - null bytes
      - non-.pt extensions
      - paths that resolve outside _VOICES_DIR

    Returns resolved Path inside _VOICES_DIR on success.
    Raises ValueError on any validation failure.
    """
    if not filename or not filename.strip():
        raise ValueError("Empty filename")

    # Strip optional voices/ prefix
    cleaned = filename.replace("voices/", "", 1) if filename.startswith("voices/") else filename

    if not cleaned:
        raise ValueError("Empty filename after stripping voices/ prefix")

    # Reject null bytes
    if "\x00" in cleaned:
        raise ValueError("Invalid filename: contains null byte")

    # Reject absolute paths
    if cleaned.startswith("/"):
        raise ValueError(f"Absolute path not allowed: {filename}")

    # Reject path traversal using Path parts
    parts = Path(cleaned).parts
    if ".." in parts:
        raise ValueError(f"Path traversal not allowed: {filename}")

    # Reject hidden files (any component starting with dot)
    if any(part.startswith(".") for part in parts):
        raise ValueError(f"Hidden file not allowed: {filename}")

    # Must end with .pt
    if not cleaned.endswith(".pt"):
        raise ValueError(f"Only .pt files allowed: {filename}")

    # Resolve and verify containment within _VOICES_DIR
    resolved = (_VOICES_DIR / cleaned).resolve()
    voices_resolved = _VOICES_DIR.resolve()
    # Verify the resolved path starts with voices_resolved
    resolved_str = str(resolved)
    voices_str = str(voices_resolved)
    if resolved_str != voices_str and not resolved_str.startswith(voices_str + os.sep):
        raise ValueError(f"Path escapes voices directory: {filename}")

    return resolved


def _validate_voice_ref(voice):
    """Validate a voice reference for set_active_voice / get_status.

    Accepts:
      - Built-in voice IDs (e.g. "af_bella")
      - voices/<file>.pt paths for blend files

    Rejects:
      - Empty strings
      - Unknown voice IDs
      - Invalid voices/ paths (traversal, non-.pt, hidden, nonexistent)
      - Absolute paths

    Returns:
      - Built-in voice ID string for built-in voices
      - Resolved absolute Path for voices/ references

    Raises ValueError on any validation failure.
    """
    if not voice:
        raise ValueError("No voice specified")

    # Built-in voice ID
    if voice in VOICE_IDS:
        return voice

    # voices/ path reference
    if voice.startswith("voices/"):
        # Validate the path portion using the shared helper
        safe_path = _validate_voices_path(voice)

        # Check existence
        if not safe_path.exists():
            raise ValueError(f"Voice file not found: {voice}")

        return safe_path

    # Neither built-in nor voices/ path
    raise ValueError(f"Unknown voice: {voice}")


def _blend_filename(voices):
    payload = json.dumps(
        [{"id": v["id"], "weight": float(v["weight"])} for v in voices],
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = sha1(payload.encode("utf-8")).hexdigest()[:12]
    return "_".join(v["id"] for v in voices) + "_" + digest + ".pt"


class KokoroApi(ApiHandler):
    async def process(self, input, request):
        action = input.get("action", "")
        if action == "list_voices":
            return {"voices": ALL_VOICES}
        if action == "create_blend":
            return self._create_blend(input)
        if action == "list_blends":
            return self._list_blends()
        if action == "delete_blend":
            return self._delete_blend(input)
        if action == "set_active_voice":
            return self._set_active_voice(input)
        if action == "get_status":
            return self._get_status()
        return Response(status=400, response="Unknown action")

    def _create_blend(self, input):
        voices = input.get("voices", [])
        if not voices:
            return {"success": False, "error": "No voices"}
        unknown = [v.get("id") for v in voices if v.get("id") not in VOICE_IDS]
        if unknown:
            return {
                "success": False,
                "error": "Unknown voice id(s): " + ", ".join(sorted(set(map(str, unknown))))
            }
        total = sum(float(v.get("weight", 1)) for v in voices)
        if total <= 0:
            return {"success": False, "error": "Blend weights must sum to a positive value"}
        normalized = []
        for v in voices:
            normalized.append({"id": v["id"], "weight": float(v.get("weight", 1)) / total})
        try:
            os.makedirs(_VOICES_DIR, exist_ok=True)
            blend_name = _blend_filename(normalized)
            blend_path = _VOICES_DIR / blend_name
            if blend_path.exists():
                return {"success": True, "blend_file": "voices/" + blend_path.name, "cached": True}
            try:
                import torch
                from kokoro import KPipeline

                pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
                blend = None
                for v in normalized:
                    pack = pipeline.load_single_voice(v['id'])
                    if blend is None:
                        blend = v['weight'] * pack
                    else:
                        blend = blend + v['weight'] * pack

                torch.save(blend, str(blend_path))
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": (
                        "A required voice pack could not be found. "
                        "Check that the requested voice .pt files exist in /a0/usr/plugins/kokoro/voices/."
                    )
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
            return {"success": True, "blend_file": "voices/" + blend_path.name, "cached": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _delete_blend(self, input):
        filename = input.get("filename", "")
        if not filename:
            return {"success": False, "error": "No filename specified"}
        try:
            path = _validate_voices_path(filename)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        if not path.exists():
            return {"success": False, "error": "Blend file not found"}
        try:
            path.unlink()
            return {"success": True, "deleted": filename}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_blends(self):
        blends = []
        if _VOICES_DIR.exists():
            for f in _VOICES_DIR.glob("*.pt"):
                blends.append("voices/" + f.name)
        return {"blends": blends}

    def _set_active_voice(self, input):
        """Set the active voice in config.json and patch kokoro_tts globals immediately."""
        voice = input.get("voice", "")
        if not voice:
            return {"success": False, "error": "No voice specified"}

        # Validate voice reference
        try:
            validated = _validate_voice_ref(voice)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        # Load current config
        cfg = {}
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH) as f:
                cfg = json.load(f)

        # Determine absolute voice path for patching
        if isinstance(validated, Path):
            abs_voice = str(validated)
        else:
            abs_voice = validated

        # Save to config
        cfg["voice"] = voice
        with open(_CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)

        # Patch kokoro_tts globals immediately (no restart needed)
        try:
            import helpers.kokoro_tts as kokoro_tts
            kokoro_tts._voice = abs_voice
        except Exception:
            pass

        return {"success": True, "voice": voice, "active": abs_voice}

    def _get_status(self):
        """Return plugin status: active voice, speed, available blends, voice file health."""
        cfg = {}
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH) as f:
                cfg = json.load(f)

        voice = cfg.get("voice", "")
        speed = cfg.get("speed", 1.0)
        lang_code = cfg.get("lang_code", "a")

        # Validate voice reference safely
        voice_ok = False
        if voice:
            try:
                _validate_voice_ref(voice)
                voice_ok = True
            except ValueError:
                voice_ok = False

        # Resolve absolute path for live state reporting
        abs_voice = voice
        if voice.startswith("voices/"):
            try:
                safe = _validate_voices_path(voice)
                abs_voice = str(safe)
            except ValueError:
                abs_voice = voice

        # List blends
        blends = []
        if _VOICES_DIR.exists():
            blends = ["voices/" + f.name for f in _VOICES_DIR.glob("*.pt")]

        # Get live kokoro_tts state
        live_voice = None
        try:
            import helpers.kokoro_tts as kokoro_tts
            live_voice = getattr(kokoro_tts, "_voice", None)
        except Exception:
            pass

        return {
            "config_voice": voice,
            "live_voice": live_voice,
            "voice_ok": voice_ok,
            "speed": speed,
            "lang_code": lang_code,
            "blends": blends,
            "blend_count": len(blends),
        }
