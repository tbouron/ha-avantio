"""Shared test setup.

The repository root is the integration package itself. Its __init__.py pulls
in most of Home Assistant, and its calendar.py would shadow the standard
library's `calendar` module if the root were put on sys.path. So instead we
load client.py directly from its file, as the module `avantio_client`.

client.py only uses HomeAssistantError from Home Assistant. If Home Assistant
is not installed, we provide a minimal stand-in so the tests stay lightweight.
"""

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    import homeassistant.exceptions  # noqa: F401
except ImportError:
    ha = types.ModuleType("homeassistant")
    ha_exceptions = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        """Stand-in for homeassistant.exceptions.HomeAssistantError."""

    ha_exceptions.HomeAssistantError = HomeAssistantError
    ha.exceptions = ha_exceptions
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.exceptions"] = ha_exceptions

_spec = importlib.util.spec_from_file_location("avantio_client", REPO_ROOT / "client.py")
avantio_client = importlib.util.module_from_spec(_spec)
sys.modules["avantio_client"] = avantio_client
_spec.loader.exec_module(avantio_client)
