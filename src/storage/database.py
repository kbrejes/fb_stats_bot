"""
Database configuration and connection management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import inspect

from config.settings import DB_CONNECTION_STRING, OWNER_ID, OWNER_USERNAME, OWNER_FIRST_NAME
from src.utils.logger import get_logger

DATABASE_URL = DB_CONNECTION_STRING

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

def create_owner(session):
    """Create owner user if it doesn't exist."""
    from src.storage.models import User
    from src.storage.migrations.seed_permissions import seed_permissions
    
    # Сначала создаем базовые разрешения
    seed_permissions()
    
    # Проверяем существование owner'а
    owner = session.query(User).filter(User.telegram_id == OWNER_ID).first()
    if not owner:
        logger.info(f"Creating owner user with ID {OWNER_ID}...")
        owner = User(
            telegram_id=OWNER_ID,
            username=OWNER_USERNAME,
            first_name=OWNER_FIRST_NAME,
            role="owner"  # Используем строковый идентификатор роли
        )
        session.add(owner)
        
        try:
            session.commit()
            logger.info("Owner user created successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create owner user: {e}")
            raise
    else:
        logger.debug("Owner user already exists")

def init_db():
    """Initialize the database, creating tables only if they don't exist."""
    from src.storage.models import User, Account, Cache, Permission  # Import models
    
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
    
    # Создаем сессию и owner'а
    session = get_session()
    try:
        create_owner(session)
    finally:
        close_session(session)

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