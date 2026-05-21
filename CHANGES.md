# Kokoro Plugin Changes

## 1.0.1 — 2026-05-21

### Fixed
- Settings UI: select/dropdown text was invisible (white-on-white) due to inheriting theme `--color-text` CSS variable. Added explicit foreground (`#111827`) and background (`#ffffff`) colors for `.kokoro-voice-select`, `.field-control select`, `option`, and `optgroup` elements with `color-scheme: light` for native browser dropdowns.

### Changed
- Restored native browser select appearance (`appearance: auto`) for better dropdown usability.
- Select hover states now apply to both `.kokoro-voice-select` and `.field-control select`.

---

# Kokoro Plugin Changes — 2026-04-28

## Problem
Plugin crashed after update with `FileNotFoundError` for malformed blend filename `voices/af_bella_af_nicole_af_sky_bf_emma.pt`.

## Root Cause
Multiple voice IDs were concatenated into one filename. Subprocess temp-script path was fragile. Voice config was never read by the synthesis pipeline.

## Changes Made

### `/a0/usr/plugins/kokoro/extensions/python/message_loop_start/_10_patch_voice.py` (NEW)
- Extension hook that fires at `message_loop_start` before each message loop
- Reads `/a0/usr/plugins/kokoro/config.json`
- Patches `kokoro_tts._voice` and `kokoro_tts._speed` globals
- Resolves `voices/` relative paths to absolute paths under the plugin dir
- **Replaces the need for any external file changes** — fully standalone

### `/a0/usr/plugins/kokoro/api/kokoro_api.py`
- Removed subprocess temp-script path
- Added in-process blend creation using torch and KPipeline directly
- Added voice ID validation (rejects unknown IDs with clear error)
- Added stable hashed blend filenames using SHA1
- Added blend caching (returns existing .pt file if same normalized blend requested)
- Added `delete_blend` API action
- Removed unused `_KOKORO_PYTHON` constant

### `/a0/usr/plugins/kokoro/webui/config.html`
- Added plugin status/verification section with Verify setup button
- Added compact dropdown for selecting cached blends to use
- Added delete buttons on each cached blend tag
- Added `verifySetup()` method that checks readiness on page load
- Added `deleteBlend()` method that calls the delete API
- Shows cached blend count and active voice count

### `/a0/usr/plugins/kokoro/README.md`
- Added blend notes about supported voice IDs and caching
- Added cached response example showing `"cached": true`

### `/a0/usr/plugins/kokoro/requirements.txt` (NEW)
- Plugin-local dependencies: kokoro, torch, soundfile

### `/a0/usr/plugins/kokoro/tests/test_kokoro_api.py` (NEW)
- Tests for blend filename stability
- Tests for voice ID set coverage
- Tests for unknown voice ID rejection

### `/a0/api/synthesize.py`
- **Reverted to original state** — no changes needed
- The extension hook handles voice/speed patching instead

## Principle Upheld
**Zero external file changes.** Everything lives inside `/a0/usr/plugins/kokoro/`.
`/a0/helpers/kokoro_tts.py` was never modified.

## After Restart
1. Open Kokoro settings in the UI
2. Select voices, adjust weights, create blend
3. Click Use on any cached blend
4. Verify setup shows readiness
5. Speech output uses selected voice and speed