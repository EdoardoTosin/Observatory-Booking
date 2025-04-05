"""
Booking Service Module

This module provides a service class for managing event bookings and cancellations.
It ensures concurrency safety, rate-limiting, and event availability checks.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from threading import Lock

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from ..models import User, Slot, Booking, Configuration
from ..utils import logger, is_rate_limited


class BookingService:
    """
    Service class for managing event bookings and cancellations.

    This class ensures:
    - Thread-safe operations
    - Rate limiting enforcement
    - Slot availability validation
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

    def _validate_user_and_slot(self, db, user_id, slot_id):
        """
        Validate user and slot existence and eligibility.

        Args:
            db (Session): Database session.
            user_id (int): ID of the user.
            slot_id (str): ID of the slot.

        Returns:
            Tuple[Optional[str], Optional[User], Optional[Slot]]:
                - Error message (if any)
                - User object (if valid)
                - Slot object (if valid)
        """
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return "User not found.", None, None
        if user.blocked:
            return "Your account is blocked.", None, None

        slot = db.query(Slot).filter_by(id=slot_id).first()
        if not slot:
            return "Event not found.", None, None

        return None, user, slot

    def book_slot(self, user_id, slot_id):  # pylint: disable=too-many-return-statements
        """
        Book an event slot for a user if all conditions are met.

        Args:
            user_id (int): The user's ID.
            slot_id (str): The slot's ID.

        Returns:
            str: A message indicating the success or failure of the booking.
        """
        with self.lock:
            db = self.db()
            try:
                error, _, slot = self._validate_user_and_slot(db, user_id, slot_id)
                if error:
                    return error

                if is_rate_limited(user_id):
                    return "You are rate-limited. Please try again later."

                tz = self._get_timezone(db)
                current_time = datetime.now(tz)
                slot_start = slot.start_time.replace(tzinfo=tz)

                if current_time >= slot_start:
                    return "Event is no longer available for booking."

                existing_booking = (
                    db.query(Booking)
                    .filter(
                        and_(
                            Booking.user_id == user_id,
                            Booking.slot_id == slot_id,
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
                        and_(Booking.slot_id == slot_id, Booking.status == "confirmed")
                    )
                    .count()
                )

                if current_bookings >= slot.max_bookings:
                    return "Event is fully booked."

                new_booking = Booking(
                    user_id=user_id, slot_id=slot_id, status="confirmed"
                )
                db.add(new_booking)

                if current_bookings + 1 >= slot.max_bookings:
                    slot.available = False

                db.commit()
                logger.info("User %d successfully booked event %s.", user_id, slot_id)
                return "Booking confirmed."

            except (SQLAlchemyError, RuntimeError) as e:
                db.rollback()
                logger.exception(
                    "Error booking event %s for user %d: %s", slot_id, user_id, e
                )
                return "Booking failed due to a server error."
            finally:
                db.close()

    def cancel_booking(self, user_id, slot_id):
        """
        Cancel an existing booking for a specific user and event slot.

        Args:
            user_id (int): The user's ID.
            slot_id (str): The slot's ID.

        Returns:
            str: A message indicating the success or failure of the cancellation.
        """
        with self.lock:
            db = self.db()
            try:
                error, _, slot = self._validate_user_and_slot(db, user_id, slot_id)
                if error:
                    return error

                if is_rate_limited(user_id):
                    return "You are rate-limited. Please try again later."

                booking = (
                    db.query(Booking)
                    .filter(
                        and_(
                            Booking.user_id == user_id,
                            Booking.slot_id == slot_id,
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
                slot_start = slot.start_time.replace(tzinfo=tz)

                if current_time >= slot_start:
                    return "Cannot cancel booking after event has started."

                db.delete(booking)
                db.flush()

                confirmed_count = (
                    db.query(Booking)
                    .filter(
                        and_(Booking.slot_id == slot_id, Booking.status == "confirmed")
                    )
                    .count()
                )

                if confirmed_count < slot.max_bookings:
                    slot.available = True

                db.commit()
                logger.info("User %d cancelled booking for event %s.", user_id, slot_id)
                return "Booking cancelled successfully."

            except (SQLAlchemyError, RuntimeError) as e:
                db.rollback()
                logger.exception(
                    "Error cancelling booking for user %d and slot %s: %s",
                    user_id,
                    slot_id,
                    e,
                )
                return "Booking cancellation failed due to a server error."
            finally:
                db.close()
