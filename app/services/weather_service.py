"""
Weather Service Module

This module provides the `WeatherService` class responsible for:

- Fetching weather data from the Open-Meteo API.
- Updating weather conditions for scheduled events.
- Using a background scheduler to refresh data every 3 hours.
- Implementing a robust HTTP request retry mechanism.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import atexit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import SQLAlchemyError

from ..models import Configuration, Slot
from ..data_transfer_objects import WeatherData
from ..utils import ttl_cache, logger


class WeatherService:
    """
    A service to retrieve and manage weather data.

    This class:
    - Fetches weather forecasts from the Open-Meteo API.
    - Updates weather conditions for scheduled events.
    - Schedules periodic weather updates in the background.
    - Implements a retry mechanism for API requests.
    """

    API_ENDPOINT_TEMPLATE = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude={latitude}&longitude={longitude}"
        "&hourly=dew_point_2m,precipitation_probability,cloud_cover,visibility"
        "&timezone={tz_str}"
    )

    WEIGHTS = {
        "cloud_cover": 0.4,
        "precipitation_probability": 0.3,
        "dew_point": 0.15,
        "visibility": 0.15,
    }
    DEW_POINT_THRESHOLD_LOW = 5.0
    DEW_POINT_THRESHOLD_HIGH = 10.0
    IDEAL_VISIBILITY = 20000.0  # in meters

    def __init__(self, db_session, cache_time=3):
        """
        Initialize the WeatherService.

        Args:
            db_session (Callable[[], Session]): A callable that returns a new database session.
            cache_time (int, optional): Cache time (in hours) for API responses. Defaults to 3.
        """
        self.db = db_session
        self.cache_time = cache_time

        self.http_session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.http_session.mount("https://", adapter)

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.update_events_weather, "interval", hours=3, id="update_events_weather"
        )
        self.scheduler.start()

        atexit.register(self.shutdown)
        logger.info("WeatherService initialized with background scheduler.")

    def shutdown(self):
        """
        Gracefully shuts down the background scheduler.
        """
        self.scheduler.shutdown()
        logger.info("WeatherService scheduler shutdown complete.")

    @ttl_cache(ttl=3)
    def fetch_weather_data(self, latitude, longitude, tz_str):
        """
        Retrieve weather data from Open-Meteo API.

        Args:
            latitude (float): Latitude coordinate.
            longitude (float): Longitude coordinate.
            tz_str (str): Timezone string.

        Returns:
            Dict[datetime, Dict[str, float]]: A mapping of datetime to weather parameters.
        """
        api_url = self.API_ENDPOINT_TEMPLATE.format(
            latitude=latitude, longitude=longitude, tz_str=tz_str
        )
        logger.debug("Fetching weather data from URL: %s", api_url)

        try:
            response = self.http_session.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            dew_points = hourly.get("dew_point_2m", [])
            precip_probs = hourly.get("precipitation_probability", [])
            cloud_covers = hourly.get("cloud_cover", [])
            visibilities = hourly.get("visibility", [])

            weather_data = WeatherData(
                times=times,
                dew_points=dew_points,
                precip_probs=precip_probs,
                cloud_covers=cloud_covers,
                visibilities=visibilities,
                tz_str=tz_str,
            )

            return self._process_hourly_data(weather_data)

        except (requests.RequestException, ValueError) as exc:
            logger.exception("Error fetching weather data: %s", exc)

        return {}

    def _process_hourly_data(self, weather_data):
        """
        Process raw hourly weather data.

        Args:
            weather_data (WeatherData): The retrieved weather data.

        Returns:
            Dict[datetime, Dict[str, float]]: A dictionary mapping datetimes to weather parameters.
        """
        weather_by_time = {}

        for time_str, dew, precip, cloud, vis in zip(
            weather_data.times,
            weather_data.dew_points,
            weather_data.precip_probs,
            weather_data.cloud_covers,
            weather_data.visibilities,
        ):
            try:
                dt = datetime.fromisoformat(time_str).replace(
                    tzinfo=ZoneInfo(weather_data.tz_str)
                )
            except ValueError as exc:
                logger.exception("Error parsing datetime '%s': %s", time_str, exc)
                continue

            weather_by_time[dt] = {
                "dew_point": float(dew),
                "precipitation_probability": float(precip),
                "cloud_cover": float(cloud),
                "visibility": float(vis),
            }

        logger.debug("Parsed weather data for %d hourly entries.", len(weather_by_time))
        return weather_by_time

    @classmethod
    def calculate_hourly_rating(cls, weather):
        """
        Calculate weather rating based on parameters.

        Args:
            weather (Dict[str, float]): Weather parameters.

        Returns:
            float: Calculated rating (0 to 100).
        """
        cloud_rating = max(0.0, 100.0 - weather.get("cloud_cover", 100.0))

        precip_rating = max(
            0.0, 100.0 - weather.get("precipitation_probability", 100.0)
        )

        dew_point = weather.get("dew_point", cls.DEW_POINT_THRESHOLD_HIGH)
        if dew_point < cls.DEW_POINT_THRESHOLD_LOW:
            dew_rating = 100.0
        elif dew_point <= cls.DEW_POINT_THRESHOLD_HIGH:
            range_size = cls.DEW_POINT_THRESHOLD_HIGH - cls.DEW_POINT_THRESHOLD_LOW
            relative_pos = dew_point - cls.DEW_POINT_THRESHOLD_LOW
            dew_rating = 100.0 - (relative_pos * (100.0 / range_size))
        else:
            dew_rating = 0.0

        visibility = weather.get("visibility", 0.0)
        visibility_rating = min(100.0, (visibility / cls.IDEAL_VISIBILITY) * 100.0)

        rating = (
            cls.WEIGHTS["cloud_cover"] * cloud_rating
            + cls.WEIGHTS["precipitation_probability"] * precip_rating
            + cls.WEIGHTS["dew_point"] * dew_rating
            + cls.WEIGHTS["visibility"] * visibility_rating
        )
        return rating

    @classmethod
    def calculate_average_weather_rating(cls, hourly_weather):
        """
        Calculate the average weather rating over a list of hourly weather data.

        Args:
            hourly_weather (List[Dict[str, float]]): A list of hourly
            weather parameter dictionaries.

        Returns:
            float: The average weather rating (0 to 100).
        """
        if not hourly_weather:
            return 0.0
        ratings = [cls.calculate_hourly_rating(hour) for hour in hourly_weather]
        return sum(ratings) / len(ratings)

    def get_event_weather(self, event_start, event_end, config):
        """
        Retrieve weather conditions for an event.

        Args:
            event_start (datetime): Event start time.
            event_end (datetime): Event end time.
            config (Configuration): System configuration.

        Returns:
            Tuple[Optional[float], bool, bool]:
                - Average rating (None if unavailable)
                - Warning (True if below threshold)
                - Forecast availability
        """
        weather_data = self.fetch_weather_data(
            config.latitude, config.longitude, config.timezone
        )

        hourly_range = self._generate_hourly_range(
            event_start, event_end, config.timezone
        )
        hourly_data = [
            weather_data[hour] for hour in hourly_range if hour in weather_data
        ]

        rating = (
            self.calculate_average_weather_rating(hourly_data) if hourly_data else None
        )
        weather_warning = rating is not None and rating < config.weather_threshold
        logger.debug("Event weather rating: %s, warning: %s", rating, weather_warning)
        return rating, weather_warning, bool(hourly_data)

    def update_events_weather(self):
        """
        Update weather conditions for all upcoming events.
        """
        session = self.db()
        try:
            config = Configuration.get_config(session)
            forecast_data = self.fetch_weather_data(
                config.latitude, config.longitude, config.timezone
            )
            events = self._get_upcoming_events(session, config.timezone)
            logger.info("Updating weather for %d upcoming events.", len(events))

            for event in events:
                self._update_event_weather(event, forecast_data, config)

            session.commit()
            logger.info("Weather conditions successfully updated for upcoming events.")
        except (SQLAlchemyError, ValueError, KeyError) as exc:
            logger.exception("Error updating event weather: %s", exc)
            session.rollback()
        finally:
            session.close()

    def _update_event_weather(
        self,
        event,
        forecast_data,
        config,
    ):
        """
        Update weather data for a single event.

        Args:
            event: The event to update
            forecast_data: The forecast data dictionary
            config: The configuration object with weather thresholds
        """
        hourly_range = self._generate_hourly_range(
            event.start_time, event.end_time, config.timezone
        )
        hourly_data = [
            forecast_data[hour] for hour in hourly_range if hour in forecast_data
        ]

        if hourly_data:
            event.weather_rating = self.calculate_average_weather_rating(hourly_data)
            event.weather_warning = event.weather_rating < config.weather_threshold
            event.weather_forecast = True
        else:
            event.weather_forecast = False

    @staticmethod
    def _generate_hourly_range(start, end, tz_str):
        """
        Generate a list of hourly timestamps between start and end, inclusive.
        Ensures that the datetimes are timezone-aware and in the specified timezone.

        Args:
            start (datetime): The start datetime.
            end (datetime): The end datetime.
            tz_str (str): Timezone string (e.g., 'UTC', 'Europe/Rome').

        Returns:
            List[datetime]: Hourly datetime objects covering the entire period.
        """
        tz = ZoneInfo(tz_str)
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        else:
            start = start.astimezone(tz)

        if end.tzinfo is None:
            end = end.replace(tzinfo=tz)
        else:
            end = end.astimezone(tz)

        start = start.replace(minute=0, second=0, microsecond=0)
        total_hours = int((end - start).total_seconds() // 3600) + 1
        return [start + timedelta(hours=i) for i in range(total_hours)]

    def _get_upcoming_events(self, session, timezone_str):
        """
        Retrieve upcoming events from the database.

        Args:
            session (Any): The database session.
            timezone_str (str): The timezone string.

        Returns:
            List[Slot]: A list of upcoming events within the next 7 days.
        """
        now_local = datetime.now(ZoneInfo(timezone_str))
        now_utc = now_local.astimezone(timezone.utc)
        future_utc = (now_local + timedelta(days=7)).astimezone(timezone.utc)
        events = (
            session.query(Slot)
            .filter(Slot.start_time >= now_utc, Slot.start_time <= future_utc)
            .all()
        )
        logger.debug("Retrieved %d upcoming events.", len(events))
        return events
