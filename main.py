import importlib.util
import os
import sys

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_MAIN = os.path.join(BASE_DIR, "Neo", "main.py")

def main():
    if not os.path.exists(TARGET_MAIN):
        print(f"Error: Neo/main.py not found at {TARGET_MAIN}")
        sys.exit(1)

    print(f"Running: {TARGET_MAIN}")
    print(f"Args: {sys.argv[1:]}")

    sys.argv = [TARGET_MAIN] + sys.argv[1:]

    spec = importlib.util.spec_from_file_location("neo_main", TARGET_MAIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "main") and callable(module.main):
        module.main()
    else:
        print("Warning: No 'main' function found. Execution complete.")

if __name__ == "__main__":
    main()
