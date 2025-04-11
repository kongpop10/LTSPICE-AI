# file_utils.py
import os
import platform
import subprocess
import sys  # sys needed for platform check refinement

def open_file_with_default_app(filepath: str) -> bool:
    """
    Opens a file using the system's default application.

    Args:
        filepath: The path to the file to open.

    Returns:
        True if the command to open the file was issued successfully, False otherwise.
    """
    if not os.path.exists(filepath):
        print(f"Error: File not found at '{filepath}'")
        return False

    system = platform.system()
    print(f"Attempting to open '{os.path.basename(filepath)}' on {system}...")

    try:
        if system == "Windows":
            os.startfile(os.path.abspath(filepath))  # Use abspath for reliability
        elif system == "Darwin":  # macOS
            subprocess.run(['open', filepath], check=True)
        elif system == "Linux":
            # Check if running under WSL, as xdg-open might not work directly with Windows apps
            # This check might need refinement depending on WSL setup
            if 'microsoft' in platform.uname().release.lower():
                print("Running under WSL? Trying explorer.exe...")
                try:
                    # Convert Linux path to Windows path if possible
                    windows_path = subprocess.check_output(['wslpath', '-w', filepath]).strip().decode()
                    # Using 'explorer.exe' might be more robust for files associated with Windows apps
                    subprocess.run(['explorer.exe', windows_path], check=True)
                except subprocess.CalledProcessError:
                    # Fallback to xdg-open if wslpath fails
                    subprocess.run(['xdg-open', filepath], check=True)
            else:
                subprocess.run(['xdg-open', filepath], check=True)
        else:
            print(f"Warning: Unsupported operating system '{system}'. Cannot open file automatically.")
            return False
        print(f"Successfully issued command to open '{os.path.basename(filepath)}'.")
        return True
    except FileNotFoundError as e:
        # Specific error if 'open' or 'xdg-open' or 'explorer.exe' isn't found
        print(f"Error: Command not found to open the file ({e}). Is the required utility installed?")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed while trying to open the file: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while trying to open the file: {e}")
        return False

# --- Add a simple test block ---
if __name__ == "__main__":
    print("--- Testing File Opener ---")
    # Create a dummy file to test
    test_filename = "test_open_file.txt"
    try:
        with open(test_filename, "w") as f:
            f.write("This is a test file for the open_file_with_default_app function.")
        print(f"Created dummy file: {test_filename}")

        # Test opening the file
        success = open_file_with_default_app(test_filename)
        print(f"Open attempt result: {success}")

        # Test opening a non-existent file
        print("\n--- Testing non-existent file ---")
        success_non_existent = open_file_with_default_app("non_existent_file.xyz")
        print(f"Open attempt result (non-existent): {success_non_existent}")

    finally:
        # Clean up the dummy file
        if os.path.exists(test_filename):
            os.remove(test_filename)
            print(f"Cleaned up dummy file: {test_filename}")
