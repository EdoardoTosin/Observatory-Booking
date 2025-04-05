"""
Database Models Module

This module defines the ORM models for the application using SQLAlchemy.
It includes models for application configuration, users, event slots, and bookings.
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
from sqlalchemy.orm import relationship, DeclarativeBase
from .utils import encrypt_data, decrypt_data

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
        max_bookings_per_event (int): Default maximum bookings allowed per slot.
        default_opening_time (time): Default slot start time (local time).
        default_closing_time (time): Default slot end time (local time).
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
    )

    @staticmethod
    def get_config(session: "Session") -> "Configuration":
        """
        Retrieve the current configuration from the database.

        If none exists, a default configuration is created and persisted.

        Args:
            session (Session): SQLAlchemy session instance.

        Returns:
            Configuration: The configuration object.
        """
        config: Optional[Configuration] = session.query(Configuration).first()
        if not config:
            config = Configuration()
            session.add(config)
            session.commit()
        return config


class User(Base):
    """
    User model representing a system user.

    Stores encrypted user data and securely hashed passwords.
    Provides methods for setting/verifying passwords and handling encrypted fields.

    Attributes:
        id (int): Primary key.
        name_encrypted (str): AES-encrypted user name.
        email_encrypted (str): AES-encrypted email address.
        password_hash (str): Bcrypt-hashed password.
        role (str): Role (User/Admin), default is 'User'.
        blocked (bool): True if user is blocked.
        admin_rank (Optional[str]): Admin rank if applicable (e.g., 'super').
        bookings (relationship): One-to-many relationship with Booking.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name_encrypted = Column(String(50), nullable=False, unique=True)
    email_encrypted = Column(String(255), nullable=False, unique=True, index=True)
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
        """
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
        """Encrypt and store the user's name."""
        self.name_encrypted = encrypt_data(name)

    def get_name(self):
        """Decrypt and return the user's name."""
        return decrypt_data(self.name_encrypted)


class Slot(Base):  # pylint: disable=too-few-public-methods
    """
    Slot model representing an event slot available for booking.

    Attributes:
        id (int): Primary key.
        title (str): Short title for the slot.
        description (str): Description or purpose of the slot.
        start_time (datetime): Slot start time (UTC).
        end_time (datetime): Slot end time (UTC).
        available (bool): True if the slot is available.
        weather_rating (Optional[float]): Weather suitability rating (0-100).
        max_bookings (int): Max bookings allowed for this slot.
        weather_warning (bool): True if weather is unfavorable.
        weather_forecast (bool): True if forecast data is present.
        bookings (relationship): One-to-many relationship with Booking.
    """

    __tablename__ = "slots"

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
        "Booking", back_populates="slot", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("start_time < end_time", name="check_slot_time_range"),
        CheckConstraint(
            "weather_rating IS NULL OR (weather_rating >= 0 AND weather_rating <= 100)",
            name="check_weather_rating_range",
        ),
        CheckConstraint("max_bookings >= 0", name="check_max_bookings_per_slot"),
    )


class Booking(Base):  # pylint: disable=too-few-public-methods
    """
    Booking model representing a user booking for a slot.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to User.
        slot_id (int): Foreign key to Slot.
        status (str): Booking status (e.g., 'confirmed').
        user (relationship): Many-to-one link to User.
        slot (relationship): Many-to-one link to Slot.
    """

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False, index=True)
    status = Column(String(20), default="confirmed")

    user = relationship("User", back_populates="bookings")
    slot = relationship("Slot", back_populates="bookings")

    __table_args__ = (
        CheckConstraint(
            "status IN ('confirmed', 'pending', 'cancelled')",
            name="check_booking_status",
        ),
        UniqueConstraint("user_id", "slot_id", name="uq_user_slot_booking"),
    )
