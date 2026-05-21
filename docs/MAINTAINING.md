# Maintaining the Kokoro Plugin

This guide covers the development and publishing workflow for maintainers of the Kokoro Agent Zero plugin.

## Repository

- **GitHub**: https://github.com/twilso24/kokoro-a0-plugin
- **Plugin Index**: Submitted to [agent0ai/a0-plugins](https://github.com/agent0ai/a0-plugins)

## Development Workflow

### 1. Make changes locally

Edit plugin files in the cloned repository. Key locations:

| Path | Purpose |
|---|---|
| `plugin.yaml` | Plugin manifest and version |
| `api/kokoro_api.py` | Backend API handlers |
| `webui/config.html` | Settings UI (HTML + Alpine.js + CSS) |
| `hooks.py` | Plugin lifecycle hooks |
| `tests/test_kokoro_api.py` | Test suite |
| `CHANGES.md` | Changelog |
| `README.md` | User documentation |

### 2. Verify locally

```bash
# Syntax check all Python files
python -m py_compile api/kokoro_api.py hooks.py tests/test_kokoro_api.py

# Run tests (requires pytest)
python -m pytest tests/test_kokoro_api.py -v

# Validate plugin.yaml
python -c "import yaml; yaml.safe_load(open('plugin.yaml'))"

# Check settings UI manually in Agent Zero light and dark themes
```

### 3. Version bump

Update `version` in `plugin.yaml` following semantic versioning:

- **Patch** (`1.0.0` → `1.0.1`): Bug fixes, no API change
- **Minor** (`1.0.0` → `1.1.0`): New features, backward compatible
- **Major** (`1.0.0` → `2.0.0`): Breaking changes

### 4. Update changelog

Add an entry to `CHANGES.md` in the format:

```markdown
## X.Y.Z — YYYY-MM-DD

### Fixed
- Description of bug fix

### Added
- Description of new feature

### Changed
- Description of change
```

## Publishing via MCP2CLI (from Agent Zero)

When working inside Agent Zero without direct git credentials, use MCP2CLI with the configured GitHub MCP server to publish changes.

### Prerequisites

- The `github` MCP server is configured in Agent Zero settings (stdio: `npx -y @modelcontextprotocol/server-github`)
- A GitHub Personal Access Token with repo write access is set in the server's env
- `uvx` is available (installed via `uv`)

### Step 1: Verify changes locally

```bash
cd /a0/usr/workdir/kokoro-a0-plugin
python -m py_compile api/kokoro_api.py hooks.py tests/test_kokoro_api.py
```

### Step 2: Inspect what changed

```bash
git diff --stat
```

### Step 3: Publish via MCP2CLI

Use `uvx mcp2cli` with the GitHub MCP server config:

```bash
# Build the MCP2CLI command from settings
python - <<'PY'
import json, shlex
from pathlib import Path
raw = json.loads(Path('/a0/usr/settings.json').read_text())
m = raw.get('mcp_servers', {})
if isinstance(m, str): m = json.loads(m)
cfg = m['mcpServers']['github']
parts = ['uvx', 'mcp2cli']
cmd = [cfg['command']] + cfg.get('args', [])
parts += ['--mcp-stdio', ' '.join(shlex.quote(x) for x in cmd)]
for k, v in cfg.get('env', {}).items():
    parts += ['--env', f'{k}={v}']
print(' '.join(shlex.quote(x) for x in parts))
PY > /tmp/mcp_github_cmd.sh

# Prepare push payload
python - <<'PY'
import json
from pathlib import Path
payload = {
    "owner": "twilso24",
    "repo": "kokoro-a0-plugin",
    "branch": "main",
    "message": "chore: describe your change",
    "files": [
        {"path": "plugin.yaml", "content": Path("plugin.yaml").read_text()},
        {"path": "CHANGES.md", "content": Path("CHANGES.md").read_text()}
        # Add other changed files as needed
    ]
}
Path('/tmp/push_payload.json').write_text(json.dumps(payload))
PY

# Push
bash -lc "$(cat /tmp/mcp_github_cmd.sh) --pretty push-files --stdin < /tmp/push_payload.json"
```

### Step 4: Verify remote

```bash
git fetch origin main --quiet
git show origin/main:<changed-file> > /tmp/remote_check
# Compare with local
diff <changed-file> /tmp/remote_check
```

## Release Checklist

For every release:

- [ ] `plugin.yaml` version bumped
- [ ] `CHANGES.md` entry added
- [ ] Python syntax checks pass
- [ ] Tests pass (when pytest available)
- [ ] Settings UI verified in light and dark themes
- [ ] Published to GitHub via MCP2CLI
- [ ] Remote content verified

## CI

GitHub Actions CI runs on push and PR to `main`. It validates:

- `plugin.yaml` is valid YAML
- Python files compile without syntax errors
- Test suite passes
- Required repo files exist

## Troubleshooting

### MCP2CLI not found

Install via the mcp2cli plugin's Initialize action, or:
```bash
pip install mcp2cli
```

### Push fails with auth error

Check that `GITHUB_PERSONAL_ACCESS_TOKEN` is set in the GitHub MCP server's env config in `/a0/usr/settings.json`.

### Local git divergence

If local commits diverge from remote (e.g., MCP2CLI created a different commit), the local clone may show `ahead 1, behind 1`. This is cosmetic — MCP2CLI publishes file contents independently of local git history.
