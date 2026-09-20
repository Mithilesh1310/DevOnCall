#!/usr/bin/env python3
import sys
import subprocess
import os

def run_tests():
    print("==========================================")
    print("   DevOnCall - Running Backend Pytest     ")
    print("==========================================")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(project_root, "apps", "api")

    cmd = [sys.executable, "-m", "pytest", os.path.join(api_dir, "tests"), "-v"]
    print(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=api_dir)
    if result.returncode == 0:
        print("\n✅ All tests passed successfully!")
    else:
        print(f"\n❌ Tests failed with exit code: {result.returncode}")
    sys.exit(result.returncode)

if __name__ == "__main__":
    run_tests()
