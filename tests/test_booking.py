"""Booking/cancellation business-rule regression tests, including the
timezone-offset bug found while auditing the weather service (the same
"naive UTC datetime reinterpreted as local time" mistake was also present
in BookingService's already-started checks).
"""

from datetime import datetime, timedelta, timezone

import pytest

from helpers import current_csrf_token, register


def _create_event(system, start_offset_hours=48, duration_hours=2, max_bookings=1):
    from app.models import Event  # pylint: disable=import-outside-toplevel

    start = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) + timedelta(
        hours=start_offset_hours
    )
    end = start + timedelta(hours=duration_hours)
    with system as db:
        event = Event(
            title="Test Event",
            description="A test event.",
            start_time=start,
            end_time=end,
            max_bookings=max_bookings,
            available=True,
        )
        db.add(event)
        db.commit()
        return event.id


def _book(client, event_id, csrf):
    return client.post(
        "/booking",
        data={"event_id": str(event_id), "_csrf_token": csrf},
        follow_redirects=True,
    )


def _cancel(client, event_id, csrf):
    return client.post(
        f"/cancel_booking/{event_id}",
        data={"_csrf_token": csrf},
        follow_redirects=True,
    )


@pytest.fixture
def user_client(client):
    """A logged-in regular-user client, with a CSRF token ready to reuse."""
    register(client, "Booker", "booker@example.com", "Passw0rd1")
    return client, current_csrf_token(client)


def test_book_event_success(app, user_client):
    client, csrf = user_client
    event_id = _create_event(app.system)
    response = _book(client, event_id, csrf)
    assert b"Booking confirmed" in response.data


def test_double_booking_is_rejected(app, user_client):
    client, csrf = user_client
    event_id = _create_event(app.system, max_bookings=2)
    _book(client, event_id, csrf)
    response = _book(client, event_id, csrf)
    assert b"already booked" in response.data


def test_fully_booked_event_is_rejected(app, user_client):
    client, csrf = user_client
    event_id = _create_event(app.system, max_bookings=1)
    _book(client, event_id, csrf)  # fills the only slot

    client.get("/logout")
    register(client, "Second Booker", "secondbooker@example.com", "Passw0rd1")
    csrf2 = current_csrf_token(client)
    response = _book(client, event_id, csrf2)
    assert b"fully booked" in response.data


def test_cancel_booking_success(app, user_client):
    client, csrf = user_client
    event_id = _create_event(app.system)
    _book(client, event_id, csrf)
    response = _cancel(client, event_id, csrf)
    assert b"cancelled successfully" in response.data


def test_cancel_nonexistent_booking_is_rejected(app, user_client):
    client, csrf = user_client
    event_id = _create_event(app.system)
    response = _cancel(client, event_id, csrf)
    assert b"No active booking found" in response.data


@pytest.mark.parametrize(
    "tz_name", ["America/Los_Angeles", "Europe/Rome", "Pacific/Kiritimati"]
)
def test_service_rejects_already_started_event_regardless_of_timezone(app, tz_name):
    """
    Regression test for the "naive UTC datetime reinterpreted as local time"
    bug in `BookingService.book_event`/`cancel_booking`: it used to do
    `event.start_time.replace(tzinfo=tz)` directly on a naive-UTC value,
    shifting the "has this event already started" check by the configured
    timezone's UTC offset. Depending on the offset's sign, that either let
    the service book/cancel events that had already started (offset behind
    UTC, e.g. US zones) or wrongly blocked events that hadn't started yet
    (offset ahead of UTC, e.g. Europe/Rome).

    Exercises `BookingService` directly (not through the `/booking` route),
    since the route has its own separate, already-correct pure-UTC guard
    that runs first - this test is what actually pins down the service
    layer's own logic, independent of that route-level duplication.
    """
    from app.models import Configuration  # pylint: disable=import-outside-toplevel

    with app.system as db:
        config = Configuration.get_config(db)
        config.timezone = tz_name
        db.commit()
        user = app.system.create_user_account(
            "Direct Booker",
            f"direct-{tz_name.replace('/', '-')}@example.com",
            "Passw0rd1",
        )
        user_id = user.id

    # Starts 1 hour in the past (naive UTC) - i.e. genuinely already started.
    event_id = _create_event(app.system, start_offset_hours=-1, duration_hours=3)

    result = app.system.book_event(user_id, event_id)
    assert "no longer available" in result.lower()


@pytest.mark.parametrize("tz_name", ["America/Los_Angeles", "Europe/Rome"])
def test_service_allows_upcoming_event_regardless_of_timezone(app, tz_name):
    """Companion to the above: a genuinely-upcoming event must still be
    bookable regardless of the configured timezone's UTC offset direction."""
    from app.models import Configuration  # pylint: disable=import-outside-toplevel

    with app.system as db:
        config = Configuration.get_config(db)
        config.timezone = tz_name
        db.commit()
        user = app.system.create_user_account(
            "Upcoming Booker",
            f"upcoming-{tz_name.replace('/', '-')}@example.com",
            "Passw0rd1",
        )
        user_id = user.id

    event_id = _create_event(app.system, start_offset_hours=48, duration_hours=2)
    result = app.system.book_event(user_id, event_id)
    assert result == "Booking confirmed."
