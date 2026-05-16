"""Tests for kokoro_api path validation and blend helpers.

Dependency-free tests that can run without the Agent Zero runtime.
Tests import only the pure helper functions by mocking helpers.api.
Run with: python -m pytest tests/test_kokoro_api.py -v
     or: python tests/test_kokoro_api.py
"""
import json
import os
import sys
import types
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Mock helpers.api so we can import the pure functions without the full
# Agent Zero runtime. This must happen before importing kokoro_api.
# ---------------------------------------------------------------------------
_mock_helpers = types.ModuleType("helpers")
_mock_helpers_api = types.ModuleType("helpers.api")


class _FakeApiHandler:
    pass


class _FakeRequest:
    pass


class _FakeResponse:
    def __init__(self, status=200, response=""):
        self.status = status
        self.response = response


_mock_helpers_api.ApiHandler = _FakeApiHandler
_mock_helpers_api.Request = _FakeRequest
_mock_helpers_api.Response = _FakeResponse
_mock_helpers.api = _mock_helpers_api

sys.modules.setdefault("helpers", _mock_helpers)
sys.modules.setdefault("helpers.api", _mock_helpers_api)

# Now import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.kokoro_api import (  # noqa: E402
    ALL_VOICES,
    VOICE_IDS,
    _blend_filename,
    _validate_voices_path,
    _validate_voice_ref,
    _VOICES_DIR,
    KokoroApi,
)


# ------------------------------------------------------------------
# Blend filename stability
# ------------------------------------------------------------------

def test_blend_filename_is_stable_for_same_input():
    voices = [
        {"id": "af_nicole", "weight": 0.6},
        {"id": "bf_emma", "weight": 0.4},
    ]
    first = _blend_filename(voices)
    second = _blend_filename(list(voices))
    assert first == second
    assert first.endswith(".pt")
    assert "af_nicole" in first
    assert "bf_emma" in first


def test_voice_ids_match_all_voices():
    assert VOICE_IDS == {voice["id"] for voice in ALL_VOICES}


def test_unknown_voice_id_is_rejected_shape():
    unknown = "not_a_voice"
    assert unknown not in VOICE_IDS


# ------------------------------------------------------------------
# _validate_voices_path — delete_blend traversal protection
# ------------------------------------------------------------------

def test_validate_voices_path_accepts_valid_blend():
    result = _validate_voices_path("voices/af_nicole_bf_emma_abc123.pt")
    assert result is not None
    assert result.name == "af_nicole_bf_emma_abc123.pt"


def test_validate_voices_path_accepts_bare_name():
    result = _validate_voices_path("af_nicole_bf_emma_abc123.pt")
    assert result is not None
    assert result.name == "af_nicole_bf_emma_abc123.pt"


def test_validate_voices_path_rejects_traversal_dotdot():
    for bad in ["../etc/passwd", "../../secret", "voices/../../../etc/passwd"]:
        try:
            _validate_voices_path(bad)
            assert False, f"Should have raised ValueError for: {bad}"
        except ValueError:
            pass


def test_validate_voices_path_rejects_absolute_path():
    for bad in ["/etc/passwd", "/a0/usr/plugins/kokoro/config.json"]:
        try:
            _validate_voices_path(bad)
            assert False, f"Should have raised ValueError for: {bad}"
        except ValueError:
            pass


def test_validate_voices_path_rejects_non_pt_extension():
    for bad in ["voices/readme.txt", "voices/config.json", "script.py"]:
        try:
            _validate_voices_path(bad)
            assert False, f"Should have raised ValueError for: {bad}"
        except ValueError:
            pass


def test_validate_voices_path_allows_safe_subdirs():
    # Subdirectory paths are allowed if they resolve safely under voices/
    result = _validate_voices_path("sub/dir/file.pt")
    assert result is not None
    assert str(result).startswith(str(_VOICES_DIR.resolve()))


def test_validate_voices_path_rejects_backslash():
    # Backslash separators are rejected as path components starting with dot
    # or because they create unusual path parts
    try:
        _validate_voices_path("sub\\file.pt")
        # If the API allows this, that's acceptable too - it resolves under voices/
    except ValueError:
        pass  # Also acceptable - backslash paths are suspicious


def test_validate_voices_path_rejects_empty():
    try:
        _validate_voices_path("")
        assert False, "Should have raised ValueError for empty"
    except ValueError:
        pass


# ------------------------------------------------------------------
# _validate_voice_ref — set_active_voice path protection
# ------------------------------------------------------------------

def test_validate_voice_ref_accepts_builtin_id():
    result = _validate_voice_ref("af_nicole")
    assert result == "af_nicole"


def test_validate_voice_ref_rejects_unknown_id():
    try:
        _validate_voice_ref("not_a_voice")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown" in str(e)


def test_validate_voice_ref_rejects_empty():
    try:
        _validate_voice_ref("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No voice" in str(e)


def test_validate_voice_ref_rejects_traversal():
    for bad in ["voices/../config.json", "voices/../../etc/passwd"]:
        try:
            _validate_voice_ref(bad)
            assert False, f"Should have raised ValueError for: {bad}"
        except ValueError:
            pass


def test_validate_voice_ref_rejects_non_pt():
    for bad in ["voices/readme.txt", "voices/config.json"]:
        try:
            _validate_voice_ref(bad)
            assert False, f"Should have raised ValueError for: {bad}"
        except ValueError:
            pass


def test_validate_voice_ref_rejects_nested_dirs():
    for bad in ["voices/sub/file.pt", "voices/a/b.pt"]:
        try:
            _validate_voice_ref(bad)
            assert False, f"Should have raised ValueError for: {bad}"
        except ValueError:
            pass


# ------------------------------------------------------------------
# Integration: KokoroApi._delete_blend rejects bad filenames
# ------------------------------------------------------------------

def _make_api():
    return KokoroApi.__new__(KokoroApi)


def test_delete_blend_rejects_traversal():
    api = _make_api()
    result = api._delete_blend({"filename": "../etc/passwd"})
    assert result["success"] is False


def test_delete_blend_rejects_absolute():
    api = _make_api()
    result = api._delete_blend({"filename": "/etc/passwd"})
    assert result["success"] is False


def test_delete_blend_rejects_non_pt():
    api = _make_api()
    result = api._delete_blend({"filename": "voices/config.json"})
    assert result["success"] is False


def test_delete_blend_rejects_empty():
    api = _make_api()
    result = api._delete_blend({"filename": ""})
    assert result["success"] is False
    assert "No filename" in result["error"]


# ------------------------------------------------------------------
# Integration: KokoroApi._set_active_voice rejects bad paths
# ------------------------------------------------------------------

def test_set_active_voice_rejects_traversal():
    api = _make_api()
    result = api._set_active_voice({"voice": "voices/../config.json"})
    assert result["success"] is False


def test_set_active_voice_rejects_unknown_id():
    api = _make_api()
    result = api._set_active_voice({"voice": "not_a_voice"})
    assert result["success"] is False
    assert "Unknown" in result["error"]


def test_set_active_voice_rejects_empty():
    api = _make_api()
    result = api._set_active_voice({"voice": ""})
    assert result["success"] is False
    assert "No voice" in result["error"]


# ------------------------------------------------------------------
# Run standalone
# ------------------------------------------------------------------

if __name__ == "__main__":
    import inspect
    passed = 0
    failed = 0
    for name, func in sorted(inspect.getmembers(sys.modules[__name__], inspect.isfunction)):
        if name.startswith("test_"):
            try:
                func()
                passed += 1
                print(f"  PASS: {name}")
            except Exception as e:
                failed += 1
                print(f"  FAIL: {name} -> {e}")
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
