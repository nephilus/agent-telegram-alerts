"""Shared configuration-home resolution for the generic CLI and legacy alias."""
import os
from pathlib import Path


HOME_ENV = "TELEGRAM_ALERTS_HOME"
LEGACY_HOME_ENV = "JCODE_HOME"


def home_path():
    """Resolve one writable home for every CLI alias, with legacy env precedence."""
    for name in (HOME_ENV, LEGACY_HOME_ENV):
        value = os.environ.get(name)
        if value:
            return Path(value).expanduser()
    return Path.home() / ".config" / "telegram-alerts"


def legacy_read_home():
    """Return the old default home only when no explicit home was selected."""
    if os.environ.get(HOME_ENV) or os.environ.get(LEGACY_HOME_ENV):
        return None
    legacy = Path.home() / ".jcode"
    return None if legacy == home_path() else legacy
