"""
Plugin lifecycle hooks for the kokoro plugin.

Agent Zero calls install() when the plugin is enabled and
uninstall() when it is disabled or removed.
"""

import os


def install():
    """Ensure voices directory and .gitkeep exist on install."""
    voices_dir = os.path.join(os.path.dirname(__file__), "voices")
    os.makedirs(voices_dir, exist_ok=True)

    gitkeep = os.path.join(voices_dir, ".gitkeep")
    if not os.path.exists(gitkeep):
        open(gitkeep, "a").close()

    print("Kokoro voices directory initialized")


def uninstall():
    """Optional cleanup on uninstall.
    Note: We intentionally do not remove the voices directory to preserve user custom voices."""
    print("Kokoro plugin uninstalled (voices directory preserved)")