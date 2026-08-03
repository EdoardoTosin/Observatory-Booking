"""Admin Events Calendar tab regression tests: month-scoping, capacity
min-enforcement, and booking revocation.
"""

import json
from datetime import datetime, timedelta, timezone

from helpers import current_csrf_token, login_as_admin, register


def _create_event(system, start_offset_hours=48, duration_hours=2, max_bookings=2):
    from app.models import Event  # pylint: disable=import-outside-toplevel

    start = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) + timedelta(
        hours=start_offset_hours
    )
    end = start + timedelta(hours=duration_hours)
    with system as db:
        event = Event(
            title="Admin Test Event",
            description="Created directly for admin event tests.",
            start_time=start,
            end_time=end,
            max_bookings=max_bookings,
            available=True,
        )
        db.add(event)
        db.commit()
        return event.id


def test_month_scoped_events_api(client, app):
    event_id = _create_event(app.system, start_offset_hours=48)
    login_as_admin(client)

    with app.system as db:
        from app.models import Event  # pylint: disable=import-outside-toplevel

        event = db.query(Event).filter(Event.id == event_id).first()
        year, month = event.start_time.year, event.start_time.month

    response = client.get(f"/api/v1/admin/events?year={year}&month={month}")
    body = json.loads(response.data)
    assert any(row["id"] == event_id for row in body["data"])

    # A month with nothing scheduled should come back empty.
    other_year = year - 1
    response_empty = client.get(f"/api/v1/admin/events?year={other_year}&month={month}")
    body_empty = json.loads(response_empty.data)
    assert body_empty["data"] == []


def test_capacity_cannot_be_reduced_below_confirmed_bookings(client, app):
    # Needs 2 confirmed bookings: max_bookings=1 is otherwise a perfectly
    # valid value (the general "at least 1" input check would reject 0
    # before ever reaching the capacity-vs-confirmed-count check this test
    # targets), so reducing to 1 only tests the right thing with 2 already
    # booked.
    event_id = _create_event(app.system, max_bookings=3)

    register(client, "Capacity Booker", "capacitybooker@example.com", "Passw0rd1")
    result = app.system.book_event(_user_id(app, "Capacity Booker"), event_id)
    assert result == "Booking confirmed."
    client.get("/logout")

    register(client, "Capacity Booker 2", "capacitybooker2@example.com", "Passw0rd1")
    result = app.system.book_event(_user_id(app, "Capacity Booker 2"), event_id)
    assert result == "Booking confirmed."
    client.get("/logout")

    login_as_admin(client)
    with app.system as db:
        from app.models import Event  # pylint: disable=import-outside-toplevel

        event = db.query(Event).filter(Event.id == event_id).first()
        event_date = event.start_time.date().isoformat()
        opening = event.start_time.strftime("%H:%M")
        closing = event.end_time.strftime("%H:%M")

    csrf = current_csrf_token(client)
    response = client.post(
        "/admin/confirm_event",
        data={
            "_csrf_token": csrf,
            "event_id": str(event_id),
            "event_title": "Admin Test Event",
            "event_description": "Created directly for admin event tests.",
            "event_date": event_date,
            "opening_time": opening,
            "closing_time": closing,
            "max_bookings": "1",  # below the 2 confirmed bookings
        },
        follow_redirects=True,
    )
    assert b"Cannot reduce capacity below" in response.data


def test_revoke_booking(client, app):
    event_id = _create_event(app.system, max_bookings=2)
    register(client, "Revoke Target", "revoketarget@example.com", "Passw0rd1")
    user_id = _user_id(app, "Revoke Target")
    app.system.book_event(user_id, event_id)
    client.get("/logout")

    login_as_admin(client)
    with app.system as db:
        from app.models import Booking  # pylint: disable=import-outside-toplevel

        booking = db.query(Booking).filter(Booking.event_id == event_id).first()
        booking_id = booking.id

    csrf = current_csrf_token(client)
    response = client.post(
        f"/api/v1/admin/events/{event_id}/bookings/{booking_id}/revoke",
        headers={"X-CSRF-Token": csrf},
        content_type="application/json",
        data="{}",
    )
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["data"]["num_bookings"] == 0

    with app.system as db:
        from app.models import Booking  # pylint: disable=import-outside-toplevel

        assert db.query(Booking).filter(Booking.id == booking_id).first() is None


def _user_id(app, name):
    from app.models import User  # pylint: disable=import-outside-toplevel

    with app.system as db:
        user = db.query(User).filter(User.name == name).first()
        if user is None:
            raise AssertionError(f"user with name {name!r} not found")
        return user.id
