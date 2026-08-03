"""
Booking Service Module

This module provides a service class for managing event bookings and cancellations.
It ensures concurrency safety, rate-limiting, and event availability checks.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from threading import Lock

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from ..models import User, Event, Booking, Configuration
from ..utils import logger, is_rate_limited


class BookingService:
    """
    Service class for managing event bookings and cancellations.

    This class ensures:
    - Thread-safe operations
    - Rate limiting enforcement
    - Event availability validation
    - User permission checks
    """

    def __init__(self, db_session) -> None:
        """
        Initialize the BookingService with a database session factory.

        Args:
            db_session (Callable[[], Session]): A callable returning a new database session.
        """
        self.db = db_session
        self.lock = Lock()

    def _get_timezone(self, db):
        """
        Retrieve the configured timezone from the system configuration.

        Args:
            db (Session): Active database session.

        Returns:
            ZoneInfo: The configured timezone object.
        """
        config = Configuration.get_config(db)
        return ZoneInfo(str(config.timezone))

    def _get_current_time(self, db):
        """
        Retrieve the current system time adjusted to the configured timezone.

        Args:
            db (Session): Active database session.

        Returns:
            datetime: Current time in the configured timezone.
        """
        return datetime.now(self._get_timezone(db))

    def _validate_user_and_event(self, db, user_id, event_id):
        """
        Validate user and event existence and eligibility.

        Args:
            db (Session): Database session.
            user_id (int): ID of the user.
            event_id (str): ID of the event.

        Returns:
            Tuple[Optional[str], Optional[User], Optional[Event]]:
                - Error message (if any)
                - User object (if valid)
                - Event object (if valid)
        """
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return "User not found.", None, None
        if user.blocked:
            return "Your account is blocked.", None, None

        event = db.query(Event).filter_by(id=event_id).first()
        if not event:
            return "Event not found.", None, None

        return None, user, event

    def book_event(
        self, user_id, event_id
    ):  # pylint: disable=too-many-return-statements
        """
        Book an event for a user if all conditions are met.

        Args:
            user_id (int): The user's ID.
            event_id (str): The event's ID.

        Returns:
            str: A message indicating the success or failure of the booking.
        """
        with self.lock:
            db = self.db()
            try:
                error, _, event = self._validate_user_and_event(db, user_id, event_id)
                if error:
                    return error

                if is_rate_limited(user_id):
                    return "You are rate-limited. Please try again later."

                tz = self._get_timezone(db)
                current_time = datetime.now(tz)
                # event.start_time is naive UTC (see Event model docstring) -
                # attach UTC first, then convert, rather than reinterpreting
                # the UTC wall-clock value as if it were already local time.
                event_start = event.start_time.replace(tzinfo=timezone.utc).astimezone(
                    tz
                )

                if current_time >= event_start:
                    return "Event is no longer available for booking."

                existing_booking = (
                    db.query(Booking)
                    .filter(
                        and_(
                            Booking.user_id == user_id,
                            Booking.event_id == event_id,
                            Booking.status == "confirmed",
                        )
                    )
                    .first()
                )
                if existing_booking:
                    return "You have already booked this event."

                current_bookings = (
                    db.query(Booking)
                    .filter(
                        and_(
                            Booking.event_id == event_id, Booking.status == "confirmed"
                        )
                    )
                    .count()
                )

                if current_bookings >= event.max_bookings:
                    return "Event is fully booked."

                new_booking = Booking(
                    user_id=user_id, event_id=event_id, status="confirmed"
                )
                db.add(new_booking)

                if current_bookings + 1 >= event.max_bookings:
                    event.available = False

                db.commit()
                logger.info("User %d successfully booked event %s.", user_id, event_id)
                return "Booking confirmed."

            except (SQLAlchemyError, RuntimeError) as e:
                db.rollback()
                logger.exception(
                    "Error booking event %s for user %d: %s", event_id, user_id, e
                )
                return "Booking failed due to a server error."
            finally:
                db.close()

    def cancel_booking(self, user_id, event_id):
        """
        Cancel an existing booking for a specific user and event.

        Args:
            user_id (int): The user's ID.
            event_id (str): The event's ID.

        Returns:
            str: A message indicating the success or failure of the cancellation.
        """
        with self.lock:
            db = self.db()
            try:
                error, _, event = self._validate_user_and_event(db, user_id, event_id)
                if error:
                    return error

                if is_rate_limited(user_id):
                    return "You are rate-limited. Please try again later."

                booking = (
                    db.query(Booking)
                    .filter(
                        and_(
                            Booking.user_id == user_id,
                            Booking.event_id == event_id,
                            Booking.status == "confirmed",
                        )
                    )
                    .with_for_update()
                    .first()
                )

                if not booking:
                    return "No active booking found for this event."

                tz = self._get_timezone(db)
                current_time = datetime.now(tz)
                # event.start_time is naive UTC (see Event model docstring) -
                # attach UTC first, then convert, rather than reinterpreting
                # the UTC wall-clock value as if it were already local time.
                event_start = event.start_time.replace(tzinfo=timezone.utc).astimezone(
                    tz
                )

                if current_time >= event_start:
                    return "Cannot cancel booking after event has started."

                db.delete(booking)
                db.flush()

                confirmed_count = (
                    db.query(Booking)
                    .filter(
                        and_(
                            Booking.event_id == event_id, Booking.status == "confirmed"
                        )
                    )
                    .count()
                )

                if confirmed_count < event.max_bookings:
                    event.available = True

                db.commit()
                logger.info(
                    "User %d cancelled booking for event %s.", user_id, event_id
                )
                return "Booking cancelled successfully."

            except (SQLAlchemyError, RuntimeError) as e:
                db.rollback()
                logger.exception(
                    "Error cancelling booking for user %d and event %s: %s",
                    user_id,
                    event_id,
                    e,
                )
                return "Booking cancellation failed due to a server error."
            finally:
                db.close()
