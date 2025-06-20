#!/usr/bin/env python

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEO_MAIN = os.path.join(BASE_DIR, "Neo", "main.py")

def parse_args():
    parser = argparse.ArgumentParser(description="Run Neo from a specific Git branch.")
    parser.add_argument("-b", "--branch", type=str, help="Git branch to checkout before running Neo")
    args, remaining = parser.parse_known_args()
    return args, remaining

def checkout_branch(branch):
    try:
        print(f"Checking out branch: {branch}")
        subprocess.run(["git", "checkout", branch], cwd=BASE_DIR, check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Failed to checkout branch '{branch}'.")
        sys.exit(1)

def run_main(args):
    cmd = [sys.executable, NEO_MAIN] + args
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

def main():
    args, extra = parse_args()
    if args.branch:
        checkout_branch(args.branch)
    run_main(extra)

if __name__ == "__main__":
    main()
