#!/usr/bin/env python
"""
Initialize the database for the Facebook Ads Telegram Bot.
Supports environment selection via command line arguments.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)

def initialize_database(environment=None):
    """Initialize the database, creating all tables.
    
    Args:
        environment (str, optional): Environment to initialize ('development', 'production').
            If None, uses the ENVIRONMENT environment variable or defaults to 'development'.
    """
    if environment:
        os.environ["ENVIRONMENT"] = environment
    
    logger.info(f"Starting database initialization for {os.getenv('ENVIRONMENT', 'default')} environment...")
    
    try:
        # Import after setting environment to ensure correct configuration is loaded
        from src.storage.database import init_db
        # Create all tables
        init_db()
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the database for the Facebook Ads Telegram Bot.")
    parser.add_argument(
        "--env", "-e", 
        choices=["development", "production"], 
        default=os.getenv("ENVIRONMENT", "development"),
        help="Environment to initialize (default: development)"
    )
    
    args = parser.parse_args()
    
    if initialize_database(args.env):
        print(f"✅ Database initialized successfully for {args.env} environment.")
        sys.exit(0)
    else:
        print(f"❌ Database initialization failed for {args.env} environment. Check the logs for details.")
        sys.exit(1) 