"""
Admin Service Module

This module implements the `AdminService` class, which provides administrative functionalities
for managing users, configurations, and event scheduling in the booking system.
"""

import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.exc import SQLAlchemyError

from ..models import Configuration, User, Slot
from ..utils import logger, get_env_value
from ..data_transfer_objects import (
    EventTimes,
    WeatherInfo,
)


class AdminService:
    """
    Service class for administrative operations, including superadmin initialization,
    user role management, blocking users, configuration updates, and event scheduling.
    """

    def __init__(
        self,
        db_session,
        lock,
        weather_service=None,
    ):
        """
        Initialize the AdminService.

        Args:
            db_session (Callable[[], Session]): A callable returning a new database session.
            lock (Any): A threading lock to ensure thread-safe operations.
            weather_service (Optional[Any], optional): A weather service instance for event
              forecasting. Defaults to None.
        """
        self.db = db_session
        self.lock = lock
        self.weather_service = weather_service

    def _initialize_superadmin(self):
        """
        Ensure that a superadmin account exists in the system.

        If no superadmin exists, a new one is created using environment-configured credentials.
        """
        session = self.db()
        try:
            superadmin = session.query(User).filter_by(admin_rank="super").first()
            if not superadmin:
                self._create_superadmin(session)
        except SQLAlchemyError as e:
            logger.exception("Error during superadmin initialization: %s", e)
            raise
        finally:
            session.close()

    def _create_superadmin(self, session):
        """
        Create a new superadmin user and save credentials to log.

        Args:
            session (Session): Active database session.
        """
        email = get_env_value("DEFAULT_ADMIN_EMAIL", "admin@example.com")
        password = get_env_value("DEFAULT_ADMIN_PASSWORD", secrets.token_urlsafe(16))
        superadmin = User(
            name="Superadmin",
            email=email,
            password=password,
            role="Admin",
            admin_rank="super",
        )
        session.add(superadmin)
        session.commit()
        logger.info("Default superadmin created. Email: %s", email)
        print(f"Default superadmin created.\nEmail: {email}\nPassword: {password}")

    def update_user_role(self, user_id, new_role):
        """
        Update the role of a user.

        Superadmin account cannot have his role changed.

        Args:
            user_id (int): The ID of the user to update.
            new_role (str): The new role to assign.

        Raises:
            ValueError: If the user does not exist or is a superadmin.
        """
        session = self.db()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            if user.admin_rank == "super":
                raise ValueError("Cannot change role for superadmin")
            user.role = new_role
            user.admin_rank = "admin" if new_role == "Admin" else None
            session.commit()
        except (SQLAlchemyError, ValueError) as e:
            session.rollback()
            logger.exception("Error updating role for user %s: %s", user_id, e)
            raise
        finally:
            session.close()

    def block_user(self, user_id, block):
        """
        Block or unblock a user.

        Admin accounts cannot be blocked.

        Args:
            user_id (int): The ID of the user.
            block (bool): True to block the user, False to unblock.
        """
        session = self.db()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            if user.role == "Admin":
                raise ValueError("Cannot block admin")
            user.blocked = block
            session.commit()
        except (SQLAlchemyError, ValueError) as e:
            session.rollback()
            logger.exception(
                "Error updating blocked status for user %s: %s", user_id, e
            )
            raise
        finally:
            session.close()

    def delete_user(self, user_id):
        """
        Delete a user.

        Superadmin account cannot be deleted.

        Args:
            user_id (int): The ID of the user.
        """
        session = self.db()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found.")
            if user.admin_rank == "super":
                raise ValueError("Cannot delete superadmin account.")
            session.delete(user)
            session.commit()
            logger.info("User ID %s deleted successfully.", user_id)
        except (SQLAlchemyError, ValueError) as e:
            session.rollback()
            logger.exception("Error deleting user %s: %s", user_id, e)
            raise
        finally:
            session.close()

    def update_configuration(self, **config_params):
        """
        Update the system configuration with provided parameters.

        Args:
            **config_params (Any): Configuration fields and their new values.

        Returns:
            Configuration: The updated configuration object.
        """
        with self.lock:
            session = self.db()
            try:
                config = Configuration.get_config(session)
                for key, value in config_params.items():
                    setattr(config, key, value)
                session.commit()
                if self.weather_service:
                    self.weather_service.update_events_weather()
                return config
            except (SQLAlchemyError, ValueError) as e:
                session.rollback()
                logger.exception("Error updating configuration: %s", e)
                raise
            finally:
                session.close()

    def confirm_event(self, event, event_id=None):
        """
        Create or update an event slot based on provided event details.

        Args:
            event (EventData): Event details.
            event_id (int): Event ID.

        Returns:
            str: Confirmation message regarding event creation or update.
        """
        return self._process_event_confirmation(event, event_id=event_id)

    def _process_event_confirmation(self, event, event_id):
        """
        Process event confirmation with validation and weather integration.

        Args:
            event: The event details encapsulated in an EventData instance.
            event_id (int): The event ID.

        Returns:
            str: A confirmation message.
        """
        session = self.db()
        try:
            config = Configuration.get_config(session)
            tz = ZoneInfo(str(config.timezone))

            event_times, weather_info, error_msg = self._prepare_event_data(
                session, event, tz
            )
            if error_msg:
                return error_msg

            current_time = datetime.now(tz)
            existing_event = (
                session.query(Slot).filter(Slot.id == int(event_id)).first()
                if event_id
                else None
            )

            if existing_event and not self._can_modify_event(
                existing_event, current_time, tz
            ):
                return "Cannot modify an event that has already started or ended."

            event_data = {
                "title": event.event_title,
                "description": event.event_description,
                "max_bookings": event.max_bookings,
                "start_time": event_times.start_utc,
                "end_time": event_times.end_utc,
                "weather_info": weather_info,
            }

            return self._save_event(session, existing_event, event_data)

        except (SQLAlchemyError, ValueError) as e:
            session.rollback()
            logger.exception("Error confirming event: %s", e)
            raise
        finally:
            session.close()

    def _prepare_event_data(self, session, event, tz):
        """
        Validate and prepare event times and weather data.

        Performs input validation, computes local and UTC event time ranges,
        and fetches weather data for the event duration. Returns a tuple of
        event time info, weather info, and an optional error message.

        Args:
            session: Active database session.
            event (EventData): Event input data from the client.
            tz (ZoneInfo): Timezone for the event.

        Returns:
            Tuple[Optional[EventTimes], Optional[WeatherInfo], Optional[str]]:
                - EventTimes: Local and UTC event start/end times.
                - WeatherInfo: Weather rating and warnings, if available.
                - str: Error message if validation fails, otherwise None.
        """
        if not self._validate_event_input(
            event.event_title, event.event_description, event.max_bookings
        ):
            return None, None, "Invalid input parameters."

        event_times = self._calculate_event_times_full(
            event.event_date, event.opening_time, event.closing_time, tz
        )

        current_time = datetime.now(tz)
        if event_times.start_local < current_time:
            return (
                None,
                None,
                "Cannot schedule or edit an event with opening time in the past.",
            )
        if event_times.end_local < current_time:
            return (
                None,
                None,
                "Cannot schedule or edit an event with closing time in the past.",
            )

        config = Configuration.get_config(session)
        weather_info = self._get_weather_data(
            event_times.start_local, event_times.end_local, config
        )
        if not weather_info:
            return None, None, "Weather service not available."

        return event_times, weather_info, None

    def _validate_event_input(self, title, description, max_bookings):
        """Validate event input parameters."""
        title = title.strip()
        description = description.strip()
        if not title or len(title) > 30 or len(description) > 255 or max_bookings < 1:
            return False
        return True

    def _calculate_event_times(
        self,
        event_date,
        opening_time,
        closing_time,
        tz,
    ):
        """Calculate local start and end times for the event."""
        event_start_local = datetime.combine(event_date, opening_time, tzinfo=tz)
        if closing_time <= opening_time:
            event_end_local = datetime.combine(
                event_date + timedelta(days=1), closing_time, tzinfo=tz
            )
        else:
            event_end_local = datetime.combine(event_date, closing_time, tzinfo=tz)
        return event_start_local, event_end_local

    def _calculate_event_times_full(
        self,
        event_date,
        opening_time,
        closing_time,
        tz,
    ) -> EventTimes:
        """Calculate both local and UTC start and end times for the event."""
        event_start_local, event_end_local = self._calculate_event_times(
            event_date, opening_time, closing_time, tz
        )
        event_start_utc = event_start_local.astimezone(timezone.utc)
        event_end_utc = event_end_local.astimezone(timezone.utc)

        return EventTimes(
            start_local=event_start_local,
            end_local=event_end_local,
            start_utc=event_start_utc,
            end_utc=event_end_utc,
        )

    def _get_existing_event(self, session, event_start_utc):
        """Get existing event for the given start time."""
        return session.query(Slot).filter(Slot.start_time == event_start_utc).first()

    def _can_modify_event(self, event, current_time, tz):
        """Check if an existing event can be modified."""
        current_start = event.start_time.astimezone(tz)
        current_end = event.end_time.astimezone(tz)
        return current_start >= current_time and current_end >= current_time

    def _get_weather_data(self, start_time, end_time, config: Configuration):
        """Get weather data for the event time period."""
        if self.weather_service is None:
            return None

        condition_rating, weather_warning, weather_forecast = (
            self.weather_service.get_event_weather(start_time, end_time, config)
        )

        return WeatherInfo(
            condition_rating=condition_rating,
            weather_warning=weather_warning,
            weather_forecast=weather_forecast,
        )

    def _save_event(self, session, existing_event, event_data):
        """
        Save a new event or update an existing event, ensuring no time overlap.

        Args:
            session: The database session.
            existing_event: An existing event to update, or None for a new event.
            event_data: Dictionary containing event information.

        Returns:
            str: Success message or overlap error.
        """
        start_time = event_data["start_time"]
        end_time = event_data["end_time"]

        if self._check_same_day_start(session, existing_event, start_time):
            return "Only one event can start per day."

        if self._check_prev_day_overlap(session, existing_event, start_time):
            return "Start time overlaps with previous day's event."

        if self._check_next_day_overlap(session, existing_event, end_time):
            return "End time overlaps with next day's event."

        query = session.query(Slot).filter(
            Slot.end_time > start_time, Slot.start_time < end_time
        )
        if existing_event:
            query = query.filter(Slot.id != existing_event.id)

        overlapping_event = query.first()
        if overlapping_event:
            return f"Time conflict with another event (ID: {overlapping_event.id})."

        title = event_data["title"]
        description = event_data["description"]
        max_bookings = event_data["max_bookings"]
        weather_info = event_data["weather_info"]

        if existing_event:
            existing_event.title = title
            existing_event.description = description
            existing_event.end_time = end_time
            existing_event.start_time = start_time
            existing_event.max_bookings = max_bookings
            existing_event.weather_rating = weather_info.condition_rating
            existing_event.weather_warning = weather_info.weather_warning
            existing_event.weather_forecast = weather_info.weather_forecast
            existing_event.available = True
            session.commit()
            logger.info("Existing event updated for start time %s.", start_time)
            return "Event updated successfully."

        new_event = Slot(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            max_bookings=max_bookings,
            weather_rating=weather_info.condition_rating,
            weather_warning=weather_info.weather_warning,
            weather_forecast=weather_info.weather_forecast,
            available=True,
        )
        session.add(new_event)
        session.commit()
        logger.info("New event created for start time %s.", start_time)
        return "Event created successfully."

    def _check_same_day_start(self, session, existing_event, start_time):
        """Check if any event starts on the same UTC day."""
        start_day_utc = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day_utc = start_day_utc + timedelta(days=1)
        query = session.query(Slot).filter(
            Slot.start_time >= start_day_utc,
            Slot.start_time < next_day_utc,
        )
        if existing_event:
            query = query.filter(Slot.id != existing_event.id)
        return query.first() is not None

    def _check_prev_day_overlap(self, session, existing_event, start_time):
        """Check if an event from the previous day overlaps into the new event's start time."""
        start_day_utc = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_day_start_utc = start_day_utc - timedelta(days=1)
        prev_day_end_utc = start_day_utc

        query = session.query(Slot).filter(
            Slot.start_time >= prev_day_start_utc,
            Slot.start_time < prev_day_end_utc,
            Slot.end_time > start_time,
        )
        if existing_event:
            query = query.filter(Slot.id != existing_event.id)
        return query.first() is not None

    def _check_next_day_overlap(self, session, existing_event, end_time):
        """Check if the current event's end time overlaps into the next day's event start."""
        end_day_utc = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day_utc = end_day_utc + timedelta(days=1)

        query = session.query(Slot).filter(
            Slot.start_time >= next_day_utc,
            Slot.start_time < next_day_utc + timedelta(days=1),
            Slot.start_time < end_time,
        )
        if existing_event:
            query = query.filter(Slot.id != existing_event.id)
        return query.first() is not None

    def update_events_weather(self):
        """
        Update weather conditions for upcoming events.

        If a weather service is configured, it updates stored weather data for all scheduled events.

        Raises:
            ValueError: If the weather service is not initialized.
        """
        if not self.weather_service:
            raise ValueError("Weather service not initialized")
        self.weather_service.update_events_weather()
