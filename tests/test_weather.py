"""Regression tests for WeatherService's hour-range calculation.

Pins down the fix for a bug found during a full audit of the weather
implementation: `_generate_hourly_range` used to attach the configured
timezone directly to a naive datetime (`start.replace(tzinfo=tz)`).
`Event.start_time`/`end_time` are naive UTC (see the Event model docstring),
so that silently reinterpreted a UTC wall-clock hour as if it were already
local time, shifting the whole hourly range by the zone's UTC offset -
this was live in the default seeded config (`Europe/Rome`, UTC+1/+2),
corrupting every event's weather rating on the very first periodic
refresh (which fires almost immediately - `next_run_time=datetime.now()`).
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.weather_service import WeatherService


@pytest.mark.parametrize(
    "tz_name",
    ["UTC", "Europe/Rome", "America/Los_Angeles", "Pacific/Kiritimati"],
)
def test_naive_utc_input_matches_aware_utc_input(tz_name):
    """A naive datetime (as read back from the `Event` table) must produce
    the exact same hourly range as the equivalent timezone-aware UTC
    datetime (as used when an event is first created) - the two code paths
    must agree, since they represent the same instant."""
    naive_utc_start = datetime(2026, 8, 10, 18, 0, 0)
    naive_utc_end = datetime(2026, 8, 10, 23, 0, 0)
    aware_utc_start = naive_utc_start.replace(tzinfo=timezone.utc)
    aware_utc_end = naive_utc_end.replace(tzinfo=timezone.utc)

    from_naive = (
        WeatherService._generate_hourly_range(  # pylint: disable=protected-access
            naive_utc_start, naive_utc_end, tz_name
        )
    )
    from_aware = (
        WeatherService._generate_hourly_range(  # pylint: disable=protected-access
            aware_utc_start, aware_utc_end, tz_name
        )
    )

    assert from_naive == from_aware


def test_naive_utc_input_converts_to_correct_local_hour():
    """18:00 UTC must land on 11:00 local in America/Los_Angeles (UTC-7 in
    August), not 18:00 local - the exact shift the bug produced."""
    naive_utc_start = datetime(2026, 8, 10, 18, 0, 0)
    naive_utc_end = datetime(2026, 8, 10, 20, 0, 0)

    hourly_range = (
        WeatherService._generate_hourly_range(  # pylint: disable=protected-access
            naive_utc_start, naive_utc_end, "America/Los_Angeles"
        )
    )

    expected_start = naive_utc_start.replace(tzinfo=timezone.utc).astimezone(
        ZoneInfo("America/Los_Angeles")
    )
    assert hourly_range[0] == expected_start
    assert hourly_range[0].hour == 11


def test_update_event_weather_uses_correct_local_hours_for_naive_event_times(app):
    """
    End-to-end regression against `_update_event_weather` (the exact method
    the periodic background job calls, and the one that read naive-UTC
    `Event.start_time`/`end_time` straight off the DB row): with a
    synthetic forecast keyed by known local hours, the computed rating
    must match manually averaging only the hours that truly overlap the
    event - proving the naive UTC start/end got converted to the right
    local hours instead of being misread as already-local.
    """
    from app.services.weather_service import (
        WeatherService as WS,
    )  # noqa: N814  pylint: disable=import-outside-toplevel

    tz_name = "America/Los_Angeles"  # UTC-7 in August
    tz = ZoneInfo(tz_name)

    # A plain stand-in (not an ORM instance) so attribute access doesn't
    # need a live session - `_update_event_weather` only reads these two
    # fields off `config`.
    class _FakeConfig:
        timezone = tz_name
        weather_threshold = 0  # force weather_warning False regardless of rating

    # Event: 18:00-20:00 UTC (naive, as stored) == 11:00-13:00 local.
    event_start_naive = datetime(2026, 8, 10, 18, 0, 0)
    event_end_naive = datetime(2026, 8, 10, 20, 0, 0)

    class _FakeEvent:  # minimal stand-in, avoids DB/CheckConstraint plumbing
        start_time = event_start_naive
        end_time = event_end_naive
        weather_rating = None
        weather_warning = None
        weather_forecast = None

    # Synthetic forecast: distinct, known values at each local hour, plus a
    # decoy at the WRONG (bug-shifted) hours so the test fails loudly if the
    # naive/local mixup regresses.
    def _weather_at(cloud_cover):
        return {
            "cloud_cover": cloud_cover,
            "precipitation_probability": 0.0,
            "dew_point": 0.0,
            "visibility": 20000.0,
        }

    correct_hours = [
        datetime(2026, 8, 10, 11, 0, tzinfo=tz),
        datetime(2026, 8, 10, 12, 0, tzinfo=tz),
        datetime(2026, 8, 10, 13, 0, tzinfo=tz),
    ]
    decoy_hours = [
        datetime(2026, 8, 10, 18, 0, tzinfo=tz),
        datetime(2026, 8, 10, 19, 0, tzinfo=tz),
        datetime(2026, 8, 10, 20, 0, tzinfo=tz),
    ]
    forecast_data = {hour: _weather_at(0.0) for hour in correct_hours}
    forecast_data.update({hour: _weather_at(100.0) for hour in decoy_hours})

    fake_event = _FakeEvent()
    weather_service = app.system.weather_service
    weather_service._update_event_weather(  # pylint: disable=protected-access
        fake_event, forecast_data, _FakeConfig()
    )

    assert fake_event.weather_forecast is True
    # cloud_cover=0.0 at every correct hour -> cloud_rating=100 for all of
    # them -> full-weight average should be a perfect (or near-perfect)
    # score, NOT the ~0 score the decoy (bug-shifted) hours would produce.
    assert fake_event.weather_rating == pytest.approx(
        WS.calculate_hourly_rating(_weather_at(0.0)), abs=0.01
    )
