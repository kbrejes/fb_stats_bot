"""
Database configuration and connection management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import inspect

from config.settings import DB_CONNECTION_STRING
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    DB_CONNECTION_STRING,
    echo=False,  # Set to True for debugging
    pool_pre_ping=True,  # Check connection before using it
)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Base class for all models
Base = declarative_base()

def init_db():
    """Initialize the database, creating tables only if they don't exist."""
    from src.storage.models import User, Account, Cache  # Import models
    
    # Проверяем существование таблиц
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = ['users', 'accounts', 'cache', 'permissions']
    
    if not all(table in existing_tables for table in required_tables):
        logger.info("Creating missing database tables...")
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    else:
        logger.debug("All required database tables already exist")

def get_session():
    """Get a database session.
    
    Returns:
        A new database session.
    """
    return Session()

def close_session(session):
    """Close a database session.
    
    Args:
        session: The session to close.
    """
    session.close()
    Session.remove() 