#!/usr/bin/env python3
"""
Simple script to run the Polymarket AI Predictions web app
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import python_dotenv
        import openai
        print("[SUCCESS] All required packages are installed")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing required package: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists"""
    if not Path('.env').exists():
        print("[WARNING] No .env file found")
        print("Creating template .env file...")
        create_env_template()
        print("Please edit .env with your API keys before running")
        return False
    return True

def create_env_template():
    """Create a template .env file"""
    template = """# Polymarket AI Predictions - Environment Configuration

# Required API Keys (choose one or both)
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional API Keys (for enhanced features)
TAVILY_API_KEY=your_tavily_search_key_here
NEWSAPI_API_KEY=your_newsapi_key_here

# Application Settings
ENVIRONMENT=development
DEBUG=true
USE_REAL_DATA=true
DEFAULT_MODEL=anthropic/claude-3-haiku
"""
    with open('.env', 'w') as f:
        f.write(template)

def run_server():
    """Run the FastAPI server"""
    print("Starting Polymarket AI Predictions Web App...")
    print("Web app will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)

    try:
        # Run the main server
        subprocess.run([
            sys.executable, "main.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Server failed to start: {e}")
        print("Make sure all dependencies are installed and .env is configured")
        print("Try running: python main.py")

def main():
    print("Polymarket AI Predictions Web App Launcher")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        return

    # Check environment
    if not check_env_file():
        return

    # Run the server
    run_server()

if __name__ == "__main__":
    main()