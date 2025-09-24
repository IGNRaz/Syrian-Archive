#!/usr/bin/env python3
"""
Test Runner for Syrian Archive API
Runs both standalone API tests and Django integrated tests
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_standalone_tests(base_url="http://127.0.0.1:8000"):
    """Run standalone API tests"""
    print("\n" + "=" * 60)
    print("RUNNING STANDALONE API TESTS")
    print("=" * 60)
    
    try:
        # Run the standalone test script
        result = subprocess.run([
            sys.executable, 
            "test_api_endpoints.py", 
            "--url", base_url
        ], capture_output=False, text=True)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: test_api_endpoints.py not found")
        return False
    except Exception as e:
        print(f"Error running standalone tests: {e}")
        return False

def run_django_tests():
    """Run Django integrated tests"""
    print("\n" + "=" * 60)
    print("RUNNING DJANGO INTEGRATED TESTS")
    print("=" * 60)
    
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')
        
        # Run Django tests
        result = subprocess.run([
            sys.executable, 
            "manage.py", 
            "test", 
            "tests.test_api_comprehensive",
            "--verbosity=2"
        ], capture_output=False, text=True)
        
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: manage.py not found or Django not properly configured")
        return False
    except Exception as e:
        print(f"Error running Django tests: {e}")
        return False

def check_server_running(base_url):
    """Check if the Django server is running"""
    import requests
    try:
        response = requests.get(f"{base_url}/api/", timeout=5)
        return True
    except requests.exceptions.RequestException:
        return False

def start_test_server():
    """Start Django test server"""
    print("Starting Django test server...")
    try:
        # Start server in background
        process = subprocess.Popen([
            sys.executable, 
            "manage.py", 
            "runserver", 
            "127.0.0.1:8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a bit for server to start
        import time
        time.sleep(3)
        
        return process
    except Exception as e:
        print(f"Error starting test server: {e}")
        return None

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Syrian Archive API Test Runner')
    parser.add_argument('--url', default='http://127.0.0.1:8000', 
                       help='Base URL for API tests (default: http://127.0.0.1:8000)')
    parser.add_argument('--standalone-only', action='store_true',
                       help='Run only standalone API tests')
    parser.add_argument('--django-only', action='store_true',
                       help='Run only Django integrated tests')
    parser.add_argument('--start-server', action='store_true',
                       help='Start Django server before running tests')
    parser.add_argument('--install-deps', action='store_true',
                       help='Install test dependencies before running')
    
    args = parser.parse_args()
    
    print("Syrian Archive API Test Suite")
    print("=" * 60)
    
    # Install dependencies if requested
    if args.install_deps:
        print("Installing test dependencies...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"], 
                         check=True)
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError:
            print("Warning: Failed to install some dependencies.")
        except FileNotFoundError:
            print("Warning: test_requirements.txt not found.")
    
    server_process = None
    
    # Start server if requested
    if args.start_server:
        server_process = start_test_server()
        if not server_process:
            print("Failed to start test server. Exiting.")
            return 1
    
    try:
        success = True
        
        # Run Django tests
        if not args.standalone_only:
            django_success = run_django_tests()
            success = success and django_success
            
            if django_success:
                print("\n✅ Django integrated tests PASSED")
            else:
                print("\n❌ Django integrated tests FAILED")
        
        # Run standalone tests
        if not args.django_only:
            # Check if server is running
            if not check_server_running(args.url):
                print(f"\n⚠️  Warning: Server not responding at {args.url}")
                print("   Make sure Django server is running for standalone tests.")
                print("   Use --start-server flag to start it automatically.")
            
            standalone_success = run_standalone_tests(args.url)
            success = success and standalone_success
            
            if standalone_success:
                print("\n✅ Standalone API tests PASSED")
            else:
                print("\n❌ Standalone API tests FAILED")
        
        # Print final results
        print("\n" + "=" * 60)
        if success:
            print("🎉 ALL TESTS PASSED!")
            return_code = 0
        else:
            print("💥 SOME TESTS FAILED!")
            return_code = 1
        print("=" * 60)
        
        return return_code
    
    finally:
        # Clean up server process
        if server_process:
            print("\nStopping test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)