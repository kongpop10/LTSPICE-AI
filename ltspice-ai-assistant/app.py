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
from file_utils import open_file_with_default_app
from raw_parser import parse_raw_file

# --- Constants ---
# Use absolute path to the root-level saved_circuits directory
SAVED_CIRCUITS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_circuits")

# --- Initialize Session State ---
# Configuration Settings (Load once at the start)
if 'config' not in st.session_state:
    st.session_state['config'] = load_settings()

# Other session state variables
INITIAL_NETLIST = "* Enter circuit description above and click Generate/Update\n*\n* Example: A 5V source V1 across 1k resistor R1\n\n.end"
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
    uploaded_file = st.file_uploader("Upload a netlist file (.net, .cir)", type=["net", "cir", "txt"], key="netlist_file_uploader")

    if uploaded_file is not None:
        if st.button("📂 Load Netlist", key="load_netlist_btn", use_container_width=True):
            try:
                # Read the content of the uploaded file
                netlist_content = uploaded_file.getvalue().decode("utf-8")

                # Update the current netlist in the session state
                st.session_state['current_netlist'] = netlist_content

                # Show success message
                st.success(f"Loaded netlist from {uploaded_file.name}")
                st.toast(f"Loaded {uploaded_file.name}", icon="📂")

                # Rerun to update the UI
                st.rerun()
            except Exception as e:
                st.error(f"Error loading netlist: {e}")

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

        # --- Save Netlist ---
        os.makedirs(SAVED_CIRCUITS_DIR, exist_ok=True)
        default_filename = "my_circuit.net"
        last_sim_temp_dir = st.session_state.get('last_sim_temp_dir')
        last_raw_file = st.session_state.get('last_raw_file')
        if last_sim_temp_dir and last_raw_file:
            default_filename = f"{os.path.basename(last_raw_file).split('.')[0]}.net"

        save_filename = st.text_input(
            "Save Filename:", # Shorter label
            value=default_filename,
            key="save_netlist_filename_sidebar" # Updated key
        )
        if st.button("💾 Save Netlist", key="save_netlist_btn_sidebar", use_container_width=True, disabled=(not st.session_state.get('current_netlist') or st.session_state['current_netlist'] == INITIAL_NETLIST)): # Updated key
            current_netlist = st.session_state.get('current_netlist', '')
            if current_netlist and current_netlist != INITIAL_NETLIST:
                fname = save_filename.strip()
                if not fname.endswith(".net"):
                    fname += ".net"
                if not fname:
                    st.error("Please provide a valid filename.")
                else:
                    save_path = os.path.join(SAVED_CIRCUITS_DIR, fname)
                    try:
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
netlist_display = st.text_area(
    "Generated/Current Netlist:",
    value=netlist_display_value, # Bind value directly
    height=300,
    key="netlist_display_area" # Use a key for potential programmatic updates if needed later
)
# Store manual edits back to session state if user types directly
st.session_state['current_netlist'] = netlist_display


# --- Buttons ---
col1, col2, col3, col4 = st.columns(4)
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

        if not current_netlist or current_netlist == INITIAL_NETLIST:
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

            # --- Run New Simulation ---
            # Use toast instead of status placeholder
            st.toast("Running LTSPICE simulation...", icon="⚡")
            # Clear previous plot data
            st.session_state['plot_data'] = None
            st.session_state['available_variables'] = None
            st.session_state['selected_variables'] = []

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
                    # Optionally pre-select the first variable if available
                    if variables:
                        st.session_state['selected_variables'] = [variables[0]]
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
    if st.button("👁️ View Raw File", use_container_width=True): # Updated for Phase 3
        raw_file_path = st.session_state.get('last_raw_file')
        if raw_file_path and os.path.isfile(raw_file_path):
            if open_file_with_default_app(raw_file_path):
                st.toast("Opening simulation results in LTSPICE...", icon="📈")
            else:
                st.error(f"Failed to open RAW file: {raw_file_path}. Is LTSPICE installed and associated with .raw files?")
        else:
            st.warning("No simulation results (.raw) file available. Run a simulation first.")
with col4:
    if st.button("🗑️ Clear All", use_container_width=True): # Added icon
         st.session_state['current_netlist'] = INITIAL_NETLIST
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
        # Use current selection from state as default
        selected_vars = st.multiselect(
            "Select variables to plot:",
            options=available_vars,
            default=st.session_state.get('selected_variables', []) # Use state for persistence
        )
        # Update state with current selection
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
