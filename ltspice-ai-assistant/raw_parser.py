# raw_parser.py
from PyLTSpice import RawRead
import pandas as pd
import numpy as np
import os

def parse_raw_file(raw_filepath: str) -> tuple[pd.DataFrame | None, list[str] | None, str | None]:
    """
    Parses an LTSPICE .raw file and returns data as a Pandas DataFrame.

    Args:
        raw_filepath: The path to the .raw file.

    Returns:
        A tuple containing:
        - pd.DataFrame: DataFrame with time as index and variables as columns (or None on error).
        - list[str]: List of variable names (trace names excluding 'time') (or None on error).
        - str: An error message if parsing failed, otherwise None.
    """
    if not os.path.isfile(raw_filepath):
        return None, None, f"Error: RAW file not found at '{raw_filepath}'"

    try:
        print(f"Attempting to parse RAW file: {raw_filepath}") # Debug print
        ltr = RawRead(raw_filepath)

        # Get trace names (variables available in the raw file)
        all_trace_names = ltr.get_trace_names()
        # print(f"Traces found: {all_trace_names}") # Debug print

        # Identify the primary independent variable (usually 'time')
        # Sometimes it might be frequency, etc. PyLTSpice might handle this,
        # but we assume 'time' for transient analysis for now.
        x_variable = 'time' # Assume transient analysis
        if x_variable not in all_trace_names:
             # Fallback or error handling if 'time' isn't the primary trace
             # Could try to guess (e.g., first trace) or look for known alternatives
             if all_trace_names:
                 x_variable = all_trace_names[0] # Risky guess
                 print(f"Warning: 'time' trace not found. Assuming '{x_variable}' is the independent variable.")
             else:
                  return None, None, "Error: No traces found in the RAW file."
             # return None, None, f"Error: Required '{x_variable}' trace not found in RAW file."


        # Extract data into a dictionary
        data_dict = {}
        x_trace = ltr.get_trace(x_variable)
        # PyLTSpice data can sometimes be complex (e.g., complex numbers for AC)
        # get_wave() might return complex types. Need to handle magnitude or real part.
        x_data = x_trace.get_wave() # Get data for step 0 (assuming single run)
        # Ensure data is real for typical plotting
        if np.iscomplexobj(x_data):
             print(f"Warning: Independent variable '{x_variable}' is complex. Taking magnitude.")
             x_data = np.abs(x_data)
        data_dict[x_variable] = x_data


        variable_names = []
        for name in all_trace_names:
            if name == x_variable:
                continue # Skip the independent variable

            trace = ltr.get_trace(name)
            # Handle potentially complex data from AC analysis etc.
            wave_data = trace.get_wave() # Get data for step 0
            if np.iscomplexobj(wave_data):
                # Decide how to handle complex data (e.g., magnitude, real part)
                # For generic plotting, magnitude is often useful
                print(f"Trace '{name}' is complex. Taking magnitude.")
                data_dict[name] = np.abs(wave_data)
            else:
                data_dict[name] = wave_data
            variable_names.append(name) # Add to list of dependent variables

        # Create DataFrame
        df = pd.DataFrame(data_dict)

        # Check if lengths match (important!)
        expected_len = len(x_data)
        mismatched = []
        for col, data in data_dict.items():
             if len(data) != expected_len:
                 mismatched.append(f"{col} (len {len(data)})")
                 # Handle mismatch: Pad, truncate, or error out. For now, let's just warn.
                 # df = df.drop(columns=[col]) # Option: drop mismatched columns
                 # variable_names.remove(col)
        if mismatched:
            print(f"Warning: Mismatched data lengths found! Expected {expected_len}. Mismatched: {', '.join(mismatched)}. DataFrame might be incomplete or plotting may fail.")
            # Attempt to create DF anyway, pandas might handle it or raise error
            try:
                 df = pd.DataFrame(data_dict) # Recreate maybe? Or handle above.
            except ValueError as ve:
                 return None, None, f"Error creating DataFrame due to mismatched lengths: {ve}"


        df = df.set_index(x_variable) # Set time (or x_variable) as index

        print(f"Successfully parsed. Variables: {variable_names}") # Debug print
        return df, variable_names, None

    except FileNotFoundError: # Redundant due to check above, but safe
         return None, None, f"Error: RAW file not found at '{raw_filepath}'"
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return None, None, f"Error parsing RAW file '{raw_filepath}': {e}"

# --- Add a simple test block ---
if __name__ == "__main__":
    print("--- Testing Raw File Parser ---")
    # Option 1: Put a sample .raw file in the same directory (e.g., 'test_circuit.raw')
    test_file = "test_circuit.raw" # CHANGE THIS if you have a sample file

    if os.path.exists(test_file):
        print(f"Attempting to parse local file: {test_file}")
        df_data, variables, error_msg = parse_raw_file(test_file)

        if error_msg:
            print(f"Parsing failed: {error_msg}")
        elif df_data is not None and variables is not None:
            print("Parsing successful!")
            print("Available variables:", variables)
            print("Data summary:")
            print(df_data.head()) # Print first few rows
            print("\nDataFrame Info:")
            df_data.info()
        else:
            print("Parsing returned unexpected None values without error message.")
    else:
        print(f"Test file '{test_file}' not found.")
        print("To test, place a valid LTSPICE .raw file named 'test_circuit.raw' in this directory,")
        print("or modify the 'test_file' variable in raw_parser.py.")
