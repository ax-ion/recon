import os
import sys
import argparse
import glob
import importlib.util

# Dynamically set the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Mapping of version numbers to folder names
VERSION_MAP = {
    "1": "Neo_Alpha",
    "2": "Neo_Beta",
    "2.1": "Neo_ReleaseCandidate",
    "3": "Neo_Stable",
}

def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Run a specific Neo version.")
    parser.add_argument(
        "-v", "--version", type=str, help="Specify the Neo version number (e.g., 2 or 2.1)."
    )
    return parser.parse_args()

def resolve_version(version):
    """Resolves a version number to the corresponding folder name."""
    if version in VERSION_MAP:
        return VERSION_MAP[version]
    print(f"Error: Version '{version}' not found. Available versions: {', '.join(VERSION_MAP.keys())}")
    sys.exit(1)

def find_latest_version():
    """Finds the latest version folder based on the mapping."""
    sorted_versions = sorted(VERSION_MAP.keys(), key=lambda x: [int(i) if i.isdigit() else i for i in x.split(".")])
    latest_version = sorted_versions[-1]
    return VERSION_MAP[latest_version]

def run_version_main(version_folder):
    """Runs the main.py file of the specified version folder."""
    version_path = os.path.join(BASE_DIR, version_folder, "main.py")
    if not os.path.exists(version_path):
        print(f"Error: {version_folder} does not have a main.py file.")
        sys.exit(1)

    # Load and execute the version's main.py file
    spec = importlib.util.spec_from_file_location("main", version_path)
    version_main = importlib.util.module_from_spec(spec)
    sys.modules["version_main"] = version_main
    spec.loader.exec_module(version_main)
    version_main.main()

def main():
    args = parse_args()
    selected_version_folder = None

    if args.version:
        # Resolve the user-specified version to the folder name
        selected_version_folder = resolve_version(args.version)
    else:
        # Default to the latest version
        selected_version_folder = find_latest_version()

    print(f"Running version: {selected_version_folder}")
    run_version_main(selected_version_folder)

if __name__ == "__main__":
    main()
