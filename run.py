#!/usr/bin/env python3
"""
Simple startup script for Agent Script Interface
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("Try running: pip install -r requirements.txt")
        return False

def check_files():
    """Check if required files exist"""
    required_files = ['app.py', 'index.html', 'requirements.txt']
    missing = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print(f"❌ Missing required files: {', '.join(missing)}")
        return False
    
    print("✅ All required files found")
    return True

def open_browser():
    """Open browser after delay"""
    time.sleep(3)
    webbrowser.open('http://localhost:5000')

def main():
    print("🚀 Starting Agent Script Interface...")
    
    # Check files
    if not check_files():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    print("\n✅ Setup complete!")
    print("🌐 Starting server on http://localhost:5000")
    print("📋 Server will automatically open in your browser")
    print("🛑 Press Ctrl+C to stop\n")
    
    # Open browser in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    from app import app
    try:
        app.run(debug=False, host='127.0.0.1', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()