import os
import sys
import argparse
import importlib.util

# Configurable constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
PROJECT_NAME = "Neo_"  # Common project prefix
DEFAULT_VERSION = "3.2"  # Default stable version

def parse_args():
    """Parses command-line arguments, only caring about --version for this launcher."""
    parser = argparse.ArgumentParser(
        description=f"Run a specific or stable version of {PROJECT_NAME}."
    )
    parser.add_argument(
        "-v", "--version",
        type=str,
        default=DEFAULT_VERSION,
        help=f"Specify the version to run (e.g., 2, 2.1.1.1). Defaults to {DEFAULT_VERSION}.",
    )
    
    # parse_known_args: returns (known_args, unknown_args)
    known_args, unknown_args = parser.parse_known_args()
    return known_args, unknown_args

def find_version_folder(version):
    """Find the folder matching the specified version. The folder should start with PROJECT_NAME and end with 'v{version}'."""
    for folder in os.listdir(BASE_DIR):
        if folder.startswith(PROJECT_NAME) and folder.endswith(f"v{version}"):
            return folder
    return None

def run_version_main(folder_name, unknown_args):
    """Run the main.py file of the specified version, forwarding unknown_args."""
    version_path = os.path.join(BASE_DIR, folder_name, "main.py")
    if not os.path.exists(version_path):
        print(f"Error: {folder_name} does not have a main.py file.")
        sys.exit(1)

    print(f"Loading and running: {version_path}")
    print(f"Forwarded arguments to versioned main.py: {unknown_args}")

    # Forward unknown_args to the versioned script
    sys.argv = [version_path] + unknown_args
    print("sys.argv in versioned main.py:", sys.argv)

    try:
        # Dynamically load and execute the version-specific main.py file
        spec = importlib.util.spec_from_file_location("version_main", version_path)
        version_main = importlib.util.module_from_spec(spec)
        sys.modules["version_main"] = version_main
        spec.loader.exec_module(version_main)

        # Check if `main` function exists in the loaded module
        if hasattr(version_main, "main") and callable(version_main.main):
            version_main.main()
        else:
            print(f"Error: No `main` function found in {version_path}.")
            sys.exit(1)
    except Exception as e:
        print(f"Error while executing {version_path}: {e}")
        sys.exit(1)

def main():
    """Main function to handle version selection and execution."""
    known_args, unknown_args = parse_args()
    print("Known args for launcher:", known_args)
    print("Unknown args for versioned main.py:", unknown_args)

    selected_version = known_args.version

    # Find the folder matching the specified version
    folder_name = find_version_folder(selected_version)
    if not folder_name:
        print(f"Error: No folder found for version 'v{selected_version}' under '{PROJECT_NAME}'.")
        sys.exit(1)

    print(f"Running {folder_name}...")
    run_version_main(folder_name, unknown_args)

if __name__ == "__main__":
    main()
