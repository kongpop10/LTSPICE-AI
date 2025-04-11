# config.py
# This file previously handled loading configuration from environment variables.
# Configuration is now managed via settings_manager.py and initialized in app.py using Streamlit's session state.
# Default values are defined in settings_manager.DEFAULT_SETTINGS.

# import os
# import sys

# API_KEY = os.environ.get("OPENROUTER_API_KEY")
# LTSPICE_EXECUTABLE = os.environ.get("LTSPICE_PATH") or r"C:\Program Files\ADI\LTspice\LTspice.exe"
# OPENROUTER_MODEL = "openrouter/quasar-alpha"
# OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
