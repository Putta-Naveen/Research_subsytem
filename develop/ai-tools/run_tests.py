"""
Run all tests for the project.

This script runs pytest with common options.
"""

import sys
import subprocess
import argparse


def main():
    """Run the tests with the specified arguments."""
    parser = argparse.ArgumentParser(description="Run tests for AI Tools")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--cov", action="store_true", help="Run with coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", help="Specific test file to run")
    
    args = parser.parse_args()
    
    # Build the pytest command using conda environment
    cmd = ["C:/Users/pnave/anaconda3/Scripts/conda.exe", "run", "-p", "C:/Users/pnave/develop/ai-tools/backend/venv", "python", "-m", "pytest"]
    
    
    if args.unit:
        cmd.append("tests/unit")
    elif args.integration:
        cmd.append("tests/integration")
    elif args.file:
        cmd.append(args.file)
    
    if args.verbose:
        cmd.append("-v")
    
    if args.cov:
        cmd.append("--cov=backend")
        if args.html:
            cmd.append("--cov-report=html")
        else:
            cmd.append("--cov-report=term")
    
    # Run the tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
