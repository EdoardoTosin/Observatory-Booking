"""Booking system module.

This module defines the `BookingSystem` class, which serves as the central orchestrator
for the observatory booking application. It initializes the database and services, and
exposes unified methods for both administrative and user-facing functionalities.
"""

from threading import Lock

from .models import (  # pylint: disable=unused-import
    Base,
    User,
    Slot,
    Booking,
    Configuration,
)
from .utils import logger
from .database_setup import create_db_session
from .services.weather_service import WeatherService
from .services.admin_service import AdminService
from .services.user_service import UserService
from .services.booking_service import BookingService


class BookingSystem:
    """
    Central orchestrator for Observatory Booking Web App.

    Responsibilities:
    - Initialize the database and create tables.
    - Instantiate service layers for weather, admin, user, and booking domains.
    - Provide high-level methods for user management, event handling, and booking.

    Attributes:
        session_local (scoped_session): Thread-safe session factory for database access.
        lock (Lock): Synchronization primitive for thread-safe operations.
        weather_service (WeatherService): Manages weather updates and ratings.
        admin_service (AdminService): Handles admin operations and configurations.
        user_service (UserService): Manages user accounts and credentials.
        booking_service (BookingService): Processes slot bookings and cancellations.
    """

    def __init__(self):
        """
        Initialize the BookingSystem instance.

        Steps:
        - Set up a scoped SQLAlchemy session and create database tables if not present.
        - Instantiate core services with their dependencies.
        - Ensure a superadmin user exists for initial access.
        """
        self.session_local, engine = create_db_session()

        Base.metadata.create_all(bind=engine)

        self.lock = Lock()

        self.weather_service = WeatherService(self.session_local)
        self.admin_service = AdminService(
            db_session=self.session_local,
            lock=self.lock,
            weather_service=self.weather_service,
        )
        self.user_service = UserService(self.session_local, self.lock)
        self.booking_service = BookingService(self.session_local)

        try:
            self.admin_service._initialize_superadmin()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to initialize superadmin: %s", e)

        logger.info("Observatory Booking Web App initialized.")

    def __enter__(self):
        """
        Enter the context manager for resource setup.

        Returns:
            scoped_session: The active scoped session for database interaction.
        """
        logger.debug("Entering context: setting up resources.")
        return self.session_local

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        """
        Exit the context manager and perform cleanup.

        Args:
            exc_type: Exception type, if raised.
            exc_value: Exception instance, if raised.
            traceback: Traceback object, if exception occurred.

        Returns:
            bool: False to propagate any exception that occurred.
        """
        logger.debug("Exiting context: cleaning up resources.")
        self.session_local.remove()
        return False

    def shutdown(self):
        """
        Shutdown the booking system gracefully.

        Terminates background services (e.g., weather scheduler) and removes
        the scoped session to release database connections.
        """
        self.weather_service.shutdown()
        self.session_local.remove()

    def update_user_role(self, user_id, new_role):
        """
        Change a user's role.

        Args:
            user_id: Identifier of the user.
            new_role: Role to assign (e.g., 'admin', 'user').
        """
        self.admin_service.update_user_role(user_id, new_role)

    def block_user(self, user_id, block):
        """
        Block or unblock a user account.

        Args:
            user_id: Identifier of the user.
            block: True to block; False to unblock.
        """
        self.admin_service.block_user(user_id, block)

    def delete_user(self, user_id):
        """
        Delete a user account.

        Args:
            user_id: Identifier of the user.
        """
        self.admin_service.delete_user(user_id)

    def update_configuration(self, config):
        """
        Update system-wide configuration parameters.

        Args:
            config: Object containing updated configuration values.
        """
        self.admin_service.update_configuration(
            latitude=config.latitude,
            longitude=config.longitude,
            timezone=config.timezone_str,
            weather_threshold=config.weather_threshold,
            max_bookings_per_event=config.max_bookings_per_event,
            default_opening_time=config.default_opening_time,
            default_closing_time=config.default_closing_time,
        )

    def confirm_event(self, event, event_id=None):
        """
        Create or update an event slot.

        Args:
            event: Event data including time, description, and limits.
            event_id (int): Event ID.

        Returns:
            str: Status message about the confirmation result.
        """
        return self.admin_service.confirm_event(event, event_id=event_id)

    def update_events_weather(self):
        """
        Trigger weather updates for all scheduled events.
        """
        self.weather_service.update_events_weather()

    def book_slot(self, user_id, slot_id):
        """
        Book a slot for a user.

        Args:
            user_id: Identifier of the user making the booking.
            slot_id: Identifier of the slot to book.

        Returns:
            str: Status message about the booking result.
        """
        return self.booking_service.book_slot(user_id=user_id, slot_id=slot_id)

    def cancel_booking(self, user_id, slot_id):
        """
        Cancel a previously booked slot.

        Args:
            user_id: Identifier of the user.
            slot_id: Identifier of the slot to cancel.

        Returns:
            str: Status message about the cancellation result.
        """
        return self.booking_service.cancel_booking(user_id=user_id, slot_id=slot_id)

    def create_user_account(self, name, email, password):
        """
        Register a new user account.

        Args:
            name: User's full name.
            email: User's email address.
            password: User's password.

        Returns:
            User: The newly created user instance.
        """
        return self.user_service.create_user_account(
            name=name, email=email, password=password
        )

    def change_user_password(self, user_id, new_password):
        """
        Change the password for an existing user.

        Args:
            user_id: Identifier of the user.
            new_password: New password to assign.
        """
        self.user_service.change_user_password(
            user_id=user_id, new_password=new_password
        )
