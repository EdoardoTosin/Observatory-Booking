"""
Database Models Module

This module defines the ORM models for the application using SQLAlchemy.
It includes models for application configuration, users, events, and bookings.
"""

from datetime import time
from typing import Optional, TYPE_CHECKING

import bcrypt
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Time,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from .utils import encrypt_data, decrypt_data, MAX_NAME_LENGTH

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """Base class for declarative SQLAlchemy models."""


class Configuration(Base):  # pylint: disable=too-few-public-methods
    """
    Configuration settings for the application.

    Stores global settings that influence system behavior, such as location,
    timezone, weather sensitivity, and default operational hours.

    Attributes:
        id (int): Primary key.
        latitude (float): Geographic latitude (-90 to 90).
        longitude (float): Geographic longitude (-180 to 180).
        timezone (str): IANA timezone string.
        weather_threshold (int): Minimum acceptable weather rating (0-100).
        max_bookings_per_event (int): Default maximum bookings allowed per event.
        default_opening_time (time): Default event start time (local time).
        default_closing_time (time): Default event end time (local time).
    """

    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False, default=41.8933203)
    longitude = Column(Float, nullable=False, default=12.4829321)
    timezone = Column(String(50), nullable=False, default="Europe/Rome")
    weather_threshold = Column(Integer, nullable=False, default=70)
    max_bookings_per_event = Column(Integer, nullable=False, default=10)
    default_opening_time = Column(Time, nullable=False, default=time(17, 0))
    default_closing_time = Column(Time, nullable=False, default=time(22, 0))

    __table_args__ = (
        CheckConstraint("-90 <= latitude <= 90", name="check_latitude"),
        CheckConstraint("-180 <= longitude <= 180", name="check_longitude"),
        CheckConstraint(
            "0 <= weather_threshold <= 100", name="check_weather_threshold"
        ),
        CheckConstraint("max_bookings_per_event >= 1", name="check_max_bookings"),
        # Only one configuration row may ever exist. Without this, concurrent
        # first-time get_config() calls could each insert their own row, and
        # subsequent reads/writes would nondeterministically target different
        # rows depending on query order.
        CheckConstraint("id = 1", name="check_configuration_singleton"),
    )

    @staticmethod
    def get_config(session: "Session") -> "Configuration":
        """
        Retrieve the current configuration from the database.

        If none exists, a default configuration is created and persisted.
        Concurrent first-time creation is handled safely: if another thread
        wins the race to insert the singleton row, this falls back to
        reading the row it created instead of failing.

        Args:
            session (Session): SQLAlchemy session instance.

        Returns:
            Configuration: The configuration object.
        """
        config: Optional[Configuration] = (
            session.query(Configuration).filter_by(id=1).first()
        )
        if not config:
            config = Configuration(id=1)
            session.add(config)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                config = session.query(Configuration).filter_by(id=1).first()
        if config is None:
            raise RuntimeError("Failed to load or create the configuration row.")
        return config


class User(Base):
    """
    User model representing a system user.

    Stores encrypted user data and securely hashed passwords.
    Provides methods for setting/verifying passwords and handling encrypted fields.

    Attributes:
        id (int): Primary key.
        name (str): Plaintext user name. Low-sensitivity, frequently-displayed
            data (admin dashboard, bookings), so it is not encrypted like
            email; this avoids an AES-GCM decrypt on every row rendered.
        email_encrypted (str): AES-encrypted email address.
        password_hash (str): Bcrypt-hashed password.
        role (str): Role (User/Admin), default is 'User'.
        blocked (bool): True if user is blocked.
        admin_rank (Optional[str]): Admin rank if applicable (e.g., 'super').
        bookings (relationship): One-to-many relationship with Booking.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(MAX_NAME_LENGTH), nullable=False, unique=True
    )
    # Sized for base64(nonce + ciphertext + tag) of a MAX_EMAIL_LENGTH
    # plaintext, not the plaintext length itself.
    email_encrypted: Mapped[str] = mapped_column(
        String(400), nullable=False, unique=True, index=True
    )
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), default="User")
    blocked = Column(Boolean, default=False)
    admin_rank = Column(String(10), nullable=True)

    bookings = relationship(
        "Booking", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "LENGTH(password_hash) >= 60", name="check_password_hash_length"
        ),
        CheckConstraint("role IN ('User', 'Admin')", name="check_user_role"),
        CheckConstraint(
            "admin_rank IS NULL OR admin_rank = 'super'",
            name="check_admin_rank_super_only",
        ),
    )

    def __init__(
        self, name, email, password, role="User", admin_rank=None
    ):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """
        Initialize a new user instance with encrypted fields and a hashed password.

        Args:
            name (str): Plaintext name.
            email (str): Plaintext email address.
            password (str): Plaintext password.
            role (str): Role (default is 'User').
            admin_rank (Optional[str]): Admin rank if applicable (e.g., 'super'). Defaults to None.
        """
        super().__init__()
        self.set_name(name)
        self.set_email(email)
        self.set_password(password)
        self.role = role
        self.admin_rank = admin_rank

    def set_password(self, password):
        """Hash and securely store the user's password."""
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(12)
        ).decode(
            "utf-8"
        )  # type: ignore[assignment]

    def verify_password(self, password):
        """Check if the provided password matches the stored hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def set_email(self, email):
        """Encrypt and store the user's email."""
        self.email_encrypted = encrypt_data(email)

    def get_email(self):
        """Decrypt and return the user's email."""
        return decrypt_data(self.email_encrypted)

    def set_name(self, name):
        """Store the user's name."""
        self.name = name

    def get_name(self):
        """Return the user's name."""
        return self.name


class Event(Base):  # pylint: disable=too-few-public-methods
    """
    Event model representing an observatory event available for booking.

    Attributes:
        id (int): Primary key.
        title (str): Short title for the event.
        description (str): Description or purpose of the event.
        start_time (datetime): Event start time (UTC).
        end_time (datetime): Event end time (UTC).
        available (bool): True if the event is available.
        weather_rating (Optional[float]): Weather suitability rating (0-100).
        max_bookings (int): Max bookings allowed for this event.
        weather_warning (bool): True if weather is unfavorable.
        weather_forecast (bool): True if forecast data is present.
        bookings (relationship): One-to-many relationship with Booking.
    """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(30), nullable=False, default="")
    description = Column(String(255), nullable=False, default="")
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    available = Column(Boolean, default=True)
    weather_rating = Column(Float, nullable=True)
    max_bookings = Column(Integer, nullable=False, default=10)
    weather_warning = Column(Boolean, default=False)
    weather_forecast = Column(Boolean, default=False)

    bookings = relationship(
        "Booking", back_populates="event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("start_time < end_time", name="check_event_time_range"),
        CheckConstraint(
            "weather_rating IS NULL OR (weather_rating >= 0 AND weather_rating <= 100)",
            name="check_weather_rating_range",
        ),
        CheckConstraint("max_bookings >= 0", name="check_max_bookings_per_event"),
        # Mirrors the length limits already enforced in AdminService, at the
        # database level, so a validation gap can't silently persist an
        # oversized title/description.
        CheckConstraint("LENGTH(title) <= 30", name="check_title_length"),
        CheckConstraint("LENGTH(description) <= 255", name="check_description_length"),
    )


class Booking(Base):  # pylint: disable=too-few-public-methods
    """
    Booking model representing a user booking for an event.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        event_id (int): Foreign key to Event.
        status (str): Booking status. Only 'confirmed' is ever persisted;
            cancellation hard-deletes the row rather than transitioning
            status, so no other value is valid.
        user (relationship): Many-to-one link to User.
        event (relationship): Many-to-one link to Event.
    """

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    status = Column(String(20), default="confirmed")

    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")

    __table_args__ = (
        CheckConstraint(
            "status = 'confirmed'",
            name="check_booking_status",
        ),
        UniqueConstraint("user_id", "event_id", name="uq_user_event_booking"),
    )
