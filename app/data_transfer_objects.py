"""
Data Transfer Objects (DTOs) for the application.

These classes serve as lightweight, structured containers for transferring
data between different layers of the system (e.g., services, routes).
"""

from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime, time as datetime_time


@dataclass
class ConfigurationUpdate:
    """
    DTO for updating system configuration.

    Attributes:
        latitude (float): Geographic latitude (-90 to 90) for weather data.
        longitude (float): Geographic longitude (-180 to 180) for weather data.
        timezone_str (str): IANA timezone identifier (e.g., 'UTC', 'America/New_York').
        weather_threshold (float): Minimum acceptable weather condition rating (0-100%).
        max_bookings_per_event (int): Default maximum number of user bookings per event.
        default_opening_time (datetime_time): Default event start time (local time).
        default_closing_time (datetime_time): Default event end time (local time).
    """

    latitude: float
    longitude: float
    timezone_str: str
    weather_threshold: float
    max_bookings_per_event: int = field(default=10)
    default_opening_time: datetime_time = field(default=datetime_time(17, 0))
    default_closing_time: datetime_time = field(default=datetime_time(22, 0))


@dataclass
class EventData:
    """
    DTO for creating or updating an event slot.

    Attributes:
        event_title (str): Title of the event (up to 30 characters recommended).
        event_description (str): Event description (up to 255 characters).
        event_date (datetime): Date of the event (typically in UTC).
        opening_time (datetime_time): Event start time (local time).
        closing_time (datetime_time): Event end time (local time).
        max_bookings (int): Maximum allowed user bookings for the event.
    """

    event_title: str
    event_description: str
    event_date: datetime
    opening_time: datetime_time
    closing_time: datetime_time
    max_bookings: int


@dataclass
class WeatherInfo:
    """
    DTO for summarizing weather evaluation results.

    Attributes:
        condition_rating (Optional[int]): Weather condition rating (0–100%).
        weather_warning (bool): True if warning triggered.
        weather_forecast (bool): True if forecast data is present.
    """

    condition_rating: Optional[int] = None
    weather_warning: bool = False
    weather_forecast: bool = False


@dataclass
class WeatherData:
    """
    DTO for storing detailed hourly weather forecast data.

    Attributes:
        times (List[str]): ISO 8601 formatted timestamps for hourly data points.
        dew_points (List[float]): Hourly dew point temperatures (°C).
        precip_probs (List[float]): Hourly precipitation probabilities (percentage).
        cloud_covers (List[float]): Hourly cloud cover percentages.
        visibilities (List[float]): Hourly visibility distances (in meters).
        tz_str (str): Timezone string used to interpret timestamps (e.g., 'UTC').
    """

    times: List[str] = field(default_factory=list)
    dew_points: List[float] = field(default_factory=list)
    precip_probs: List[float] = field(default_factory=list)
    cloud_covers: List[float] = field(default_factory=list)
    visibilities: List[float] = field(default_factory=list)
    tz_str: str = "UTC"


@dataclass
class EventTimes:
    """
    DTO for event timings in both local timezone and UTC.

    Attributes:
        start_local (datetime): Event start time in local timezone.
        end_local (datetime): Event end time in local timezone.
        start_utc (datetime): Event start time in UTC.
        end_utc (datetime): Event end time in UTC.
    """

    start_local: datetime
    end_local: datetime
    start_utc: datetime
    end_utc: datetime
