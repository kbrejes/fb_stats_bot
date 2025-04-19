#!/usr/bin/env python
"""
Run all tests for the Facebook Ads Telegram Bot.
"""
import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def run_tests():
    """
    Discover and run all tests in the tests directory.
    """
    print("Running tests for Facebook Ads Telegram Bot...")
    
    # Discover tests in the current directory and all subdirectories
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern="test_*.py")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    
    # Run tests
    sys.exit(run_tests()) 