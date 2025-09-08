#!/usr/bin/env python3
"""
Simple test to verify the server can start
"""
import subprocess
import sys
import time
import os

def test_server_startup():
    print("Testing server startup...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    
    # Check if server.py exists
    if not os.path.exists("server.py"):
        print("❌ ERROR: server.py not found!")
        return False
    
    print("✅ server.py found")
    
    # Try to start the server
    try:
        print("Starting server process...")
        process = subprocess.Popen(
            [sys.executable, "-u", "server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a few seconds
        time.sleep(5)
        
        # Check if process is still running
        return_code = process.poll()
        
        if return_code is None:
            print("✅ Server started successfully and is still running!")
            process.terminate()
            process.wait()
            return True
        else:
            print(f"❌ Server process terminated with code: {return_code}")
            
            # Read output
            stdout, stderr = process.communicate()
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

if __name__ == "__main__":
    success = test_server_startup()
    if success:
        print("\n🎉 Server test passed!")
    else:
        print("\n❌ Server test failed. Fix the server issues first.")
        
        print("\nTroubleshooting checklist:")
        print("1. Check that all dependencies are installed:")
        print("   pip install -r requirements.txt")
        print("2. Test importing your modules:")
        print("   python -c 'from app.services import poke_api_client'")
        print("3. Check your server.py file for syntax errors")