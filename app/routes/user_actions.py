"""User actions routes module.

This module handles event viewing, searching/filtering, booking, cancellation,
and password management for authenticated users.
"""

import calendar
import hmac
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    make_response,
    jsonify,
)
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ..api_utils import api_error
from ..booking_system import Event, Booking, Configuration, User
from ..utils import is_password_strong, month_utc_bounds, resolve_calendar_month
from .blueprint import bp
from .security_decorators import login_required
from .static_pages import render_static_page

# "Browse by month" substitutes for numbered pagination on the events page
# (see Phase 1 of the UX plan): with no explicit date/range filter, show a
# rolling window instead of every future event ever scheduled.
DEFAULT_WINDOW_DAYS = 30
# Guardrail against a client requesting an unbounded ?from=&to= span.
MAX_DATE_RANGE_DAYS = 90
_SORT_OPTIONS = ("date_asc", "date_desc", "weather_desc")


@bp.route("/js/events.js", methods=["GET"])
@login_required
def events_js():
    """Load the events javascript.

    Returns:
        Any: The javascript 'events.js' file.
    """
    return render_static_page("static/js/user/events.js")


def _get_booked_counts(db, event_ids):
    """Return {event_id: confirmed_booking_count} for the given event ids.

    A single grouped query instead of one COUNT(*) per event, so this stays
    flat regardless of how many events are being displayed.
    """
    if not event_ids:
        return {}
    # pylint: disable-next=not-callable
    count_column = func.count(Booking.id)
    return dict(
        db.query(Booking.event_id, count_column)
        .filter(Booking.event_id.in_(event_ids))
        .group_by(Booking.event_id)
        .all()
    )


def _local_day_bounds_utc(date_str, tz):
    """Convert a local YYYY-MM-DD string to naive UTC [start, end) bounds.

    Raises:
        ValueError: If `date_str` isn't a valid YYYY-MM-DD date.
    """
    local_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    local_start = datetime.combine(local_date, datetime.min.time(), tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(timezone.utc).replace(tzinfo=None),
        local_end.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _parse_event_query_params(args):
    """Parse and lightly validate the /events (and /api/v1/events) query params."""
    sort = args.get("sort")
    return {
        "q": (args.get("q") or "").strip()[:100],
        "date": (args.get("date") or "").strip(),
        "date_from": (args.get("from") or "").strip(),
        "date_to": (args.get("to") or "").strip(),
        "avail_only": args.get("avail") == "1",
        "no_warning": args.get("no_warning") == "1",
        "sort": sort if sort in _SORT_OPTIONS else "date_asc",
    }


def _apply_date_range(query, filters, tz):
    """Apply an optional ?from=&to= range filter, clamped to MAX_DATE_RANGE_DAYS.

    Returns:
        Tuple[Query, bool]: The filtered query, and whether the requested
            range had to be clamped.
    """
    clamped = False
    date_from, date_to = filters["date_from"], filters["date_to"]
    try:
        if date_from:
            start, _ = _local_day_bounds_utc(date_from, tz)
            query = query.filter(Event.start_time >= start)
        if date_to:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            if date_from:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                if (to_date - from_date).days > MAX_DATE_RANGE_DAYS:
                    to_date = from_date + timedelta(days=MAX_DATE_RANGE_DAYS)
                    clamped = True
            _, end = _local_day_bounds_utc(to_date.isoformat(), tz)
            query = query.filter(Event.start_time < end)
    except ValueError:
        pass
    return query, clamped


def _apply_sort(query, sort):
    """Order the event query per the resolved `sort` filter value."""
    if sort == "date_desc":
        return query.order_by(Event.start_time.desc())
    if sort == "weather_desc":
        return query.order_by(Event.weather_rating.desc().nullslast())
    return query.order_by(Event.start_time.asc())


def _load_events(db, user_id, tz, now_utc, filters):
    """Query and annotate events matching `filters` for the given user.

    Applies the search/date/sort filters in SQL, then attaches the
    per-event `is_fully_booked`/`is_user_booked` flags (one grouped booking
    count query, not one per event), and finally applies the `avail_only`
    filter in Python against that small, already-bounded result set.

    Returns:
        Tuple[List[Event], bool]: The matching events, and whether an
            explicit ?from=&to= range had to be clamped.
    """
    query = db.query(Event).filter(Event.start_time > now_utc)

    if filters["q"]:
        query = query.filter(Event.title.ilike(f"%{filters['q']}%"))

    clamped = False
    if filters["date"]:
        try:
            start, end = _local_day_bounds_utc(filters["date"], tz)
            query = query.filter(Event.start_time >= start, Event.start_time < end)
        except ValueError:
            pass
    elif filters["date_from"] or filters["date_to"]:
        query, clamped = _apply_date_range(query, filters, tz)
    else:
        query = query.filter(
            Event.start_time < now_utc + timedelta(days=DEFAULT_WINDOW_DAYS)
        )

    if filters["no_warning"]:
        query = query.filter(Event.weather_warning.isnot(True))

    query = _apply_sort(query, filters["sort"])
    events_list = query.all()

    user_bookings = {
        b.event_id
        for b in db.query(Booking.event_id).filter(Booking.user_id == user_id)
    }
    booked_counts = _get_booked_counts(db, [event.id for event in events_list])

    for event in events_list:
        if event.start_time.tzinfo is None:
            event.start_time = event.start_time.replace(tzinfo=timezone.utc)
        if event.end_time.tzinfo is None:
            event.end_time = event.end_time.replace(tzinfo=timezone.utc)
        booked_count = booked_counts.get(event.id, 0)
        event.is_fully_booked = booked_count >= event.max_bookings
        event.is_user_booked = event.id in user_bookings

    if filters["avail_only"]:
        events_list = [
            event
            for event in events_list
            if not event.is_fully_booked and not event.is_user_booked
        ]

    return events_list, clamped


def _serialize_event(event):
    """Serialize an annotated Event row for the JSON API."""
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "max_bookings": event.max_bookings,
        "weather_rating": event.weather_rating,
        "weather_warning": event.weather_warning,
        "is_fully_booked": event.is_fully_booked,
        "is_user_booked": event.is_user_booked,
    }


def get_month_day_set(db, year, month, tz):
    # pylint: disable=duplicate-code
    """Return the set of local ISO date strings with >=1 event in the given month.

    At most ~31 rows thanks to AdminService's "one event per day" rule, so
    this is always a cheap query regardless of how large the events table is.
    (Mirrors admin_dashboard.get_month_events's shape - both are thin
    wrappers around the shared month_utc_bounds helper, returning different
    projections of the same month-scoped query.)
    """
    start_utc, end_utc = month_utc_bounds(year, month, tz)
    rows = (
        db.query(Event.start_time)
        .filter(Event.start_time >= start_utc, Event.start_time < end_utc)
        .all()
    )
    return {
        row.start_time.replace(tzinfo=timezone.utc).astimezone(tz).date().isoformat()
        for row in rows
    }


def build_calendar_weeks(year, month, day_set, today_str):
    """Build a Sunday-first month grid for the date-picker.

    Returns:
        List[List[dict]]: Weeks, each a list of 7 day-cell dicts (leading/
            trailing days from adjacent months are included to fill the grid).
    """
    cal = calendar.Calendar(
        firstweekday=6
    )  # 6 = Sunday, matches admin calendar's header
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_cells = []
        for day in week:
            date_str = day.isoformat()
            week_cells.append(
                {
                    "date": date_str,
                    "day": day.day,
                    "in_month": day.month == month,
                    "has_events": date_str in day_set,
                    "is_past": date_str < today_str,
                    "is_today": date_str == today_str,
                }
            )
        weeks.append(week_cells)
    return weeks


def _build_event_view_context(db, user_id):
    """Load everything the events page (and its API counterpart) need.

    Shared by the Jinja route (first paint) and the JSON API route
    (re-fetches on filter/date/sort change), so both stay in sync against
    one query implementation.
    """
    config = Configuration.get_config(db)
    tz = ZoneInfo(str(config.timezone))
    now_utc = datetime.now(timezone.utc)

    filters = _parse_event_query_params(request.args)
    events_list, clamped = _load_events(db, user_id, tz, now_utc, filters)

    cal_year, cal_month = resolve_calendar_month(request.args, tz)
    day_set = get_month_day_set(db, cal_year, cal_month, tz)

    return {
        "config_timezone": config.timezone,
        "now_utc": now_utc,
        "filters": filters,
        "events": events_list,
        "clamped": clamped,
        "calendar_year": cal_year,
        "calendar_month": cal_month,
        "calendar_day_set": day_set,
    }


@bp.route("/events", methods=["GET"], endpoint="events")
@login_required
def events():
    """
    Render the event booking page: search, date/date-range filters,
    sorting, and a "browse by month" date-picker.

    Booking and cancellation are handled by the dedicated /booking and
    /cancel_booking/<event_id> routes, not by this view.
    """
    user_id = session["user"]["id"]
    system = current_app.system  # type: ignore[attr-defined]
    try:
        with system as db:
            ctx = _build_event_view_context(db, user_id)
            today_str = (
                datetime.now(ZoneInfo(str(ctx["config_timezone"]))).date().isoformat()
            )
            calendar_weeks = build_calendar_weeks(
                ctx["calendar_year"],
                ctx["calendar_month"],
                ctx["calendar_day_set"],
                today_str,
            )

        if ctx["clamped"]:
            flash(f"Date range limited to {MAX_DATE_RANGE_DAYS} days.", "error")

        return make_response(
            render_template(
                "user/events.html",
                events=ctx["events"],
                config_timezone=ctx["config_timezone"],
                now_utc=ctx["now_utc"],
                filters=ctx["filters"],
                calendar_weeks=calendar_weeks,
                calendar_year=ctx["calendar_year"],
                calendar_month=ctx["calendar_month"],
            )
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Events error: {e}")
        flash("An error occurred while loading events.", "error")
        return redirect(url_for("bp.events"))


@bp.route("/api/v1/events", methods=["GET"])
@login_required
def api_events():
    """JSON API: list events matching the same filters as the /events page."""
    user_id = session["user"]["id"]
    system = current_app.system  # type: ignore[attr-defined]
    try:
        with system as db:
            ctx = _build_event_view_context(db, user_id)
            data = [_serialize_event(event) for event in ctx["events"]]
        return jsonify(
            data=data,
            meta={
                "count": len(data),
                "date_range_clamped": ctx["clamped"],
                "calendar_year": ctx["calendar_year"],
                "calendar_month": ctx["calendar_month"],
                "calendar_days_with_events": sorted(ctx["calendar_day_set"]),
            },
            errors=None,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"API events error: {e}")
        return api_error("An error occurred while loading events.")


@bp.route("/booking", methods=["POST"])
@login_required
def booking():
    """
    Handle event booking requests.

    Prevents booking if the event has already started or finished.
    """
    try:
        event_id = str(request.form.get("event_id"))
    except (ValueError, TypeError):
        flash("Invalid event selection", "error")
        return redirect(url_for("bp.events"))

    try:
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            # pylint: disable=duplicate-code
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                flash("Event not found", "error")
                return redirect(url_for("bp.events"))

            event_start_time_aware = event.start_time.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)

            if event_start_time_aware <= now_utc:
                flash(
                    "Cannot book an event that has already started or finished.",
                    "error",
                )
                return redirect(url_for("bp.events"))

            result = system.book_event(session["user"]["id"], event_id)
            flash(result, "success" if "confirmed" in result.lower() else "error")
    except SQLAlchemyError as e:
        current_app.logger.error(f"Booking error: {e}")
        flash("An error occurred during booking.", "error")
    return redirect(url_for("bp.events"))


@bp.route("/cancel_booking/<int:event_id>", methods=["POST"])
@login_required
def cancel_booking(event_id):
    """
    Cancel a booking for a specific event.

    Prevents cancellation if the event has already started or finished.
    """
    try:
        user_id = session["user"]["id"]
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            # pylint: disable=duplicate-code
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                flash("Event not found", "error")
                return redirect(url_for("bp.events"))

            event_start_time_aware = event.start_time.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)

            if event_start_time_aware <= now_utc:
                flash(
                    "Cannot cancel a booking for an event that has already started or finished.",
                    "error",
                )
                return redirect(url_for("bp.events"))

            result = system.cancel_booking(user_id, event_id)
            flash(result, "success" if "successfully" in result.lower() else "error")
    except SQLAlchemyError as e:
        current_app.logger.error(f"Cancel booking error: {e}")
        flash("An error occurred while canceling the booking.", "error")
    return redirect(url_for("bp.events"))


@bp.route("/js/change_password.js", methods=["GET"])
@login_required
def change_password_js():
    """Load the change password javascript.

    Returns:
        Any: The javascript 'change_password.js' file.
    """
    return render_static_page("static/js/user/change_password.js")


@bp.route("/change_password", methods=["GET", "POST"], endpoint="change_password")
@login_required
def change_password():  # pylint: disable=too-many-return-statements
    """
    Handle password change requests securely.

    Ensures that the old password is correct, validates the new password,
    and updates the user's password if everything is correct.
    """
    if request.method == "POST":
        old_password = request.form.get("old_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not old_password or not new_password or not confirm_password:
            flash("All fields are required.", "error")
            return redirect(url_for("bp.change_password"))

        if not hmac.compare_digest(
            new_password.encode("utf-8"), confirm_password.encode("utf-8")
        ):
            flash("New password and confirmation do not match.", "error")
            return redirect(url_for("bp.change_password"))

        if old_password == new_password:
            flash("New password cannot be the same as the old password.", "error")
            return redirect(url_for("bp.change_password"))

        if not is_password_strong(new_password):
            flash(
                "Password must be at least 8 characters long, contain uppercase, "
                "lowercase, and at least a number.",
                "error",
            )
            return redirect(url_for("bp.change_password"))

        system = current_app.system  # type: ignore[attr-defined]
        user_id = session["user"]["id"]
        try:
            with system as db:
                user_obj = db.query(User).filter(User.id == user_id).first()

                if not user_obj or not user_obj.verify_password(old_password):
                    flash("Old password is incorrect.", "error")
                    return redirect(url_for("bp.change_password"))

                system.change_user_password(user_id, new_password)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Change password error: {e}")
            flash("An unexpected error occurred while changing your password.", "error")
            return redirect(url_for("bp.change_password"))

        flash("Password changed successfully.", "success")
        return redirect(url_for("bp.events"))

    return render_template("user/change_password.html")
