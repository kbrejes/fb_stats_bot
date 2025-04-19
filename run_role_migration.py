#!/usr/bin/env python
"""
Run migrations for role-based access control.
This script adds the role column to users table and creates necessary tables for access control.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.storage.migrations.role_access_migration import run_migrations
from src.utils.logger import setup_logging

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Run migrations
    print("Starting role-based access control migrations...")
    
    if run_migrations():
        print("✅ Role-based access control migrations completed successfully.")
        sys.exit(0)
    else:
        print("❌ Role-based access control migrations failed. Check the logs for details.")
        sys.exit(1) 