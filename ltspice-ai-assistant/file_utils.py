# file_utils.py
import os
import platform
import subprocess

def get_file_path_from_upload(uploaded_file) -> tuple[str, str]:
    """
    Attempts to get the full file path from a Streamlit uploaded file.

    Args:
        uploaded_file: A file uploaded through Streamlit's file_uploader

    Returns:
        A tuple containing (file_path, file_name) where file_path is the full path
        if it can be determined, or None if it cannot. file_name is always the name
        of the uploaded file.
    """
    if uploaded_file is None:
        return None, None

    file_name = uploaded_file.name

    # Note: Due to security restrictions in browsers and Streamlit's file uploader,
    # we typically can't get the full original path of an uploaded file.
    # The code below is kept for potential future improvements or special cases
    # where the full path might be available.
    try:
        # Try to get the full path - this will likely fail in most cases
        # but we keep it for edge cases or future improvements
        full_path = os.path.abspath(file_name)
        if os.path.isfile(full_path):
            return full_path, file_name
    except Exception as e:
        print(f"Could not determine full path for {file_name}: {e}")

    # If we can't get the full path, return None for path but the name
    return None, file_name

def find_file_in_directory(filename, search_dir=None, max_depth=3) -> str:
    """
    Searches for a file with the given name in the specified directory and its subdirectories.

    Args:
        filename: The name of the file to search for
        search_dir: The directory to start the search from. If None, uses the current directory.
        max_depth: Maximum directory depth to search (to avoid searching the entire drive)

    Returns:
        The full path to the file if found, None otherwise.
    """
    if not filename:
        return None

    if search_dir is None:
        # Start with the current directory
        search_dir = os.getcwd()

    # Also check the saved_circuits directory if it's defined
    saved_circuits_dir = None
    try:
        # Try to get the saved_circuits directory relative to this file
        file_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(file_dir)
        potential_saved_dir = os.path.join(parent_dir, "saved_circuits")
        if os.path.isdir(potential_saved_dir):
            saved_circuits_dir = potential_saved_dir
    except Exception:
        pass

    # List of directories to search
    search_dirs = [search_dir]
    if saved_circuits_dir and saved_circuits_dir != search_dir:
        search_dirs.append(saved_circuits_dir)

    # Add common LTspice directories if on Windows
    if platform.system() == "Windows":
        potential_ltspice_dirs = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'LTspiceXVII'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'LTspice'),
            os.path.join('C:\\', 'Program Files', 'ADI', 'LTspice', 'examples'),
            os.path.join('C:\\', 'Program Files', 'LTC', 'LTspiceXVII', 'examples')
        ]
        for dir_path in potential_ltspice_dirs:
            if os.path.isdir(dir_path) and dir_path not in search_dirs:
                search_dirs.append(dir_path)

    # Helper function to search with depth limit
    def search_with_depth_limit(directory, current_depth=0):
        if current_depth > max_depth:
            return None

        # First check if the file is directly in this directory
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            return file_path

        # Then check subdirectories
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    result = search_with_depth_limit(item_path, current_depth + 1)
                    if result:
                        return result
        except (PermissionError, OSError):
            # Skip directories we can't access
            pass

        return None

    # Search in each directory with depth limit
    for directory in search_dirs:
        try:
            result = search_with_depth_limit(directory)
            if result:
                return result
        except Exception as e:
            print(f"Error searching in {directory}: {e}")

    return None

def select_directory_dialog(initial_dir=None) -> str:
    """
    Opens a directory selection dialog using tkinter.

    Args:
        initial_dir: The initial directory to open in the dialog.

    Returns:
        The selected directory path or None if canceled.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        # Create a root window but hide it
        root = tk.Tk()
        root.withdraw()

        # Try to bring the dialog to the front
        try:
            root.attributes('-topmost', True)
        except Exception:
            # Some platforms might not support this
            pass

        # Show the directory selection dialog
        selected_dir = filedialog.askdirectory(initialdir=initial_dir)

        # Destroy the root window
        root.destroy()

        return selected_dir if selected_dir else None
    except Exception as e:
        print(f"Error opening directory selection dialog: {e}")
        return None

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
