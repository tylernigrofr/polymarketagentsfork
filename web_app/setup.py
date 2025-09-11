#!/usr/bin/env python3
"""
Setup script for Polymarket AI Predictions Web App
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"[SETUP] {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"[SUCCESS] {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"[SUCCESS] Python {version.major}.{version.minor} detected - compatible")
        return True
    else:
        print(f"[ERROR] Python {version.major}.{version.minor} detected - need Python 3.9+")
        return False

def install_requirements():
    """Install required packages"""
    if Path("requirements.txt").exists():
        return run_command("pip install -r requirements.txt", "Installing required packages")
    else:
        print("❌ requirements.txt not found")
        return False

def setup_env_file():
    """Set up environment file"""
    if Path(".env").exists():
        print("[SUCCESS] .env file already exists")
        return True

    if Path(".env.example").exists():
        print("[SETUP] Creating .env file from template...")
        try:
            # Copy .env.example to .env
            with open(".env.example", "r") as source:
                content = source.read()

            with open(".env", "w") as dest:
                dest.write(content)

            print("[SUCCESS] .env file created from template")
            print("[WARNING] IMPORTANT: Edit .env file with your actual API keys!")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create .env file: {e}")
            return False
    else:
        print("[ERROR] .env.example template not found")
        return False

def main():
    print("Polymarket AI Predictions Web App Setup")
    print("=" * 50)

    # Check Python version
    if not check_python_version():
        print("Please upgrade to Python 3.9 or higher")
        return

    # Install requirements
    if not install_requirements():
        print("Failed to install requirements. Please check your internet connection and try again.")
        return

    # Setup environment file
    if not setup_env_file():
        print("Failed to setup environment file.")
        return

    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("1. Edit the .env file with your actual API keys")
    print("2. Run: python run.py")
    print("3. Open http://localhost:8000 in your browser")
    print("\nFor help, see README.md")

if __name__ == "__main__":
    main()