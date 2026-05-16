# Kokoro TTS Plugin for Agent Zero

Full control over Kokoro text-to-speech — voice selection, weighted blending, speed adjustment, and language configuration directly from the Agent Zero settings UI.

## Features

- **Voice selection** — choose from 10 built-in voices across American and British English
- **Weighted voice blending** — mix multiple voices with adjustable weights to create custom voice packs
- **Speed control** — adjust speech rate from 0.5× (slow) to 3.0× (fast)
- **Language selection** — configure pronunciation for 9 languages
- **Custom blend persistence** — blended voices are saved as `.pt` files and reused across sessions
- **Settings UI** — integrated into the Agent Zero speech settings panel

## Installation

1. Place the `kokoro` plugin directory under `usr/plugins/kokoro/` in your Agent Zero installation.
2. Install the required Python packages:

```bash
/opt/venv/bin/pip install kokoro torch soundfile
```

> **Note:** Use `/opt/venv/bin/python` (the agent runtime), not `sys.executable` (the framework runtime).

3. Enable the plugin in the Agent Zero UI.
4. Open **Settings → Speech** and click the Kokoro tune icon to configure voices.

### First Use

On first blend creation, the plugin loads voice packs from the [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) model on Hugging Face. This may download model assets automatically. Subsequent blend creations reuse cached data.

## Built-in Voices

| Voice ID | Name | Group |
|----------|------|-------|
| `af_bella` | Bella | American Female |
| `af_nicole` | Nicole | American Female |
| `af_sarah` | Sarah | American Female |
| `af_sky` | Sky | American Female |
| `am_adam` | Adam | American Male |
| `am_michael` | Michael | American Male |
| `bf_emma` | Emma | British Female |
| `bf_isabella` | Isabella | British Female |
| `bm_george` | George | British Male |
| `bm_lewis` | Lewis | British Male |

## Supported Languages

| Code | Language | Extra Dependencies |
|------|----------|-------------------|
| `a` | American English | — |
| `b` | British English | — |
| `e` | Spanish | — |
| `f` | French | — |
| `h` | Hindi | — |
| `i` | Italian | — |
| `j` | Japanese | `pyopenjtalk`, `fugashi`, `unidic-lite` |
| `p` | Brazilian Portuguese | — |
| `z` | Mandarin Chinese | — |

## Configuration

Settings are stored in `config.json` (auto-generated on first use) and can be changed from the plugin settings UI.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `voice` | string | `af_nicole,bf_emma` | Voice ID, comma-separated IDs, or `voices/<blend>.pt` |
| `speed` | float | `1.3` | Speech rate multiplier (0.5–3.0) |
| `lang_code` | string | `a` | Language code for pronunciation |

### Default Configuration

```yaml
# default_config.yaml
voice: "af_nicole,bf_emma"
speed: 1.3
lang_code: "a"
```

## Voice Blending

1. Open **Settings → Speech** and click the Kokoro settings button (tune icon)
2. Adjust the **weight slider** (0–10) for each voice to control the blend ratio
3. Click **Create blend & activate** to compute and save a weighted voice pack
4. The new blend is saved to `voices/` and automatically set as the active voice

Blend files are named by constituent voices with a content hash:

```
voices/af_nicole_bf_emma_<hash>.pt
```

### Generated Blend Files

- Blend `.pt` files are **user-generated local data** — they are not distributed with the plugin.
- They are excluded from version control via `.gitignore`.
- Each user creates their own blends through the settings UI.

## API Endpoint

The plugin exposes a single API endpoint at `POST /api/plugins/kokoro/kokoro_api`.

### Actions

| Action | Description |
|--------|-------------|
| `list_voices` | Returns all built-in voice metadata |
| `create_blend` | Creates or returns a cached weighted blend |
| `list_blends` | Lists all saved blend files |
| `delete_blend` | Deletes a saved blend file |
| `set_active_voice` | Sets the active voice and patches runtime immediately |
| `get_status` | Returns current voice, speed, language, and blend status |

### Example: Create Blend

```json
{
  "action": "create_blend",
  "voices": [
    { "id": "af_nicole", "weight": 0.6 },
    { "id": "bf_emma", "weight": 0.4 }
  ]
}
```

Response:
```json
{ "success": true, "blend_file": "voices/af_nicole_bf_emma_<hash>.pt" }
```

## How It Works

Synthesis is handled by the core Agent Zero pipeline:

1. **Frontend** sends text to `/api/synthesize`
2. **Core** calls `helpers/kokoro_tts.py`
3. **Extension hook** (`message_loop_start`) patches `kokoro_tts` globals from plugin config before each message
4. Voice paths ending in `.pt` are resolved to tensor files from the `voices/` directory
5. The Kokoro KPipeline generates audio

The plugin handles only voice listing, blend creation, and config patching — not synthesis itself.

## Plugin Structure

```
usr/plugins/kokoro/
├── plugin.yaml              # Plugin manifest
├── hooks.py                 # Install/uninstall lifecycle hooks
├── default_config.yaml      # Default settings
├── LICENSE                  # MIT license
├── .gitignore               # Excludes generated artifacts
├── README.md                # This file
├── api/
│   └── kokoro_api.py        # Backend API (voice listing, blend CRUD)
├── extensions/
│   ├── python/
│   │   └── message_loop_start/
│   │       └── _10_patch_voice.py  # Patches kokoro_tts from config
│   └── webui/
│       └── kokoro-settings/
│           └── settings-btn.html   # Settings button injection
├── webui/
│   └── config.html          # Settings UI component
├── tests/
│   └── test_kokoro_api.py   # Unit tests
└── voices/                  # User-generated blend .pt files (gitignored)
    └── .gitkeep
```

## Installation

1. Place the `kokoro` directory under `usr/plugins/` in your Agent Zero installation
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   Or install individually:

   ```bash
   pip install kokoro torch soundfile
   ```

3. Restart Agent Zero
4. Enable the plugin in the Agent Zero UI
5. Open **Settings → Speech** to configure voices and blending

### First-Use Model Download

On first use, Kokoro automatically downloads the `Kokoro-82M` model from [Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M). This is a one-time download (~330 MB) handled by the Kokoro library — no manual steps required.

**Offline environments:** Pre-download the model before deploying:

```python
from kokoro import KPipeline
KPipeline(lang_code='a')  # triggers download
```

### Additional Language Support

English voices work out of the box. Some languages require extra packages:

```bash
pip install pyopenjtalk fugashi unidic-lite  # Japanese
```

See the [Supported Languages](#supported-languages) table for all available language codes.

## Dependencies

| Package | Purpose |
|---------|----------|
| `kokoro` | TTS synthesis engine (KPipeline) |
| `torch` | Tensor operations for voice blending |
| `soundfile` | WAV audio encoding |

**No pinned minimum versions** — this plugin tracks the latest stable releases.

## Data & Storage

### What Gets Generated Locally

| File/Dir | Purpose | Git-Tracked |
|----------|---------|:-----------|
| `config.json` | User settings (voice, speed, language) | No — gitignored |
| `.toggle-*` | Plugin enabled/disabled state | No — gitignored |
| `voices/*.pt` | Custom voice blend files | No — gitignored |
| `voices/.gitkeep` | Ensures `voices/` directory exists in git | Yes |

**Voice blends are user-generated local data.** They are never distributed with the plugin and are excluded from version control via `.gitignore`.

### How Voice Blends Work

1. The API computes a weighted average of the selected voice tensors
2. The result is saved as a `.pt` file in `voices/`
3. The filename is a stable hash of the voice IDs (e.g., `voices/af_nicole_bf_emma.pt`)
4. Requesting the same blend again returns the cached file — no recomputation

Blend files are portable within the same plugin version but are not guaranteed compatible across versions.

## Security & Path Hygiene

- **Path traversal prevention:** Voice file resolution enforces containment under the `voices/` directory. Paths containing `..` are rejected
- **Voice ID validation:** Only the 10 built-in voice IDs are accepted for blending. Unknown IDs are rejected with a clear error message
- **No synthesis in plugin API:** The plugin handles voice listing and blend creation only. Speech synthesis runs through the core Agent Zero pipeline
- **Config isolation:** User settings in `config.json` are local and never leave the machine
- **No secrets stored:** The plugin stores no API keys, tokens, or credentials

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes — follow existing code style
4. Add or update tests in `tests/` for any API changes
5. Update this README if you change user-facing behavior
6. Commit with a clear message (`git commit -m 'Add new feature')
7. Open a pull request

### Development Notes

- **Plugin scope:** All code lives under `usr/plugins/kokoro/`. No Agent Zero core file modifications needed
- **Extension hooks:** Voice/speed patching is handled by `extensions/python/message_loop_start/_10_patch_voice.py`, which runs before each message loop
- **Testing:** Run `pytest tests/` from the plugin directory
- **API changes:** Update `api/kokoro_api.py` and `tests/test_kokoro_api.py` together

## License

MIT License. See [LICENSE](LICENSE).

## Changelog

See [CHANGES.md](CHANGES.md) for detailed change history.
