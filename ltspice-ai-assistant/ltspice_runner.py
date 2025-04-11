# ltspice_runner.py
import subprocess
import os
import tempfile
import shutil  # For cleanup
# Remove direct config import
# from config import LTSPICE_EXECUTABLE

def run_ltspice_simulation(netlist_content: str, ltspice_executable_path: str, base_filename: str = 'temp_circuit') -> tuple[bool, str, str | None, str | None, str | None]:
    """
    Runs LTSPICE simulation in batch mode on the given netlist using the specified executable.

    Args:
        netlist_content: The SPICE netlist as a string.
        ltspice_executable_path: The full path to the LTspice executable.
        base_filename: The base name for the .net, .raw, .log files.

    Returns:
        A tuple containing:
        - bool: True if simulation ran successfully (return code 0 and .raw file exists), False otherwise.
        - str: A status message describing the outcome.
        - str | None: Path to the generated .raw file if successful, None otherwise.
        - str | None: Path to the generated .log file if it exists, None otherwise.
        - str | None: Path to the temporary directory used for the simulation.
    """
    if not ltspice_executable_path or not os.path.isfile(ltspice_executable_path):
        return False, f"LTSPICE executable not found or invalid path: {ltspice_executable_path}", None, None, None

    temp_dir = None  # Initialize to None
    try:
        temp_dir = tempfile.mkdtemp(prefix="ltspice_sim_")
        netlist_filename = f"{base_filename}.net"
        netlist_filepath = os.path.join(temp_dir, netlist_filename)

        # --- Write Netlist File ---
        try:
            with open(netlist_filepath, 'w', encoding='utf-8') as f:
                f.write(netlist_content)
            print(f"Netlist written to: {netlist_filepath}")
        except IOError as e:
            return False, f"Error writing netlist file: {e}", None, None, temp_dir  # Return dir path for potential partial cleanup

        # --- Construct and Run LTSPICE Command ---
        command = [ltspice_executable_path, "-b", netlist_filepath]
        log_filename = f"{base_filename}.log"
        raw_filename = f"{base_filename}.raw"
        log_filepath = os.path.join(temp_dir, log_filename)
        raw_filepath = os.path.join(temp_dir, raw_filename)

        print(f"Running LTSPICE command: {' '.join(command)}")
        print(f"Working Directory: {temp_dir}")

        try:
            # Run simulation, setting cwd ensures output files land in temp_dir
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,  # Don't raise exception on non-zero exit
                encoding='utf-8',
                errors='ignore',  # Ignore potential decoding errors from LTspice output
                cwd=temp_dir  # Critical: Run LTspice within the temp directory
            )

            print(f"LTSPICE exited with code: {result.returncode}")
            # print(f"LTSPICE stdout:\n{result.stdout}")  # Often empty in batch mode
            # print(f"LTSPICE stderr:\n{result.stderr}")  # Can contain errors or info

            log_content = ""
            if os.path.isfile(log_filepath):
                print(f"Log file found: {log_filepath}")
                try:
                    with open(log_filepath, 'r', encoding='utf-8', errors='ignore') as lf:
                        log_content = lf.read()
                    # print(f"Log Content:\n{log_content}")
                except IOError as e:
                    print(f"Warning: Could not read log file {log_filepath}: {e}")
            else:
                print(f"Log file not found: {log_filepath}")

            # --- Check Results ---
            raw_file_exists = os.path.isfile(raw_filepath)
            if raw_file_exists:
                print(f"RAW file found: {raw_filepath}")
            else:
                print(f"RAW file not found: {raw_filepath}")

            if result.returncode == 0 and raw_file_exists:
                success_msg = f"LTSPICE simulation completed successfully.\nOutput Raw file: {raw_filepath}"
                if os.path.isfile(log_filepath):
                    success_msg += f"\nLog file: {log_filepath}"
                return True, success_msg, raw_filepath, log_filepath, temp_dir
            else:
                # Simulation failed or didn't produce a .raw file
                error_msg = f"LTSPICE simulation failed (Return Code: {result.returncode})."
                details = result.stderr.strip()
                if not details and log_content:  # If stderr is empty, use log content
                    details = log_content.strip()
                elif not details and not log_content:
                    details = "No specific error message captured. Check netlist syntax."

                error_msg += f"\nDetails:\n{details}"
                return False, error_msg, None, log_filepath if os.path.isfile(log_filepath) else None, temp_dir

        except FileNotFoundError:
            # This error now specifically refers to the provided path
            return False, f"Error: LTSPICE executable not found at '{ltspice_executable_path}'. Cannot run simulation.", None, None, temp_dir
        except Exception as e:
            return False, f"An unexpected error occurred while running LTSPICE: {e}", None, None, temp_dir

    except Exception as e:
        # Catch errors during temp dir creation or file writing setup
        error_message = f"Failed during simulation setup: {e}"
        # Cleanup if temp_dir was created before the error
        if temp_dir and os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory after setup error: {temp_dir}")
            except Exception as cleanup_e:
                print(f"Warning: Failed to cleanup temporary directory {temp_dir} after setup error: {cleanup_e}")
        return False, error_message, None, None, None  # temp_dir is None or cleaned up

def cleanup_simulation_files(temp_dir_path: str | None):
    """Safely removes the temporary simulation directory."""
    if temp_dir_path and os.path.isdir(temp_dir_path):
        try:
            shutil.rmtree(temp_dir_path)
            print(f"Successfully cleaned up simulation directory: {temp_dir_path}")
        except Exception as e:
            print(f"Warning: Failed to cleanup simulation directory {temp_dir_path}: {e}")
    elif temp_dir_path:
        print(f"Cleanup requested for non-existent directory: {temp_dir_path}")

# --- Add a test block ---
if __name__ == "__main__":
    print("--- Testing LTSPICE Runner ---")

    # Test Case 1: Valid Netlist (Simple RC Circuit with Transient Analysis)
    # Ensure this netlist includes a simulation command (e.g., .tran)
    valid_netlist = """
* Simple RC Circuit Example
V1 1 0 DC 5V
R1 1 2 1k
C1 2 0 1uF IC=0
.tran 0 5m 0 10u UIC ; Run transient analysis for 5ms
.end
"""
    print("\n--- Running Test Case 1: Valid Netlist ---")
    # Note: These tests now require a valid path passed manually
    # Example: Get path from settings or environment for testing
    test_ltspice_path = os.environ.get("LTSPICE_PATH") or r"C:\Program Files\ADI\LTspice\LTspice.exe" # Example fetch for test
    if not test_ltspice_path or not os.path.isfile(test_ltspice_path):
         print(f"SKIPPING TESTS: LTSPICE executable not found at '{test_ltspice_path}'")
    else:
        print(f"Using LTSPICE path for tests: {test_ltspice_path}")
        # --- Test Case 1 Execution ---
        success, message, raw_path, log_path, temp_dir = run_ltspice_simulation(valid_netlist, test_ltspice_path, "test_valid")
        print(f"\nResult (Test 1): Success={success}")
        print(f"Message (Test 1):\n{message}")
        print(f"Raw Path (Test 1): {raw_path}")
        print(f"Log Path (Test 1): {log_path}")
        print(f"Temp Dir (Test 1): {temp_dir}")
        # In a real test, you might assert raw_path is not None if success is True
        # Cleanup after test 1
        cleanup_simulation_files(temp_dir)

        # --- Test Case 2: Invalid Netlist (Syntax Error) ---
        invalid_netlist = """
* Invalid Circuit Example
V1 1 0 DC 5V
R1 1 2 1k OHMS ; Invalid unit specification
C1 2 0 1uF
.tran 1m
.end
"""
        print("\n--- Running Test Case 2: Invalid Netlist ---")
        success, message, raw_path, log_path, temp_dir = run_ltspice_simulation(invalid_netlist, test_ltspice_path, "test_invalid")
        print(f"\nResult (Test 2): Success={success}")
        print(f"Message (Test 2):\n{message}")
        print(f"Raw Path (Test 2): {raw_path}")
        print(f"Log Path (Test 2): {log_path}")
        print(f"Temp Dir (Test 2): {temp_dir}")
        # In a real test, you might assert success is False
        # Cleanup after test 2
        cleanup_simulation_files(temp_dir)

        # --- Test Case 3: Netlist missing simulation command ---
        no_sim_netlist = """
* No Simulation Command
V1 1 0 DC 5V
R1 1 0 1k
.end
"""
        print("\n--- Running Test Case 3: No Simulation Command ---")
        # LTspice might return 0 but not produce a .raw file without a simulation command
        success, message, raw_path, log_path, temp_dir = run_ltspice_simulation(no_sim_netlist, test_ltspice_path, "test_no_sim")
        print(f"\nResult (Test 3): Success={success}")
        print(f"Message (Test 3):\n{message}")
        print(f"Raw Path (Test 3): {raw_path}")
        print(f"Log Path (Test 3): {log_path}")
        print(f"Temp Dir (Test 3): {temp_dir}")
        # Expect success == False because .raw file won't be generated
        cleanup_simulation_files(temp_dir)

    # Test Case 4: Invalid Executable Path (Manual test - requires editing config.py temporarily)
    # print("\n--- Running Test Case 4: Invalid Executable Path ---")
    # Temporarily set LTSPICE_EXECUTABLE = "invalid/path/to/ltspice.exe" in config.py or env var
    # success, message, _, _, _ = run_ltspice_simulation(valid_netlist, "invalid/path", "test_invalid_exe") # Pass invalid path directly
    # print(f"\nResult: Success={success}")
    # print(f"Message:\n{message}")
    # Reset LTSPICE_EXECUTABLE afterwards!
    # Expect success == False because .raw file won't be generated
    cleanup_simulation_files(temp_dir)

    # Test Case 4: Invalid Executable Path (Manual test - requires editing config.py temporarily)
    # print("\n--- Running Test Case 4: Invalid Executable Path ---")
    # Temporarily set LTSPICE_EXECUTABLE = "invalid/path/to/ltspice.exe" in config.py or env var
    # success, message, _, _, _ = run_ltspice_simulation(valid_netlist, "test_invalid_exe")
    # print(f"\nResult: Success={success}")
    # print(f"Message:\n{message}")
    # Reset LTSPICE_EXECUTABLE afterwards!
