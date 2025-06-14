"""
Database configuration and connection management.
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from config.settings import (DB_CONNECTION_STRING, OWNER_FIRST_NAME, OWNER_ID,
                             OWNER_USERNAME)
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
    from src.storage.migrations.seed_permissions import seed_permissions
    from src.storage.models import User

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
            role="owner",  # Используем строковый идентификатор роли
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


def migrate_accounts_to_users():
    """
    Миграция существующих данных в таблицу accounts_to_users.
    Создает связи для всех существующих аккаунтов с их пользователями.
    """
    from src.storage.models import Account, User, accounts_to_users

    logger.info("Starting migration of existing accounts to accounts_to_users table...")

    session = get_session()
    try:
        # Получаем все существующие аккаунты
        accounts = session.query(Account).all()
        logger.info(f"Found {len(accounts)} accounts to migrate")

        # Для каждого аккаунта создаем связь с его пользователем
        for account in accounts:
            # Проверяем, существует ли уже такая связь
            existing_link = session.execute(
                accounts_to_users.select().where(
                    (accounts_to_users.c.user_id == account.telegram_id)
                    & (accounts_to_users.c.account_id == account.id)
                )
            ).first()

            if not existing_link:
                # Создаем новую связь
                session.execute(
                    accounts_to_users.insert().values(
                        user_id=account.telegram_id, account_id=account.id
                    )
                )
                logger.debug(
                    f"Created link for account {account.id} and user {account.telegram_id}"
                )

        session.commit()
        logger.info("Migration completed successfully")

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        session.rollback()
    finally:
        session.close()


def init_db():
    """Initialize the database, creating tables only if they don't exist."""
    from src.storage.models import (Account, Cache,  # Import models
                                    Permission, User)

    # Проверяем существование таблиц
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = ["users", "accounts", "cache", "permissions", "accounts_to_users"]

    if not all(table in existing_tables for table in required_tables):
        logger.info("Creating missing database tables...")
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")

        # Мигрируем существующие данные в accounts_to_users
        migrate_accounts_to_users()
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
