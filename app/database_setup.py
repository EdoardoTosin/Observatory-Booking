"""Database setup module.

This module provides utility functions for configuring a SQLAlchemy engine and creating
a thread-safe scoped session for database interactions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from .utils import get_env_value, logger


def get_database_url():
    """
    Retrieve the database connection URL from environment variables.

    If the 'DATABASE_URL' environment variable is unset or empty, defaults to a local
    SQLite database file named 'observatory_booking.db'.

    Returns:
        str: A valid SQLAlchemy database connection URL.

    Note:
        Logs a warning and defaults to SQLite if the URL is missing.
    """
    database_url = get_env_value(
        "DATABASE_URL", "sqlite:///observatory_booking.db"
    ).strip()

    if not database_url:
        logger.warning("DATABASE_URL is not set. Using default SQLite database.")
        database_url = "sqlite:///observatory_booking.db"

    return database_url


def create_db_session():
    """
    Create and configure a SQLAlchemy scoped session and engine for database access.

    This function performs the following:
    - Retrieves the database connection URL.
    - Determines environment mode (development or production) from the 'ENV' variable.
    - Configures the SQLAlchemy engine with connection pooling and debug options.
    - Creates a thread-safe scoped session for concurrent use.

    Returns:
        tuple[scoped_session, Engine]:
            - session_local (scoped_session): A thread-safe SQLAlchemy session factory.
            - engine (Engine): The SQLAlchemy engine bound to the session.

    Raises:
        SQLAlchemyError: If engine creation or session configuration fails.
    """
    try:
        database_url = get_database_url()

        is_dev_mode = get_env_value("ENV", "production").lower() == "development"

        engine = create_engine(
            database_url,
            connect_args=(
                {"check_same_thread": False} if "sqlite:///" in database_url else {}
            ),
            pool_size=10 if is_dev_mode else 20,
            max_overflow=5 if is_dev_mode else 30,
            pool_timeout=10 if is_dev_mode else 30,
            echo=is_dev_mode,
        )

        session_local = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=engine)
        )

        logger.info("Database connection established successfully.")
        return session_local, engine

    except (ValueError, SQLAlchemyError) as e:
        logger.error("Failed to set up the database session: %s", e)
        raise
