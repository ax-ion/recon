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

def get_current_branch():
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    return result.stdout.strip()

def checkout_branch(branch):
    print(f"🔀 Checking out branch: {branch}")
    subprocess.run(["git", "checkout", branch], cwd=BASE_DIR, check=True)

def run_main(args):
    cmd = [sys.executable, NEO_MAIN] + args
    print(f"🚀 Running: {' '.join(cmd)}")
    subprocess.run(cmd)

def main():
    args, extra = parse_args()
    starting_branch = get_current_branch()

    try:
        if args.branch:
            checkout_branch(args.branch)
        run_main(extra)
    finally:
        if args.branch and starting_branch != "master":
            print("🔁 Returning to master branch...")
            try:
                checkout_branch("master")
            except Exception as e:
                print(f"⚠️  Failed to return to master: {e}")

if __name__ == "__main__":
    main()
