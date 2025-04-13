# app.py
import streamlit as st
import asyncio
import re
import os
import platform  # May need this if file_utils needs refinement based on app context
import pandas as pd
import altair as alt # Add altair import
# Remove direct config import, use settings manager instead
# from config import API_KEY, LTSPICE_EXECUTABLE, OPENROUTER_MODEL, OPENROUTER_API_BASE
from settings_manager import load_settings, save_settings, is_model_expired, DEFAULT_MODEL # Import settings manager functions

# Import new functions and prompts
from llm_interface import get_llm_response, extract_spice_netlist, is_model_expired_message, extract_model_expired_message, get_alternative_models # Will be refactored later
from prompts import NETLIST_GENERATION_PROMPT_TEMPLATE, NETLIST_MODIFICATION_PROMPT_TEMPLATE, ADD_SIMULATION_PROMPT_TEMPLATE
from ltspice_runner import run_ltspice_simulation, cleanup_simulation_files # Will be refactored later
from file_utils import open_file_with_default_app, get_file_path_from_upload, find_file_in_directory, select_directory_dialog
from raw_parser import parse_raw_file
# Use the fixed netlist parser
from netlist_parser_fixed import extract_plot_directives

# --- Constants ---
# Use absolute path to the root-level saved_circuits directory
SAVED_CIRCUITS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_circuits")

# --- Initialize Session State ---
# Configuration Settings (Load once at the start)
if 'config' not in st.session_state:
    st.session_state['config'] = load_settings()

# Other session state variables
INITIAL_NETLIST = "* Enter circuit description above and click Generate/Update\n*\n* Example: A 5V source V1 across 1k resistor R1\n\n.end"
EMPTY_NETLIST = "" # Empty string for cleared state
if 'current_netlist' not in st.session_state:
    st.session_state['current_netlist'] = INITIAL_NETLIST
if 'user_input' not in st.session_state:
     st.session_state['user_input'] = "" # Initialize user input state
if 'last_sim_status' not in st.session_state:
    st.session_state['last_sim_status'] = None
if 'last_log_file' not in st.session_state:
    st.session_state['last_log_file'] = None
if 'last_raw_file' not in st.session_state:
    st.session_state['last_raw_file'] = None
if 'last_sim_temp_dir' not in st.session_state:
    st.session_state['last_sim_temp_dir'] = None
if 'llm_raw_response' not in st.session_state:
    st.session_state['llm_raw_response'] = None
if 'ai_summary_message' not in st.session_state:
    st.session_state['ai_summary_message'] = None

if 'need_sidebar_refresh' not in st.session_state:
    st.session_state['need_sidebar_refresh'] = False

# Plot-related session state variables
if 'plot_data' not in st.session_state:
    st.session_state['plot_data'] = None
if 'available_variables' not in st.session_state:
    st.session_state['available_variables'] = None
if 'selected_variables' not in st.session_state:
    st.session_state['selected_variables'] = []
if 'plot_directive_nodes' not in st.session_state:
    st.session_state['plot_directive_nodes'] = []
if 'log_x_axis' not in st.session_state:
    st.session_state['log_x_axis'] = False
if 'log_y_axis' not in st.session_state:
    st.session_state['log_y_axis'] = False

st.set_page_config(
    page_title="LTSpice AI",
    page_icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABEUlEQVR4nO2aLQoCURRGvxnEFVgEs7oAcQMWrdrMug7L7MJgg1CQIwoDBBYwWmz/RibMHDYIgWn0nzHfae+UeDjxueVF9vHqoxMS0AI0D0AII0DkAL0DgALUDjALQAjQPQAjQOQAvQOAAtQOMAtACNA9ACNA5AC9A4AC1A4wwC0AI0D0AI0DkAL0FRCDjvPh2pP1x93g05Dk35TktRt1ZRdCknSYnfTNrv/33SlogF+kx1zpMZf0CjRK9kHnl/4JOAAtQOMAtABN0C1QrcTazHrv8+FaKFmeeQip8EfmXWMlxAFqAxgFoARoHoAVoHIAWoHEAWoDGAWgBGgegBWgcgBagcQBagMYBaAEaB6AFaByAFqB5AuFRHu2vKsDAAAAAAElFTkSuQmCC",
    layout="wide"
)
st.title("LTPSICE AI Assistant ⚡️")

# --- Sidebar ---

# --- Settings Expander ---
# Define callback to save settings
def save_current_settings():
    # Update session state from widgets before saving
    # Note: Streamlit usually updates session state bound to widget keys automatically on change.
    # Explicit update might be needed if keys don't match state structure directly.
    # Assuming widget keys directly update st.session_state.config items.
    if 'config' in st.session_state:
        save_settings(st.session_state.config)
        st.toast("Settings saved!", icon="⚙️")

with st.sidebar.expander("⚙️ Settings", expanded=False):
    st.session_state.config['ltspice_path'] = st.text_input(
        "LTSPICE Path:",
        value=st.session_state.config.get('ltspice_path', ''),
        key="config_ltspice_path", # Use key to potentially access widget state if needed
        on_change=save_current_settings,
        help="Full path to the LTspice executable (e.g., LTspice.exe)."
    )
    # Check if the current model is expired
    current_model = st.session_state.config.get('llm_model', '')
    model_expired = is_model_expired(current_model)

    # Show a warning if the model is expired
    if model_expired:
        st.warning(f"⚠️ The model '{current_model}' is no longer available. Please select a different model.")
        # Show alternative models
        with st.expander("Suggested Alternative Models"):
            st.write("Please update your model to one of these alternatives:")
            for model in get_alternative_models():
                st.code(model, language="text")

        # Use the default model as the value
        model_value = DEFAULT_MODEL
    else:
        model_value = current_model

    st.session_state.config['llm_model'] = st.text_input(
        "LLM Model:",
        value=model_value,
        key="config_llm_model",
        on_change=save_current_settings,
        help="Identifier for the LLM model to use (e.g., openrouter/anthropic/claude-3-sonnet:beta)."
    )
    st.session_state.config['api_url'] = st.text_input(
        "API Base URL:",
        value=st.session_state.config.get('api_url', ''),
        key="config_api_url",
        on_change=save_current_settings,
        help="The base URL for the LLM API endpoint."
    )
    st.session_state.config['api_key'] = st.text_input(
        "API Key:",
        value=st.session_state.config.get('api_key', ''),
        key="config_api_key",
        type="password",
        on_change=save_current_settings,
        help="Your API key for the LLM service."
    )

    # --- Status Indicators ---

    # Check LTSPICE Path
    ltspice_path_valid = st.session_state.config.get('ltspice_path') and os.path.isfile(st.session_state.config['ltspice_path'])
    if not ltspice_path_valid:
        st.error(f"LTSPICE path invalid or not found: `{st.session_state.config.get('ltspice_path', 'Not Set')}`")

    # Check API Key
    if not st.session_state.config.get('api_key'):
        st.warning("API Key is not set.")

    # Check API URL
    if not st.session_state.config.get('api_url'):
        st.warning("API URL is not set.")

    # Check Model
    if not st.session_state.config.get('llm_model'):
        st.warning("LLM Model is not set.")


st.sidebar.title("Output & Actions")

# --- Load Netlist from File (Sidebar) ---
with st.sidebar.container():
    st.subheader("Load Netlist")
    # Store the previous uploaded file name to detect changes
    previous_file_name = st.session_state.get('previous_uploaded_file_name', None)

    # Use a callback function to handle file upload changes
    def on_file_upload_change():
        if 'netlist_file_uploader' in st.session_state and st.session_state['netlist_file_uploader'] is not None:
            uploaded_file = st.session_state['netlist_file_uploader']
            current_file_name = uploaded_file.name

            # Check if this is a new file upload (different from previous)
            if current_file_name != st.session_state.get('previous_uploaded_file_name', None):
                try:
                    # Read the content of the uploaded file
                    netlist_content = uploaded_file.getvalue().decode("utf-8")

                    # Update the current netlist in the session state
                    st.session_state['current_netlist'] = netlist_content

                    # Store the current file name for future comparison
                    st.session_state['previous_uploaded_file_name'] = current_file_name

                    # Store the original file path if available
                    file_path, file_name = get_file_path_from_upload(uploaded_file)

                    # If we couldn't get the file path directly, try to find it in the workspace
                    if file_path is None and file_name:
                        # Try to find the file in the workspace
                        found_path = find_file_in_directory(file_name)
                        if found_path:
                            file_path = found_path
                            print(f"Found file in workspace: {file_path}")
                            # Store a flag to show a success message about finding the file
                            st.session_state['file_found_in_workspace'] = True
                            st.session_state['found_file_path'] = file_path

                    st.session_state['original_file_path'] = file_path
                    st.session_state['original_file_name'] = file_name

                    # Show success message (will appear after rerun)
                    st.session_state['file_load_success'] = True
                    st.session_state['loaded_file_name'] = current_file_name

                    # Flag for rerun
                    st.session_state['need_rerun_after_file_load'] = True
                except Exception as e:
                    st.session_state['file_load_error'] = str(e)

    # File uploader with on_change callback
    uploaded_file = st.file_uploader(
        "Upload a netlist file (.net, .cir)",
        type=["net", "cir", "txt"],
        key="netlist_file_uploader",
        on_change=on_file_upload_change
    )

    # Display success message if file was loaded
    if st.session_state.get('file_load_success', False):
        st.success(f"Loaded netlist from {st.session_state.get('loaded_file_name', '')}")
        st.toast(f"Loaded {st.session_state.get('loaded_file_name', '')}", icon="📂")
        # Clear the flag to avoid showing the message again
        st.session_state['file_load_success'] = False

    # Display message if file was found in workspace
    if st.session_state.get('file_found_in_workspace', False):
        found_path = st.session_state.get('found_file_path', '')
        if found_path:
            st.success(f"Found original file in workspace: {found_path}")
            st.toast(f"Found file location", icon="🔍")
        # Clear the flag to avoid showing the message again
        st.session_state['file_found_in_workspace'] = False

    # Display error message if there was an error
    if 'file_load_error' in st.session_state and st.session_state['file_load_error']:
        st.error(f"Error loading netlist: {st.session_state['file_load_error']}")
        # Clear the error message
        st.session_state['file_load_error'] = None

    # Trigger rerun if needed
    if st.session_state.get('need_rerun_after_file_load', False):
        st.session_state['need_rerun_after_file_load'] = False
        st.rerun()

# --- Simulation Output & Actions (Sidebar) ---
with st.sidebar.container():
    st.subheader("Simulation Status") # Clear section title



    # --- Display simulation status from session state ---
    last_sim_status = st.session_state.get('last_sim_status', None)
    if last_sim_status:
        if last_sim_status['success']:
            if last_sim_status.get('has_warning', False):
                # Show as warning if sim ok but plot failed
                status_container = st.warning(last_sim_status['message'])
            else:
                status_container = st.success(last_sim_status['message'])
        else:
            status_container = st.error(last_sim_status['message'])

        # --- Display log file content if available ---
        log_file_path = st.session_state.get('last_log_file')
        if log_file_path and os.path.isfile(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                with st.expander("Show LTSPICE Log", expanded=not st.session_state.get('last_sim_status', {}).get('success', True)): # Shortened label
                    st.code(log_content, language='text')
            except Exception as e:
                st.warning(f"Could not read log file {log_file_path}: {e}")

        # --- Action Buttons (Vertical Layout) ---

        # --- Save Netlist Section ---
        st.subheader("Save Netlist")

        # Check if we have a valid netlist to save
        has_valid_netlist = (st.session_state.get('current_netlist') and
                            st.session_state['current_netlist'] != INITIAL_NETLIST and
                            st.session_state['current_netlist'] != EMPTY_NETLIST)

        # Get the original file path if available
        original_file_path = st.session_state.get('original_file_path')
        original_file_name = st.session_state.get('original_file_name')

        # Option to save back to original file
        if original_file_path and os.path.isfile(original_file_path):
            if st.button("💾 Save to Original File", key="save_to_original_btn",
                       use_container_width=True, disabled=not has_valid_netlist):
                current_netlist = st.session_state.get('current_netlist', '')
                if has_valid_netlist:
                    try:
                        with open(original_file_path, 'w', encoding='utf-8') as f:
                            f.write(current_netlist)
                        st.success(f"Saved to original file: `{original_file_path}`")
                        st.toast(f"Saved to {os.path.basename(original_file_path)}", icon="💾")
                    except Exception as e:
                        st.error(f"Error saving to original file: {e}")
                else:
                    st.warning("No netlist generated yet to save.")
        elif original_file_name:
            # Try to find the file one more time in case it was moved or renamed
            found_path = find_file_in_directory(original_file_name)
            if found_path and os.path.isfile(found_path):
                # Update the session state with the found path
                st.session_state['original_file_path'] = found_path
                if st.button("💾 Save to Found Original File", key="save_to_found_file_btn",
                           use_container_width=True, disabled=not has_valid_netlist):
                    current_netlist = st.session_state.get('current_netlist', '')
                    if has_valid_netlist:
                        try:
                            with open(found_path, 'w', encoding='utf-8') as f:
                                f.write(current_netlist)
                            st.success(f"Saved to found file: `{found_path}`")
                            st.toast(f"Saved to {os.path.basename(found_path)}", icon="💾")
                        except Exception as e:
                            st.error(f"Error saving to found file: {e}")
                    else:
                        st.warning("No netlist generated yet to save.")
            else:
                # Show a more helpful message with instructions
                st.info(f"Original file '{original_file_name}' path not available for direct saving. " +
                        f"You can save to a custom location below.")

        # Save to custom location
        st.write("Save to custom location:")
        os.makedirs(SAVED_CIRCUITS_DIR, exist_ok=True)

        # Determine default filename
        default_filename = "my_circuit.net"
        # First try to use the original filename if available
        if original_file_name:
            default_filename = original_file_name
        # Otherwise use the simulation filename if available
        else:
            last_sim_temp_dir = st.session_state.get('last_sim_temp_dir')
            last_raw_file = st.session_state.get('last_raw_file')
            if last_sim_temp_dir and last_raw_file:
                default_filename = f"{os.path.basename(last_raw_file).split('.')[0]}.net"

        # Save to custom location UI
        save_filename = st.text_input(
            "Filename:", # Shorter label
            value=default_filename,
            key="save_netlist_filename_sidebar", # Updated key
            help="Enter filename with or without extension. If no extension is provided, .net will be added automatically."
        )

        # Radio button for save location
        save_location = st.radio(
            "Save location:",
            ["Default directory", "Custom path"],
            key="save_location_radio",
            horizontal=True
        )

        # Custom path input if selected
        custom_save_path = None
        if save_location == "Custom path":
            # Initialize the directory path in session state if not already set
            if 'custom_dir_path' not in st.session_state:
                st.session_state['custom_dir_path'] = os.path.dirname(original_file_path) if original_file_path else SAVED_CIRCUITS_DIR

            # Function to handle directory selection
            def select_directory():
                initial_dir = st.session_state.get('custom_dir_path', os.getcwd())
                selected_dir = select_directory_dialog(initial_dir)
                if selected_dir:
                    st.session_state['custom_dir_path'] = selected_dir
                    # Flag to trigger a rerun to update the UI
                    st.session_state['need_rerun_after_dir_select'] = True
                else:
                    # If dialog fails or is canceled, show a message
                    st.session_state['dir_select_error'] = True

            # Create a container for the directory selection with a label above both controls
            st.write("Custom directory path:")

            # Create a horizontal layout with columns for the text input and browse button
            dir_cols = st.columns([0.8, 0.2])

            # Text input in the first column
            with dir_cols[0]:
                custom_dir = st.text_input(
                    "",  # Empty label to remove the label
                    value=st.session_state.get('custom_dir_path', ''),
                    key="custom_save_dir",
                    label_visibility="collapsed"  # Hide the label completely
                )
                # Update session state when text input changes
                if custom_dir != st.session_state.get('custom_dir_path', ''):
                    st.session_state['custom_dir_path'] = custom_dir

            # Browse button in the second column
            with dir_cols[1]:
                # Use container width to make the button fill the column
                st.button("📁 Browse", key="browse_dir_btn", on_click=select_directory, use_container_width=True)

            # Display error message if directory selection failed
            if st.session_state.get('dir_select_error', False):
                st.info("No directory selected or dialog could not be opened. Please enter the path manually.")
                st.session_state['dir_select_error'] = False

            # Check if directory exists and show warning if not
            if custom_dir and not os.path.isdir(custom_dir):
                st.warning(f"Directory does not exist: {custom_dir}")
            else:
                custom_save_path = custom_dir

            # Trigger rerun if needed after directory selection
            if st.session_state.get('need_rerun_after_dir_select', False):
                st.session_state['need_rerun_after_dir_select'] = False
                st.rerun()

        # Save button
        if st.button("💾 Save Netlist", key="save_netlist_btn_sidebar",
                   use_container_width=True, disabled=not has_valid_netlist):
            current_netlist = st.session_state.get('current_netlist', '')
            if has_valid_netlist:
                fname = save_filename.strip()
                # Check if the filename has any extension
                if '.' not in fname:
                    # No extension provided, add .net as default
                    fname += ".net"
                # Otherwise, respect the user's choice of extension
                if not fname:
                    st.error("Please provide a valid filename.")
                else:
                    # Determine the save path based on the selected location
                    if save_location == "Default directory":
                        save_path = os.path.join(SAVED_CIRCUITS_DIR, fname)
                    else:
                        if custom_save_path and os.path.isdir(custom_save_path):
                            save_path = os.path.join(custom_save_path, fname)
                        else:
                            st.error(f"Invalid save directory: {custom_save_path}")
                            save_path = None

                    # Save the file if we have a valid path
                    if save_path:
                        try:
                            # Create directory if it doesn't exist
                            os.makedirs(os.path.dirname(save_path), exist_ok=True)
                            with open(save_path, 'w', encoding='utf-8') as f:
                                f.write(current_netlist)
                            st.success(f"Saved: `{save_path}`") # Shorter success
                            st.toast(f"Saved {fname}", icon="💾")
                        except Exception as e:
                            st.error(f"Error saving: {e}") # Shorter error
            else:
                st.warning("No netlist generated yet to save.")


        # --- Open Log File ---
        log_file_path = st.session_state.get('last_log_file')
        log_exists = log_file_path and os.path.isfile(log_file_path)
        if st.button("📄 Open Log File", key="open_log_btn_sidebar", use_container_width=True, disabled=not log_exists): # Updated key
            if log_exists:
                if not open_file_with_default_app(log_file_path):
                    st.error(f"Failed to open log file: {log_file_path}")
                else:
                    st.toast("Attempting to open log file...", icon="📄")
            else:
                st.warning("No log file found.")  # Shorter warning


        # --- Open Raw File ---
        raw_file_path = st.session_state.get('last_raw_file')
        raw_exists = raw_file_path and os.path.isfile(raw_file_path)
        if st.button("📈 Open Results (.raw)", key="open_raw_btn_sidebar", use_container_width=True, disabled=not raw_exists): # Updated key
            if raw_exists:
                if not open_file_with_default_app(raw_file_path):
                    st.error(f"Failed to open RAW file: {raw_file_path}")
                else:
                    st.toast("Attempting to open .raw file...", icon="📈") # Shorter toast
            else:
                st.warning("No .raw file found.") # Shorter warning


# --- Main Area ---
st.header("Circuit Description / Command")
# Use session state for user input persistence across reruns
st.session_state.user_input = st.text_area(
    "Enter your circuit description or modification command:",
    value=st.session_state.user_input,
    height=100,
    key="user_input_area" # Give it a key
)
user_input = st.session_state.user_input # Get the value for processing

st.header("Current Netlist")

# Display AI summary message if available
ai_summary = st.session_state.get('ai_summary_message')
if ai_summary:
    st.info(f"**AI Summary:** {ai_summary}")

# Ensure text area displays the current state value directly
# Do NOT assign to st.session_state.netlist_area here, let rerun handle it.
netlist_display_value = st.session_state.get('current_netlist', INITIAL_NETLIST)
# If the netlist is empty (after Clear All), use an empty string
if netlist_display_value == EMPTY_NETLIST:
    netlist_display_value = ""
netlist_display = st.text_area(
    "Generated/Current Netlist:",
    value=netlist_display_value, # Bind value directly
    height=300,
    key="netlist_display_area" # Use a key for potential programmatic updates if needed later
)
# Store manual edits back to session state if user types directly
st.session_state['current_netlist'] = netlist_display


# --- Buttons ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⚡ Generate/Update Netlist", use_container_width=True):
        # Check config from session state
        current_config = st.session_state.get('config', {})
        if not user_input.strip():
            st.warning("Please enter a description or command first.")
        elif not current_config.get('api_key'):
             st.error("Cannot generate netlist: API Key is missing in settings.")
        elif not current_config.get('llm_model'):
             st.error("Cannot generate netlist: LLM Model is missing in settings.")
        elif not current_config.get('api_url'):
             st.error("Cannot generate netlist: API URL is missing in settings.")
        else:
            current_netlist = st.session_state.get('current_netlist', '')
            status_display = st.empty() # Create placeholder here for updates

            # Decide on prompt template
            generation_keywords = ['new circuit', 'generate', 'create', 'design a', 'make a', 'start over']
            use_generation_prompt = any(keyword in user_input.lower() for keyword in generation_keywords) or \
                                    current_netlist == INITIAL_NETLIST or \
                                    current_netlist == EMPTY_NETLIST or \
                                    not current_netlist.strip()

            if use_generation_prompt:
                prompt = NETLIST_GENERATION_PROMPT_TEMPLATE.format(user_description=user_input)
                status_msg = "Generating new netlist..."
            else:
                prompt = NETLIST_MODIFICATION_PROMPT_TEMPLATE.format(
                    current_netlist=current_netlist,
                    user_modification_request=user_input
                )
                status_msg = "Updating netlist..."

            with st.spinner(status_msg):
                llm_response = asyncio.run(get_llm_response(
                    prompt=prompt,
                    api_key=current_config.get('api_key'),
                    model=current_config.get('llm_model'),
                    api_base=current_config.get('api_url')
                )) # Pass config from session state

                if llm_response:
                    # Check if the response indicates the model has expired
                    if is_model_expired_message(llm_response):
                        error_msg = extract_model_expired_message(llm_response)
                        alternative_models = get_alternative_models()

                        # Create an error message with alternative model suggestions
                        st.error(f"🚫 {error_msg}")

                        # Show alternative models
                        with st.expander("Suggested Alternative Models"):
                            st.write("The model you're using is no longer available. Please update your settings with one of these alternatives:")
                            for model in alternative_models:
                                st.code(model, language="text")
                            st.write("You can update your model in the ⚙️ Settings panel in the sidebar.")

                        # Highlight the settings section
                        st.info("👈 Open the Settings panel in the sidebar to update your model.")
                    else:
                        # Normal processing for valid responses
                        st.session_state['llm_raw_response'] = llm_response # Store for debugging
                        new_netlist, summary_message = extract_spice_netlist(llm_response)
                        if new_netlist:
                            st.session_state['current_netlist'] = new_netlist
                            st.session_state['ai_summary_message'] = summary_message
                            st.success("Netlist updated!") # Use temporary success message
                            st.session_state['user_input'] = "" # Clear input field after success
                            st.rerun()
                        else:
                            st.warning("LLM responded, but could not extract a valid SPICE netlist. See raw response below.")
                            # Display raw response for debugging
                            st.text_area("LLM Raw Response:", value=llm_response, height=200, disabled=True)
                else:
                    st.error("Failed to get response from LLM. Check console/logs for details.")

with col2:
    if st.button("🔄 Simulate", use_container_width=True): # Added icon
        current_netlist = st.session_state.get('current_netlist', '')
        # Check config from session state
        current_config = st.session_state.get('config', {})
        ltspice_path_valid = current_config.get('ltspice_path') and os.path.isfile(current_config['ltspice_path'])

        if not current_netlist or current_netlist == INITIAL_NETLIST or current_netlist == EMPTY_NETLIST:
            st.warning("Netlist is empty or default. Generate a circuit first.")
        elif not ltspice_path_valid:
            st.error(f"Cannot simulate: LTSPICE path is invalid or not configured in settings.")
        elif not current_config.get('api_key'): # Needed if we might ask AI to add sim command
            st.error("Cannot simulate: API Key is missing in settings (needed to potentially add simulation command).")
        elif not current_config.get('llm_model'): # Needed for adding sim command
             st.error("Cannot simulate: LLM Model is missing in settings (needed to potentially add simulation command).")
        elif not current_config.get('api_url'): # Needed for adding sim command
             st.error("Cannot simulate: API URL is missing in settings (needed to potentially add simulation command).")
        else:
            # We'll use the sidebar for status messages instead of the main area
            # Create a reference to the sidebar status section for updating session state only
            netlist_to_simulate = current_netlist # Start with the current netlist

            # --- Check/Add Simulation Command ---
            sim_cmd_found = re.search(r'^\s*\.(tran|ac|op|dc|noise|tf)\s+', netlist_to_simulate, re.IGNORECASE | re.MULTILINE)

            if not sim_cmd_found:
                # Use toast instead of status placeholder
                st.toast("Netlist lacks simulation command. Asking AI to add one...", icon="ℹ️")
                prompt = ADD_SIMULATION_PROMPT_TEMPLATE.format(existing_netlist=netlist_to_simulate)

                llm_response = asyncio.run(get_llm_response(
                    prompt=prompt,
                    api_key=current_config.get('api_key'),
                    model=current_config.get('llm_model'),
                    api_base=current_config.get('api_url')
                )) # Pass config
                if llm_response:
                    # Check if the response indicates the model has expired
                    if is_model_expired_message(llm_response):
                        error_msg = extract_model_expired_message(llm_response)
                        alternative_models = get_alternative_models()

                        # Create an error message with alternative model suggestions
                        st.error(f"🚫 {error_msg}")

                        # Show alternative models
                        with st.expander("Suggested Alternative Models"):
                            st.write("The model you're using is no longer available. Please update your settings with one of these alternatives:")
                            for model in alternative_models:
                                st.code(model, language="text")
                            st.write("You can update your model in the ⚙️ Settings panel in the sidebar.")

                        # Highlight the settings section
                        st.info("👈 Open the Settings panel in the sidebar to update your model.")
                        st.stop() # Stop execution for this button press
                    else:
                        # Normal processing for valid responses
                        modified_netlist, summary_message = extract_spice_netlist(llm_response)
                        if modified_netlist and re.search(r'^\s*\.(tran|ac|op|dc|noise|tf)\s+', modified_netlist, re.IGNORECASE | re.MULTILINE):
                            st.success("AI added a simulation command to the netlist.")
                            # Update the session state AND the text area for user visibility
                            st.session_state['current_netlist'] = modified_netlist
                            st.session_state['ai_summary_message'] = summary_message
                            netlist_to_simulate = modified_netlist # Use the modified one for the run
                            # For now, let's just use the modified netlist for simulation.
                            # We might need a rerun here if we want the user to *see* the change before sim runs.
                            # Let's skip immediate rerun for now to avoid interruption. User can see it after.
                            print("AI added sim command, proceeding with simulation.")
                        else:
                            st.error("AI responded, but failed to provide a netlist with a simulation command. Cannot simulate.")
                            # Optionally display raw response for debugging
                            st.text_area("LLM Raw Response (Add Sim):", value=llm_response, height=150, disabled=True)
                            st.stop() # Stop execution for this button press
                else:
                    st.error("Failed to get response from AI when asking to add simulation command. Cannot simulate.")
                    st.stop() # Stop execution
            else:
                print("Simulation command found in netlist.")

            # --- Cleanup Previous Simulation ---
            previous_temp_dir = st.session_state.pop('last_sim_temp_dir', None) # Get and remove previous dir path
            if previous_temp_dir:
                # Use toast instead of status placeholder
                st.toast(f"Cleaning up previous simulation files...", icon="🧹")
                cleanup_simulation_files(previous_temp_dir) # Call cleanup

            # --- Extract .plot directives from netlist ---
            print("\nDEBUG: Netlist content for .plot extraction:")
            print(netlist_to_simulate)
            print("\nEND DEBUG\n")
            plot_nodes = extract_plot_directives(netlist_to_simulate)
            st.session_state['plot_directive_nodes'] = plot_nodes
            if plot_nodes:
                print(f"Found .plot directives for nodes: {plot_nodes}")
            else:
                print("WARNING: No .plot directives found in the netlist!")

            # --- Run New Simulation ---
            # Use toast instead of status placeholder
            st.toast("Running LTSPICE simulation...", icon="⚡")
            # Clear previous plot data
            st.session_state['plot_data'] = None
            st.session_state['available_variables'] = None
            st.session_state['selected_variables'] = []
            # Reset first_load flag to ensure matched variables are used for the new simulation
            st.session_state['first_load'] = True

            # Generate a unique filename with timestamp to avoid conflicts
            base_name = f"streamlit_sim_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
            sim_success, sim_message, raw_file, log_file, temp_dir = run_ltspice_simulation(
                netlist_content=netlist_to_simulate,
                ltspice_executable_path=current_config.get('ltspice_path'), # Pass path from session state
                base_filename=base_name
            )

            # Store results/paths from the new simulation
            st.session_state['last_sim_temp_dir'] = temp_dir # Store new temp dir path
            st.session_state['last_raw_file'] = raw_file
            st.session_state['last_log_file'] = log_file

            # Store status message for display after potential rerun
            st.session_state['last_sim_status'] = {'success': sim_success, 'message': sim_message}

            # Attempt to parse RAW file if simulation succeeded
            if sim_success and raw_file and os.path.isfile(raw_file):
                df_data, variables, parse_error = parse_raw_file(raw_file)
                if parse_error:
                    st.session_state['last_sim_status']['message'] += f"\n⚠️ Plotting Error: {parse_error}"
                elif df_data is not None and variables is not None:
                    st.session_state['plot_data'] = df_data
                    st.session_state['available_variables'] = variables

                    # Check for plot directive nodes and select them if available
                    plot_directive_nodes = st.session_state.get('plot_directive_nodes', [])
                    if plot_directive_nodes and variables:
                        # Print available variables for debugging
                        print(f"Available variables in raw file: {variables}")
                        print(f"Plot directive nodes: {plot_directive_nodes}")

                        # DIRECT APPROACH: Match any node in plot directives
                        selected_vars = []

                        # Process each node in the plot directives
                        for plot_node in plot_directive_nodes:
                            print(f"Processing plot directive node: {plot_node}")
                            node_matched = False

                            # Extract the node name if it's in V(node) format
                            node_name = None
                            if '(' in plot_node and ')' in plot_node:
                                try:
                                    node_type = plot_node.split('(')[0].upper()  # V or I
                                    node_name = plot_node.split('(')[1].split(')')[0]  # Extract node name
                                    print(f"Extracted node name: {node_name} from {plot_node}")
                                except (IndexError, ValueError) as e:
                                    print(f"Error extracting node name from {plot_node}: {e}")
                            else:
                                # If it's just a node name without V() wrapper
                                node_name = plot_node
                                print(f"Using direct node name: {node_name}")

                            if node_name:
                                # Convert to uppercase for case-insensitive comparison
                                node_name_upper = node_name.upper()

                                # STEP 1: Try exact match with V(node_name)
                                for var in variables:
                                    # Check if variable is V(node_name) with any case
                                    if var.upper() == f"V({node_name_upper})":
                                        selected_vars.append(var)
                                        node_matched = True
                                        print(f"Exact V(node) match: {var} for {plot_node}")
                                        break

                                # STEP 2: If not found, try to match just the node name
                                if not node_matched:
                                    for var in variables:
                                        if var.upper() == node_name_upper:
                                            selected_vars.append(var)
                                            node_matched = True
                                            print(f"Exact node name match: {var} for {plot_node}")
                                            break

                                # STEP 3: Try to find any V(node) where node contains our node name
                                if not node_matched:
                                    best_match = None
                                    best_score = 0

                                    for var in variables:
                                        # Only consider voltage variables
                                        if var.upper().startswith('V(') and var.upper().endswith(')'):
                                            # Extract the variable's node name
                                            var_node = var[2:-1]  # Remove V( and )

                                            # Calculate match score
                                            score = 0

                                            # Exact match gets highest score
                                            if var_node.upper() == node_name_upper:
                                                score = 100
                                            # Node name is part of variable node
                                            elif node_name_upper in var_node.upper():
                                                score = 50
                                            # Variable node is part of node name
                                            elif var_node.upper() in node_name_upper:
                                                score = 30

                                            # Prefer shorter variable names (more specific matches)
                                            score -= len(var_node) * 0.1

                                            if score > best_score:
                                                best_score = score
                                                best_match = var

                                    if best_match:
                                        selected_vars.append(best_match)
                                        node_matched = True
                                        print(f"Best V(node) match: {best_match} for {plot_node} (score: {best_score})")

                                # STEP 4: Last resort - try any variable containing the node name
                                if not node_matched:
                                    for var in variables:
                                        if node_name_upper in var.upper():
                                            selected_vars.append(var)
                                            node_matched = True
                                            print(f"Substring match: {var} contains {node_name}")
                                            break

                            # If we still couldn't match this node, print a warning
                            if not node_matched:
                                print(f"WARNING: Could not find a match for plot node: {plot_node}")

                        # If we didn't find any matches, default to the first variable
                        if not selected_vars and variables:
                            selected_vars = [variables[0]]
                            print(f"No matches found for any plot nodes. Defaulting to first variable: {variables[0]}")

                        # IMPROVED APPROACH: Select all variables from plot directives
                        # This replaces the previous direct override approach
                        all_matched_vars = []
                        print(f"Attempting to match all plot nodes: {plot_directive_nodes}")

                        # First, try to match each plot node with available variables
                        for plot_node in plot_directive_nodes:
                            node_matched = False

                            # Direct match for common cases
                            if plot_node.upper() == 'V(IN)' and 'V(in)' in variables:
                                all_matched_vars.append('V(in)')
                                print(f"Direct match: {plot_node} -> V(in)")
                                node_matched = True
                            elif plot_node.upper() == 'V(OUT)' and 'V(out)' in variables:
                                all_matched_vars.append('V(out)')
                                print(f"Direct match: {plot_node} -> V(out)")
                                node_matched = True
                            elif plot_node.upper() == 'V(MID)' and 'V(mid)' in variables:
                                all_matched_vars.append('V(mid)')
                                print(f"Direct match: {plot_node} -> V(mid)")
                                node_matched = True

                            # Case-insensitive match for any variable
                            if not node_matched:
                                for var in variables:
                                    if var.upper() == plot_node.upper():
                                        all_matched_vars.append(var)
                                        print(f"Case-insensitive match: {plot_node} -> {var}")
                                        node_matched = True
                                        break

                            # If still not matched, try to extract node name
                            if not node_matched and '(' in plot_node and ')' in plot_node:
                                try:
                                    node_type = plot_node.split('(')[0].upper()  # V or I
                                    node_name = plot_node.split('(')[1].split(')')[0]  # Extract node name

                                    for var in variables:
                                        if var.upper() == f"{node_type}({node_name.upper()})":
                                            all_matched_vars.append(var)
                                            print(f"Node name match: {plot_node} -> {var}")
                                            node_matched = True
                                            break
                                except (IndexError, ValueError) as e:
                                    print(f"Error extracting node name from {plot_node}: {e}")

                            if not node_matched:
                                print(f"Could not match plot node: {plot_node}")

                        # If we found any matches, use them instead of the previous selection
                        if all_matched_vars:
                            selected_vars = all_matched_vars
                            print(f"OVERRIDE: Selected all matched variables: {selected_vars}")
                        elif selected_vars:  # Keep any previously matched variables if we didn't find direct matches
                            print(f"Keeping previously matched variables: {selected_vars}")
                        else:  # If no matches at all, default to first variable
                            selected_vars = [variables[0]]
                            print(f"No matches found, defaulting to first variable: {variables[0]}")

                        # Remove duplicates while preserving order
                        selected_vars = list(dict.fromkeys(selected_vars))
                        print(f"Final selected variables (after removing duplicates): {selected_vars}")

                        # The old standard matching code is now replaced by the direct approach above

                        # If we found matches, use them
                        if selected_vars:
                            # For debugging, print what we found
                            print(f"Final selected variables: {selected_vars}")

                            # We've already handled special cases with direct overrides above

                            # CRITICAL: Force the selection of all variables from the .plot directive
                            # Update session state with selected variables
                            st.session_state['selected_variables'] = selected_vars
                            # Set a flag to force the selection on the next rerun
                            st.session_state['force_plot_selection'] = True
                            print(f"Auto-selected variables from .plot directives: {selected_vars}")
                            # Add a message to the simulation status to inform the user
                            auto_select_msg = f"Auto-selected plot variables from .plot directive: {', '.join(selected_vars)}"
                            st.session_state['last_sim_status']['message'] += f"\n✅ {auto_select_msg}"
                            # Force a rerun to update the UI with the selected variables
                            st.rerun()
                        else:
                            # If no matches found, fall back to selecting the first variable
                            st.session_state['selected_variables'] = [variables[0]]
                            # Set a flag to force the selection on the next rerun
                            st.session_state['force_plot_selection'] = True
                            print(f"No matches found for plot nodes {plot_directive_nodes}, defaulting to first variable")
                            # Force a rerun to update the UI with the selected variables
                            st.rerun()
                    elif variables:
                        # If no plot directives, select the first variable as before
                        st.session_state['selected_variables'] = [variables[0]]
                        # Set a flag to force the selection on the next rerun
                        st.session_state['force_plot_selection'] = True

                    print("DEBUG: Successfully parsed RAW file. Variables:", variables) # Debug
                else:
                    # Handle case where parse_raw_file returns None, None, None (shouldn't happen ideally)
                    st.session_state['last_sim_status']['message'] += f"\n⚠️ Plotting Error: Parsing returned unexpected None values."

            # Update session state with simulation status - will be displayed in sidebar
            if sim_success:
                # Check if there was a subsequent parsing error message added
                if "Plotting Error" in sim_message:
                    st.session_state['last_sim_status'] = {'success': True, 'message': sim_message, 'has_warning': True}
                else:
                    st.session_state['last_sim_status'] = {'success': True, 'message': sim_message, 'has_warning': False}
                st.toast("Simulation successful!", icon="✅") # Add a toast
            else:
                st.session_state['last_sim_status'] = {'success': False, 'message': sim_message}
                st.toast("Simulation failed!", icon="❌")

            # Flag to indicate we need to rerun after displaying log content
            st.session_state['need_sidebar_refresh'] = True

            # Display log file content if available
            if log_file and os.path.isfile(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()
                    with st.expander("Show LTSPICE Log File", expanded=not sim_success): # Expand if error
                        st.code(log_content, language='text')
                except Exception as e:
                    st.warning(f"Could not read log file {log_file}: {e}")
            elif temp_dir: # Log file path might be None but dir exists
                potential_log = os.path.join(temp_dir, "streamlit_sim.log")
                if os.path.isfile(potential_log):
                    try:
                        with open(potential_log, 'r', encoding='utf-8', errors='ignore') as f:
                            log_content = f.read()
                        with st.expander("Show LTSPICE Log File", expanded=not sim_success):
                            st.code(log_content, language='text')
                    except Exception as e:
                        st.warning(f"Could not read potential log file {potential_log}: {e}")

            # If AI modified the netlist, update the session state
            if not sim_cmd_found and netlist_to_simulate != current_netlist:
                st.session_state['current_netlist'] = netlist_to_simulate # Ensure state has the updated one

            # Force a rerun to update the sidebar status and any other UI elements
            if st.session_state.get('need_sidebar_refresh', False):
                st.session_state['need_sidebar_refresh'] = False  # Reset the flag to avoid infinite reruns
                st.rerun() # Rerun to update the UI
with col3:
    if st.button("🗑️ Clear All", use_container_width=True): # Added icon
         st.session_state['current_netlist'] = EMPTY_NETLIST # Use empty string instead of INITIAL_NETLIST
         st.session_state['user_input'] = "" # Clear user input state too
         # Clear AI summary message
         st.session_state['ai_summary_message'] = None
         # Clear potential raw response display
         if 'llm_raw_response' in st.session_state:
              del st.session_state['llm_raw_response']
         st.success("Cleared inputs and netlist.")
         st.rerun()

# Add file management section
# --- Display Plot ---
plot_data = st.session_state.get('plot_data')
available_vars = st.session_state.get('available_variables')

if plot_data is not None and not plot_data.empty:
    st.divider()
    st.subheader("📊 Simulation Plot")
    if available_vars:
        # FINAL SOLUTION: Use a completely different approach to avoid the warning

        # Create a unique key for the multiselect widget
        multiselect_key = "plot_variables_select"

        # Get the plot directive nodes and find their corresponding variables
        plot_directive_nodes = st.session_state.get('plot_directive_nodes', [])

        # Print debug information
        print(f"Plot directive nodes: {plot_directive_nodes}")
        print(f"Available variables: {available_vars}")

        # Match plot directive nodes with available variables
        matched_vars = []

        # Try to match each plot directive node with available variables
        for node in plot_directive_nodes:
            node_upper = node.upper()
            matched = False

            # Try exact match first
            for var in available_vars:
                if var.upper() == node_upper:
                    matched_vars.append(var)
                    print(f"Exact match: {node} -> {var}")
                    matched = True
                    break

            # If not matched, try to extract node name
            if not matched and '(' in node and ')' in node:
                try:
                    node_type = node.split('(')[0].upper()  # V or I
                    node_name = node.split('(')[1].split(')')[0]  # Extract node name
                    node_name_upper = node_name.upper()

                    for var in available_vars:
                        if var.upper() == f"{node_type}({node_name_upper})":
                            matched_vars.append(var)
                            print(f"Node name match: {node} -> {var}")
                            matched = True
                            break
                except (IndexError, ValueError) as e:
                    print(f"Error extracting node name from {node}: {e}")

            if not matched:
                print(f"Could not match plot node: {node}")

        # If we didn't find any matches, use the first variable
        if not matched_vars and available_vars:
            matched_vars = [available_vars[0]]
            print(f"No matches found, defaulting to first variable: {available_vars[0]}")

        # Remove duplicates while preserving order
        matched_vars = list(dict.fromkeys(matched_vars))
        print(f"Final matched variables: {matched_vars}")

        # Handle the force_plot_selection flag - this is set when a simulation is run with .plot directives
        if st.session_state.get('force_plot_selection', False):
            # Directly update the multiselect widget's value with matched variables
            st.session_state[multiselect_key] = matched_vars.copy()
            # Also update the selected_variables session state
            st.session_state['selected_variables'] = matched_vars.copy()
            print(f"FORCED: Setting selection to matched variables: {matched_vars}")
            # Reset the flag to avoid overwriting user selections on subsequent runs
            st.session_state['force_plot_selection'] = False
            # Also reset first_load flag
            st.session_state['first_load'] = False
        # Initialize the widget with matched variables on first load or when empty
        elif multiselect_key not in st.session_state or not st.session_state[multiselect_key] or \
             (matched_vars and st.session_state.get('first_load', True)):
            # Directly update the multiselect widget's value
            st.session_state[multiselect_key] = matched_vars
            print(f"Setting initial selection to matched variables: {matched_vars}")
            # Set first_load to False to avoid overwriting user selections on subsequent runs
            st.session_state['first_load'] = False

        # Add a label for the plot variables selection
        st.write("Select variables to plot:")

        # Create a layout with the multiselect and buttons on the same line
        col1, col2, col3 = st.columns([6, 1, 1])

        # Define a callback function to handle changes to the multiselect widget
        def on_multiselect_change():
            # This function will be called when the user interacts with the multiselect widget
            print(f"Multiselect changed to: {st.session_state[multiselect_key]}")
            # Update the session state with the current selection
            st.session_state['selected_variables'] = st.session_state[multiselect_key]

        with col1:
            # If empty_selection flag is set, we want to clear the selection
            if st.session_state.get('empty_selection', False):
                # Instead of creating a new widget with a new key, update the existing widget's value
                st.session_state[multiselect_key] = []
                # Reset the flag
                st.session_state['empty_selection'] = False
                print(f"Cleared selection in existing widget")

            # If apply_selection flag is set, we want to apply specific variables
            elif st.session_state.get('apply_selection', False):
                # Get the matched variables from the session state
                apply_vars = st.session_state.get('apply_matched_vars', [])
                # Update the existing widget's value
                st.session_state[multiselect_key] = apply_vars
                # Reset the flag
                st.session_state['apply_selection'] = False
                print(f"Applied variables to existing widget: {apply_vars}")

            # Always use the same key for the multiselect widget to maintain state
            selected_vars = st.multiselect(
                "Select variables to plot:",
                options=available_vars,
                key=multiselect_key,
                on_change=on_multiselect_change,
                label_visibility="collapsed"  # Hide the label to align with buttons
            )
            print(f"Current selection: {selected_vars}")

        # Add the Apply .plot button if plot directives exist
        if plot_directive_nodes:
            # Create a string of plot nodes for the button help text
            plot_nodes_str = ', '.join(plot_directive_nodes)

            # Define a callback for the Apply .plot button
            def on_apply_plot():
                # Set a flag to apply the matched variables on the next rerun
                st.session_state['apply_selection'] = True
                st.session_state['apply_matched_vars'] = matched_vars.copy()
                st.toast(f"Applied plot nodes: {', '.join(matched_vars)}")

            with col2:
                st.button("📊 Apply .plot",
                          help=f"Apply the nodes specified in .plot directives: {plot_nodes_str}",
                          on_click=on_apply_plot,
                          use_container_width=True)

        # Always show the Clear button
        # Define a callback for the Clear button
        def on_clear_variables():
            # Set a flag to clear the selection on the next rerun
            st.session_state['empty_selection'] = True
            st.toast("Cleared all selected variables")

        with col3:
            st.button("🚫 Clear",
                      help="Clear all selected variables",
                      on_click=on_clear_variables,
                      use_container_width=True)

        # Update the session state with the current selection
        st.session_state['selected_variables'] = selected_vars

        # --- Add Log Scale Checkboxes ---
        col_log_x, col_log_y = st.columns(2)
        with col_log_x:
            log_x = st.checkbox("Log X-Axis", value=st.session_state.get('log_x_axis', False), key='log_x_checkbox')
            st.session_state['log_x_axis'] = log_x
        with col_log_y:
            log_y = st.checkbox("Log Y-Axis", value=st.session_state.get('log_y_axis', False), key='log_y_checkbox')
            st.session_state['log_y_axis'] = log_y
        # --- End Log Scale Checkboxes ---

        if selected_vars:
            try:
                # Ensure selected columns exist in the DataFrame
                valid_selected_vars = [var for var in selected_vars if var in plot_data.columns]

                if not valid_selected_vars:
                    st.warning("Selected variable(s) not found in the current data.")
                elif plot_data.empty:
                     st.warning("Plot data is empty.")
                else:
                    # Use the DataFrame index as the independent variable (X-axis)
                    df_for_plot = plot_data[valid_selected_vars].copy() # Select only dependent vars first
                    x_var_name = df_for_plot.index.name if df_for_plot.index.name else 'index' # Get index name or default
                    df_for_plot = df_for_plot.reset_index() # Turn index into a column

                    # Check for duplicate column names AFTER reset_index, although unlikely now
                    if df_for_plot.columns.duplicated().any():
                         st.error(f"Internal Error: Duplicate column names detected after reset_index: {df_for_plot.columns[df_for_plot.columns.duplicated()].tolist()}")
                         st.dataframe(df_for_plot.head())
                         st.stop()

                    # Ensure x_var_name is not accidentally in valid_selected_vars
                    if x_var_name in valid_selected_vars:
                        valid_selected_vars.remove(x_var_name)
                        st.warning(f"Removed index column '{x_var_name}' from selected variables to avoid duplication.")

                    # Melt DataFrame for Altair using the new index column name
                    try:
                        df_melted = pd.melt(df_for_plot, id_vars=[x_var_name], value_vars=valid_selected_vars,
                                            var_name='Variable', value_name='Value')
                    except Exception as melt_err:
                         st.error(f"Error preparing data for plotting (melt): {melt_err}")
                         st.dataframe(df_for_plot.head()) # Show data that failed to melt
                         st.stop()


                    # Define scales based on checkboxes
                    x_scale = alt.Scale(type='log' if log_x else 'linear', zero=False) # Added zero=False for robustness with log
                    y_scale = alt.Scale(type='log' if log_y else 'linear')

                    # Handle potential non-positive values for log scale using the correct column names
                    if log_x and (df_melted[x_var_name] <= 0).any():
                        positive_x_count = (df_melted[x_var_name] > 0).sum()
                        if positive_x_count == 0:
                             st.error(f"Cannot use log scale for X-axis ('{x_var_name}') as all values are non-positive.")
                             st.stop()
                        st.warning(f"X-axis ('{x_var_name}') has non-positive values. Filtering {len(df_melted) - positive_x_count} rows for log scale.")
                        df_melted = df_melted[df_melted[x_var_name] > 0]
                    if log_y and (df_melted['Value'] <= 0).any():
                         positive_y_count = (df_melted['Value'] > 0).sum()
                         if positive_y_count == 0:
                              st.error("Cannot use log scale for Y-axis as all selected variable values are non-positive.")
                              st.stop()
                         st.warning(f"Y-axis ('Value') has non-positive values. Filtering {len(df_melted) - positive_y_count} rows for log scale.")
                         df_melted = df_melted[df_melted['Value'] > 0]

                    if df_melted.empty:
                         st.warning("No data remaining after filtering for log scale.")
                    else:
                        # Create Altair chart using the correct x_var_name
                        chart = alt.Chart(df_melted).mark_line(point=False).encode( # point=False for potentially dense data
                            x=alt.X(f'{x_var_name}:Q', scale=x_scale, title=x_var_name),
                            y=alt.Y('Value:Q', scale=y_scale),
                            color='Variable:N',
                            tooltip=[alt.Tooltip(f'{x_var_name}:Q'), alt.Tooltip('Variable:N'), alt.Tooltip('Value:Q')]
                        ).interactive() # Enable zooming and panning

                        st.altair_chart(chart, use_container_width=True)

                        # --- Optional: Add data table ---
                        with st.expander("Show Plotted Data Table"):
                             st.dataframe(df_melted) # Show melted data

            except Exception as e:
                st.error(f"Error displaying plot: {e}")
                st.exception(e) # Show full traceback for debugging
        else:
            st.info("Select one or more variables from the list above to plot.")
    else:
        st.warning("Simulation ran, but no plottable variables were found in the `.raw` file or the data is empty.")

# Add a debug section (optional)
with st.expander("Debug Info"):
    st.write("Session State:", st.session_state)
    if 'llm_raw_response' in st.session_state:
         st.text_area("Last LLM Raw Response:", value=st.session_state['llm_raw_response'], height=150, disabled=True)

# Removed final config check - handled by sidebar status indicators now
