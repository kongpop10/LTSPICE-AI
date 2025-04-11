# ltspice-ai-assistant/settings_manager.py
import json
import os
import streamlit as st # Import Streamlit for potential use or context
from dotenv import load_dotenv
load_dotenv()

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
# Default model to use if not specified in environment or settings
# Using a model that's more likely to be available long-term
DEFAULT_MODEL = "openrouter/anthropic/claude-3-sonnet:beta"

DEFAULT_SETTINGS = {
    "ltspice_path": os.environ.get("LTSPICE_PATH") or r"C:\Program Files\ADI\LTspice\LTspice.exe",
    "llm_model": os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
    "api_url": os.environ.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
    "api_key": os.environ.get("OPENROUTER_API_KEY", "") # Default to empty string for API key
}

def load_settings() -> dict:
    """
    Loads settings from the settings.json file.
    If the file doesn't exist or is invalid, returns default settings.
    """
    settings = DEFAULT_SETTINGS.copy() # Start with defaults
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Update defaults with loaded settings, ensuring all keys are present
                for key in settings:
                    if key in loaded_settings:
                        settings[key] = loaded_settings[key]
            print(f"Loaded settings from {SETTINGS_FILE}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load settings from {SETTINGS_FILE}: {e}. Using defaults.")
            # Ensure defaults are used if loading fails
            settings = DEFAULT_SETTINGS.copy()
    else:
        print(f"Settings file not found ({SETTINGS_FILE}). Using default settings.")
        # Save defaults if the file doesn't exist initially
        save_settings(settings)

    # --- Post-load validation/updates (optional but good practice) ---
    # Ensure API key is loaded from env var if not in file (security)
    # This prioritizes env var for the key if it exists, even if file has an old/empty one
    env_api_key = os.environ.get("OPENROUTER_API_KEY")
    if env_api_key:
        settings["api_key"] = env_api_key
        print("Updated API key from environment variable.")

    # Check if the model is expired and replace it with the default
    if is_model_expired(settings.get('llm_model', '')):
        print(f"Warning: Detected expired model '{settings.get('llm_model')}'. Replacing with default model '{DEFAULT_MODEL}'")
        settings['llm_model'] = DEFAULT_MODEL

    # Validate LTSPICE path after loading
    if not settings.get("ltspice_path") or not os.path.exists(settings["ltspice_path"]):
         print(f"Warning: LTSPICE path '{settings.get('ltspice_path')}' from settings is invalid or not found.")
         # Optionally fall back to default or leave as is for user to fix in UI
         # settings["ltspice_path"] = DEFAULT_SETTINGS["ltspice_path"]

    return settings

def save_settings(settings: dict):
    """Saves the provided settings dictionary to the settings.json file."""
    try:
        # Avoid saving the API key directly if it came from env var for security?
        # Or assume saving is intended by user action. Let's save what's in the state.
        settings_to_save = settings.copy()

        # Check if the model is the expired one and replace it with the default
        if settings_to_save.get('llm_model') == 'openrouter/quasar-alpha':
            print(f"Warning: Detected expired model 'openrouter/quasar-alpha'. Replacing with default model '{DEFAULT_MODEL}'")
            settings_to_save['llm_model'] = DEFAULT_MODEL

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_to_save, f, indent=4)
        print(f"Saved settings to {SETTINGS_FILE}")
    except IOError as e:
        st.error(f"Error saving settings to {SETTINGS_FILE}: {e}")
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")

def is_model_expired(model_name: str) -> bool:
    """Checks if the given model name is known to be expired."""
    expired_models = [
        "openrouter/quasar-alpha"
    ]
    return model_name in expired_models