"""Admin Dashboard routes for managing configurations, events, and users."""

from zoneinfo import ZoneInfo, available_timezones
from datetime import datetime, date, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session,
    jsonify,
)

from ..api_utils import api_error
from ..booking_system import Configuration, User, Event, Booking
from ..data_transfer_objects import ConfigurationUpdate, EventData
from ..utils import (
    get_timezone_groups,
    logger,
    month_utc_bounds,
    resolve_calendar_month,
)
from .blueprint import bp
from .security_decorators import admin_required
from .static_pages import render_static_page

_USER_PER_PAGE_OPTIONS = (10, 25, 50, 100)
_DEFAULT_USER_PER_PAGE = 25
_USER_SORT_OPTIONS = ("id_asc", "id_desc", "role", "status", "name_asc", "name_desc")
_BULK_USER_ACTIONS = ("block", "unblock", "role_user", "role_admin")
# Carried from a POSTed form back into the redirect after a single-item
# admin action, so e.g. blocking a user doesn't reset the admin back to
# page 1 of the Calendar tab - they land back on the same tab/page/filters.
_PRESERVABLE_ADMIN_PARAMS = (
    "tab",
    "page",
    "per_page",
    "name",
    "email",
    "role",
    "status",
    "sort",
    "month",
    "year",
)


def _admin_redirect_url():
    """Build a `bp.admin` redirect URL preserving tab/pagination/filter form fields."""
    params = {
        key: request.form.get(key)
        for key in _PRESERVABLE_ADMIN_PARAMS
        if request.form.get(key)
    }
    return url_for("bp.admin", **params)  # type: ignore[arg-type]


def _admin_redirect_url_from_query():
    """Like `_admin_redirect_url`, but for GET-triggered actions (reads
    `request.args` instead of a POSTed form)."""
    params = {
        key: request.args.get(key)
        for key in _PRESERVABLE_ADMIN_PARAMS
        if request.args.get(key)
    }
    return url_for("bp.admin", **params)  # type: ignore[arg-type]


def convert_utc_time_to_local_str(time_obj, target_tz, reference_date):
    """Converts a UTC time object to a local time string in HH:MM format."""
    if not time_obj:
        return ""
    dt_utc = datetime.combine(reference_date, time_obj).replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(target_tz)
    return dt_local.strftime("%H:%M")


@bp.route("/js/admin.js", methods=["GET"])
@admin_required
def admin_js():
    """Load the admin javascript."""
    return render_static_page("static/js/admin/admin.js")


@bp.route("/js/user_accounts.js", methods=["GET"])
@admin_required
def user_accounts_js():
    """Load the User Accounts javascript."""
    return render_static_page("static/js/admin/tabs/user_accounts.js")


@bp.route("/js/events_calendar.js", methods=["GET"])
@admin_required
def events_calendar_js():
    """Load the Events Calendar javascript."""
    return render_static_page("static/js/admin/tabs/events_calendar.js")


def get_config_details(db):
    """Retrieve configuration details and format time strings."""
    config = Configuration.get_config(db)
    config_timezone = ZoneInfo(str(config.timezone))
    today_date = datetime.today().date()
    return {
        "latitude": config.latitude,
        "longitude": config.longitude,
        "timezone": config.timezone,
        "weather_threshold": config.weather_threshold,
        "max_bookings_per_event": config.max_bookings_per_event,
        "default_opening_time": convert_utc_time_to_local_str(
            config.default_opening_time, config_timezone, today_date
        ),
        "default_closing_time": convert_utc_time_to_local_str(
            config.default_closing_time, config_timezone, today_date
        ),
    }


def build_events_data(events, config_timezone):
    """Build events data for calendar display, including each booked user
    (name/email/booking id) so the admin can review and revoke individual
    bookings without a separate lookup."""
    events_data = []
    for event in events:
        start_local = event.start_time.astimezone(config_timezone)
        end_local = event.end_time.astimezone(config_timezone)
        effective_date = start_local.date().isoformat()

        rating = (
            event.weather_rating
            if event.weather_forecast and event.weather_rating is not None
            else "No Data"
        )

        bookings = [
            {
                "booking_id": booking.id,
                "user_id": booking.user_id,
                "name": booking.user.get_name(),
                "email": booking.user.get_email(),
            }
            for booking in event.bookings
        ]

        events_data.append(
            {
                "id": event.id,
                "effective_date": effective_date,
                "opening_time": start_local.strftime("%H:%M"),
                "closing_time": end_local.strftime("%H:%M"),
                "max_bookings": event.max_bookings,
                "weather_rating": rating,
                "num_bookings": len(bookings),
                "bookings": bookings,
                "title": getattr(event, "title", ""),
                "description": getattr(event, "description", ""),
            }
        )
    return events_data


def get_month_events(db, year, month, tz):
    """
    Query only the events within the given month (fixes the previous
    behavior of loading every event ever scheduled into every admin page
    load), eager-loading bookings and their users for capacity/participant
    display without N+1 queries.
    """
    start_utc, end_utc = month_utc_bounds(year, month, tz)
    return (
        db.query(Event)
        .options(joinedload(Event.bookings).joinedload(Booking.user))
        .filter(Event.start_time >= start_utc, Event.start_time < end_utc)
        .all()
    )


def _parse_user_query_params(args):
    """Parse and validate the User Accounts tab's filter/sort/pagination params."""
    try:
        page = max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(args.get("per_page", _DEFAULT_USER_PER_PAGE))
    except (TypeError, ValueError):
        per_page = _DEFAULT_USER_PER_PAGE
    if per_page not in _USER_PER_PAGE_OPTIONS:
        per_page = _DEFAULT_USER_PER_PAGE

    role = args.get("role") or ""
    status = args.get("status") or ""
    sort = args.get("sort") or "id_asc"
    return {
        "page": page,
        "per_page": per_page,
        "name": (args.get("name") or "").strip()[:100],
        "email": (args.get("email") or "").strip()[:254],
        "role": role if role in ("User", "Admin") else "",
        "status": status if status in ("active", "blocked") else "",
        "sort": sort if sort in _USER_SORT_OPTIONS else "id_asc",
    }


def _user_sort_column(sort):
    """Map a `sort` filter value to the SQL ORDER BY column/direction."""
    return {
        "id_desc": User.id.desc(),
        "role": User.role.asc(),
        "status": User.blocked.asc(),
        "name_asc": User.name.asc(),
        "name_desc": User.name.desc(),
    }.get(sort, User.id.asc())


def _build_user_filter_query(db, exclude_user_id, filters):
    """
    Build the base filtered `User` query shared by pagination
    (`get_paginated_users`) and "select all matching" bulk actions
    (`get_matching_user_ids`): the acting admin and any superadmin are
    always excluded, and `role`/`status`/`name` (all plaintext or SQL-native
    columns) are applied directly in SQL. Does not apply `email` search,
    sorting, or pagination - callers handle those themselves.
    """
    query = db.query(User).filter(
        User.id != exclude_user_id,
        User.admin_rank.isnot("super"),
    )
    if filters["role"]:
        query = query.filter(User.role == filters["role"])
    if filters["status"] == "active":
        query = query.filter(User.blocked.is_(False))
    elif filters["status"] == "blocked":
        query = query.filter(User.blocked.is_(True))
    if filters["name"]:
        query = query.filter(User.name.ilike(f"%{filters['name']}%"))
    return query


def get_matching_user_ids(db, exclude_user_id, filters):
    """
    Resolve every user id matching the User Accounts tab's active filters,
    not just the current page - backs the "select all N matching" bulk
    action (as opposed to "select all on this page").

    Returns:
        List[int]: Every matching user id (already excludes the acting
            admin and any superadmin).
    """
    query = _build_user_filter_query(db, exclude_user_id, filters)
    if filters["email"]:
        needle = filters["email"].lower()
        return [user.id for user in query.all() if needle in user.get_email().lower()]
    return [row.id for row in query.with_entities(User.id).all()]


def get_paginated_users(db, exclude_user_id, filters):
    """
    Query, filter, sort, and paginate users for the User Accounts tab.

    `role`/`status`/`name` filters and every sort except by email run
    entirely in SQL. `email` is AES-GCM encrypted at rest with a
    plaintext-derived nonce, so identical plaintext always produces
    identical ciphertext (enabling exact-match lookups elsewhere in the
    app) but ciphertext has no substring-preserving relationship to
    plaintext - an `email` search can't be pushed to SQL and instead
    decrypts and scans the (already role/status/name-filtered) candidate
    rows in Python. `meta["email_search_scanned"]` flags when that
    fallback was used, so the UI can surface the cost to the admin.

    Returns:
        Tuple[List[User], dict]: The current page of users, and pagination
            metadata (`page`, `per_page`, `total`, `total_pages`,
            `email_search_scanned`).
    """
    query = _build_user_filter_query(db, exclude_user_id, filters)
    page, per_page = filters["page"], filters["per_page"]

    if filters["email"]:
        needle = filters["email"].lower()
        matched = [user for user in query.all() if needle in user.get_email().lower()]
        if filters["sort"] == "name_desc":
            matched.sort(key=lambda user: user.name.lower(), reverse=True)
        elif filters["sort"] == "name_asc":
            matched.sort(key=lambda user: user.name.lower())
        elif filters["sort"] == "id_desc":
            matched.sort(key=lambda user: user.id, reverse=True)
        else:
            matched.sort(key=lambda user: user.id)
        total = len(matched)
        start = (page - 1) * per_page
        users = matched[start : start + per_page]
        email_scanned = True
    else:
        total = query.count()
        users = (
            query.order_by(_user_sort_column(filters["sort"]))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        email_scanned = False

    total_pages = max(1, -(-total // per_page))  # ceil division
    meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "email_search_scanned": email_scanned,
    }
    return users, meta


@bp.route("/admin", methods=["GET"], endpoint="admin")
@admin_required
def admin():
    """
    Render the admin dashboard page with full configuration, a filtered/
    paginated page of users, and event data.
    """
    system = current_app.system  # type: ignore[attr-defined]
    actor_id = session.get("user", {}).get("id")
    active_tab = request.args.get("tab", "calendar")
    if active_tab not in ("calendar", "users", "configuration"):
        active_tab = "calendar"
    try:
        with system as db:
            config = Configuration.get_config(db)
            config_timezone = ZoneInfo(str(config.timezone))
            config_dict = get_config_details(db)

            user_filters = _parse_user_query_params(request.args)
            users, users_meta = get_paginated_users(db, actor_id, user_filters)

            cal_year, cal_month = resolve_calendar_month(request.args, config_timezone)
            events = get_month_events(db, cal_year, cal_month, config_timezone)
            events_data = build_events_data(events, config_timezone)
        return render_template(
            "admin/admin.html",
            config=config_dict,
            timezone_groups=get_timezone_groups(),
            users=users,
            users_meta=users_meta,
            user_filters=user_filters,
            events=events,
            events_data=events_data,
            calendar_year=cal_year,
            calendar_month=cal_month,
            active_tab=active_tab,
        )
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Admin dashboard error: %s", error)
        flash("An error occurred while loading the admin dashboard.", "error")
        return redirect(url_for("bp.admin"))


@bp.route("/api/v1/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    """JSON API: list users matching the same filters as the User Accounts tab."""
    system = current_app.system  # type: ignore[attr-defined]
    actor_id = session.get("user", {}).get("id")
    try:
        with system as db:
            filters = _parse_user_query_params(request.args)
            users, meta = get_paginated_users(db, actor_id, filters)
            data = [
                {
                    "id": user.id,
                    "name": user.get_name(),
                    "email": user.get_email(),
                    "role": user.role,
                    "blocked": user.blocked,
                }
                for user in users
            ]
        return jsonify(data=data, meta=meta, errors=None)
    except SQLAlchemyError as error:
        current_app.logger.error("API admin users error: %s", error)
        return api_error("An error occurred while loading users.")


def _resolve_bulk_user_targets(system, actor_id, scope, payload):
    """
    Resolve the target user ids and protected-id set for a bulk user action.

    Returns:
        Tuple[List[int], set, Optional[Response]]: `user_ids`, `protected_ids`,
            and `error_response`. `error_response` is `None` on success; when
            set, the caller must return it immediately instead of proceeding.
    """
    try:
        with system as db:
            if scope == "all_matching":
                # get_matching_user_ids already excludes the acting admin
                # and any superadmin at the query level, so there's nothing
                # left to protect against here.
                filters = _parse_user_query_params(payload.get("filters") or {})
                return get_matching_user_ids(db, actor_id, filters), set(), None

            raw_ids = payload.get("user_ids") or []
            try:
                user_ids = [int(raw_id) for raw_id in raw_ids]
            except (TypeError, ValueError):
                return [], set(), api_error("Invalid user id in selection.", 400)
            if not user_ids:
                return [], set(), api_error("No users selected.", 400)
            # Re-derive the protected set server-side - never trust the
            # client's selection to have already excluded the acting admin
            # or the superadmin.
            protected_ids = {
                row.id
                for row in db.query(User.id).filter(
                    User.id.in_(user_ids),
                    (User.id == actor_id) | (User.admin_rank == "super"),
                )
            }
            return user_ids, protected_ids, None
    except SQLAlchemyError as error:
        current_app.logger.error("Bulk user action lookup failed: %s", error)
        return [], set(), api_error("Failed to process selection.")


@bp.route("/api/v1/admin/users/bulk", methods=["POST"])
@admin_required
def api_admin_users_bulk():
    """
    JSON API: apply one action (block/unblock/role change) to a batch of
    users at once, either just the rows checked on the current page
    (`scope: "selected"`, the default) or every user matching the tab's
    active filters (`scope: "all_matching"`, with a `filters` object shaped
    like the User Accounts tab's query params) - mirroring the
    "select all N videos" pattern from similar bulk-management UIs, where
    "select all on this page" can be expanded to "select all matching".

    Loops over the existing single-item `AdminService.update_user_role`/
    `block_user` methods rather than a dedicated bulk-update query, reusing
    their proven guards (an Admin can't be blocked, a superadmin's role
    can't be changed) instead of re-implementing them. The page-scoped case
    is bounded to <=100 rows (`_USER_PER_PAGE_OPTIONS`); the all-matching
    case can be larger, but is still a bounded, explicit admin action.
    """
    system = current_app.system  # type: ignore[attr-defined]
    actor_id = session.get("user", {}).get("id")
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    scope = payload.get("scope", "selected")

    if action not in _BULK_USER_ACTIONS:
        return api_error("Invalid bulk action.", 400)
    if scope not in ("selected", "all_matching"):
        return api_error("Invalid selection scope.", 400)

    user_ids, protected_ids, error_response = _resolve_bulk_user_targets(
        system, actor_id, scope, payload
    )
    if error_response is not None:
        return error_response

    targets = [user_id for user_id in user_ids if user_id not in protected_ids]
    succeeded = 0
    failed = 0
    for user_id in targets:
        try:
            if action == "block":
                system.block_user(user_id, True)
            elif action == "unblock":
                system.block_user(user_id, False)
            elif action == "role_user":
                system.update_user_role(user_id, "User")
            else:
                system.update_user_role(user_id, "Admin")
            succeeded += 1
        except (SQLAlchemyError, ValueError) as error:
            current_app.logger.error(
                "Bulk action '%s' failed for user %s: %s", action, user_id, error
            )
            failed += 1

    logger.info(
        "Admin ID %s ran bulk action '%s' on %d users "
        "(%d succeeded, %d skipped as protected, %d failed).",
        actor_id,
        action,
        len(user_ids),
        succeeded,
        len(protected_ids),
        failed,
    )
    return jsonify(
        data={
            "succeeded": succeeded,
            "skipped": len(protected_ids),
            "failed": failed,
        },
        errors=None,
    )


@bp.route("/api/v1/admin/events", methods=["GET"])
@admin_required
def api_admin_events():
    """JSON API: list events for the given (or current) month, for the
    Events Calendar tab's prev/next month navigation."""
    system = current_app.system  # type: ignore[attr-defined]
    try:
        with system as db:
            config = Configuration.get_config(db)
            tz = ZoneInfo(str(config.timezone))
            cal_year, cal_month = resolve_calendar_month(request.args, tz)
            events = get_month_events(db, cal_year, cal_month, tz)
            events_data = build_events_data(events, tz)
        return jsonify(
            data=events_data,
            meta={"year": cal_year, "month": cal_month},
            errors=None,
        )
    except SQLAlchemyError as error:
        current_app.logger.error("API admin events error: %s", error)
        return api_error("An error occurred while loading events.")


@bp.route(
    "/api/v1/admin/events/<int:event_id>/bookings/<int:booking_id>/revoke",
    methods=["POST"],
)
@admin_required
def api_revoke_booking(event_id, booking_id):
    """
    JSON API: revoke (delete) a single booking on an event, as a corrective
    admin action - unlike the user-facing self-cancel route, this is
    allowed even after the event has started, and gives the admin a real
    path to shrink an event's capacity or fully clear it before deleting it.
    """
    system = current_app.system  # type: ignore[attr-defined]
    actor_id = session.get("user", {}).get("id")
    try:
        with system as db:
            booking = (
                db.query(Booking)
                .filter(Booking.id == booking_id, Booking.event_id == event_id)
                .first()
            )
            if not booking:
                return api_error("Booking not found.", 404)
            db.delete(booking)
            db.flush()

            event = db.query(Event).filter(Event.id == event_id).first()
            remaining = db.query(Booking).filter(Booking.event_id == event_id).all()
            if event and len(remaining) < event.max_bookings:
                event.available = True
            db.commit()

            bookings_info = [
                {
                    "booking_id": remaining_booking.id,
                    "user_id": remaining_booking.user_id,
                    "name": remaining_booking.user.get_name(),
                    "email": remaining_booking.user.get_email(),
                }
                for remaining_booking in remaining
            ]
        logger.info(
            "Admin ID %s revoked booking %s for event %s.",
            actor_id,
            booking_id,
            event_id,
        )
        return jsonify(
            data={"num_bookings": len(bookings_info), "bookings": bookings_info},
            errors=None,
        )
    except SQLAlchemyError as error:
        current_app.logger.error("Revoke booking error: %s", error)
        return api_error("Failed to revoke booking.")


@bp.route("/admin/config", methods=["GET", "POST"])
@admin_required
def update_configuration():  # pylint: disable=too-many-locals
    """Updates configuration settings from the admin dashboard."""
    if request.method == "GET":
        return redirect(url_for("bp.admin"))
    try:
        latitude_str = request.form.get("latitude")
        longitude_str = request.form.get("longitude")
        if latitude_str is None or longitude_str is None:
            raise ValueError("Latitude and Longitude are required.")
        latitude = float(latitude_str)
        longitude = float(longitude_str)
        timezone_str = request.form.get("timezone")
        if timezone_str not in available_timezones():
            raise ValueError(f"Invalid timezone: {timezone_str}")
        weather_threshold_str = request.form.get("weather_threshold")
        max_bookings_str = request.form.get("max_bookings_per_event")
        if (
            weather_threshold_str is None
            or max_bookings_str is None
            or timezone_str is None
        ):
            raise ValueError("Missing required form fields.")
        weather_threshold = int(weather_threshold_str)
        max_bookings_per_event = int(max_bookings_str)
        default_opening_time_str = request.form.get("default_opening_time")
        default_closing_time_str = request.form.get("default_closing_time")
        validate_config_inputs(
            latitude, longitude, weather_threshold, max_bookings_per_event
        )
        default_opening_time_utc, default_closing_time_utc = process_time_inputs(
            default_opening_time_str, default_closing_time_str, timezone_str
        )
    except (ValueError, TypeError, SQLAlchemyError) as error:
        current_app.logger.error("Config input error: %s", error)
        flash("Invalid input. Please check your configuration values.", "error")
        return redirect(url_for("bp.admin"))
    try:
        system = current_app.system  # type: ignore[attr-defined]
        config_update = ConfigurationUpdate(
            latitude=latitude,
            longitude=longitude,
            timezone_str=timezone_str,
            weather_threshold=weather_threshold,
            max_bookings_per_event=max_bookings_per_event,
            default_opening_time=default_opening_time_utc,
            default_closing_time=default_closing_time_utc,
        )
        system.update_configuration(config_update)
        flash("Configuration updated successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Config update error: %s", error)
        flash("Failed to update configuration.", "error")
    return redirect(url_for("bp.admin"))


def validate_config_inputs(
    latitude: float,
    longitude: float,
    weather_threshold,
    max_bookings_per_event,
):
    """Validate ranges for latitude, longitude, weather threshold, and booking limits."""
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    if not 0 <= weather_threshold <= 100:
        raise ValueError("Cloud threshold must be between 0 and 100.")
    if max_bookings_per_event < 1:
        raise ValueError("Maximum bookings per event must be at least 1.")


def process_time_inputs(opening_time_str, closing_time_str, timezone_str):
    """Process time inputs from form strings to UTC time objects."""
    default_opening_time_local = datetime.strptime(opening_time_str, "%H:%M").time()
    default_closing_time_local = datetime.strptime(closing_time_str, "%H:%M").time()
    reference_date = date(2000, 1, 1)
    form_timezone = ZoneInfo(timezone_str)
    opening_local_dt = datetime.combine(
        reference_date, default_opening_time_local, tzinfo=form_timezone
    )
    closing_local_dt = datetime.combine(
        reference_date, default_closing_time_local, tzinfo=form_timezone
    )
    default_opening_time_utc = opening_local_dt.astimezone(timezone.utc).time()
    default_closing_time_utc = closing_local_dt.astimezone(timezone.utc).time()
    return default_opening_time_utc, default_closing_time_utc


@bp.route("/admin/update_events_weather", methods=["GET"])
@admin_required
def update_events_weather():
    """Updates events weather using the system logic."""
    try:
        current_app.system.update_events_weather()  # type: ignore[attr-defined]
        flash("Weather updated successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Update events weather error: %s", error)
        flash("An error occurred while regenerating events.", "error")
    return redirect(_admin_redirect_url_from_query())


@bp.route("/admin/confirm_event", methods=["GET", "POST"])
@admin_required
def confirm_event():
    """Creates or updates an event based on admin input."""
    if request.method == "GET":
        return redirect(url_for("bp.admin"))
    try:
        return handle_confirm_event()
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Confirm event error: %s", error)
        flash("Error processing event.", "error")
    return redirect(_admin_redirect_url())


def handle_confirm_event():
    """Handle the event confirmation logic."""
    title = request.form.get("event_title", "").strip()
    description = request.form.get("event_description", "").strip()
    event_id = request.form.get("event_id")
    event_date_str = request.form.get("event_date")
    opening_time_str = request.form.get("opening_time")
    closing_time_str = request.form.get("closing_time")
    try:
        max_bookings = int(request.form.get("max_bookings", "0"))
    except ValueError as error:
        raise ValueError("Invalid max bookings value.") from error
    if len(title) > 30:
        flash("Title cannot exceed 30 characters.", "error")
        return redirect(_admin_redirect_url())
    if len(description) > 255:
        flash("Description cannot exceed 255 characters.", "error")
        return redirect(_admin_redirect_url())
    if not event_date_str or not opening_time_str or not closing_time_str:
        raise ValueError("Date, Time and Max Booking fields must be provided.")
    try:
        event_date_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Invalid event date format.") from error
    event_date = datetime.combine(event_date_date, datetime.min.time())
    opening_time = datetime.strptime(opening_time_str, "%H:%M").time()
    closing_time = datetime.strptime(closing_time_str, "%H:%M").time()

    event_data = EventData(
        event_title=title,
        event_description=description,
        event_date=event_date,
        opening_time=opening_time,
        closing_time=closing_time,
        max_bookings=max_bookings,
    )
    system = current_app.system  # type: ignore[attr-defined]
    result = system.confirm_event(event_data, event_id=event_id)
    flash(result, "success" if "successfully" in result.lower() else "error")
    return redirect(_admin_redirect_url())


@bp.route("/admin/delete_event/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):
    """Deletes an event if it has no existing bookings and hasn't started yet."""
    try:
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            # pylint: disable=duplicate-code
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                flash("Event not found", "error")
                return redirect(_admin_redirect_url())
            event_start_time_aware = event.start_time.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            if event_start_time_aware <= now_utc:
                flash(
                    "Cannot delete an event that has finished or already started.",
                    "error",
                )
                return redirect(_admin_redirect_url())
            if event.bookings:
                flash("Cannot delete event with existing bookings", "error")
                return redirect(_admin_redirect_url())
            db.delete(event)
            db.commit()
            flash("Event deleted successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Delete event error: %s", error)
        flash("Error deleting event.", "error")
    return redirect(_admin_redirect_url())


@bp.route("/admin/user/role", methods=["POST"])
@admin_required
def update_user_role():
    """Updates a user's role via the admin dashboard."""
    try:
        raw_id = request.form.get("user_id")
        try:
            user_id = int(raw_id)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            flash("Invalid user ID.", "error")
            return redirect(_admin_redirect_url())
        new_role = request.form.get("new_role")
        actor_id = session.get("user", {}).get("id")
        current_app.system.update_user_role(user_id, new_role)  # type: ignore[attr-defined]
        logger.info(
            "Admin ID %s updated role of user ID %s to '%s'.",
            actor_id,
            user_id,
            new_role,
        )
        flash("User role updated successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Update role error: %s", error)
        flash("Failed to update user role.", "error")
    return redirect(_admin_redirect_url())


@bp.route("/admin/user/block", methods=["POST"])
@admin_required
def block_user():
    """Blocks or unblocks a user via the admin dashboard."""
    try:
        raw_id = request.form.get("user_id")
        if raw_id is None:
            flash("Missing user ID.", "error")
            return redirect(_admin_redirect_url())
        try:
            user_id = int(raw_id)
        except (ValueError, TypeError):
            flash("Invalid user ID.", "error")
            return redirect(_admin_redirect_url())
        block_value = request.form.get("block")
        if block_value is None:
            flash("Missing block value.", "error")
            return redirect(_admin_redirect_url())
        block = handle_block_user_logic(user_id, block_value)
        actor_id = session.get("user", {}).get("id")
        current_app.system.block_user(user_id, block)  # type: ignore[attr-defined]
        action = "blocked" if block else "unblocked"
        logger.info("Admin ID %s %s user ID %s.", actor_id, action, user_id)
        flash(f"User {action} successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Block user error: %s", error)
        flash("Failed to update user block status.", "error")
    return redirect(_admin_redirect_url())


def handle_block_user_logic(user_id, block_value):
    """Handle the logic for blocking/unblocking a user."""
    if block_value == "toggle":
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            target_user = db.query(User).filter(User.id == user_id).first()
            if not target_user:
                raise ValueError("User not found.")
            return not target_user.blocked
    return block_value.lower() == "true"


@bp.route("/admin/user/delete", methods=["POST"])
@admin_required
def delete_user():
    """Handle the logic for deleting a user account."""
    current_user_rank = session.get("user", {}).get("admin_rank")
    if current_user_rank != "super":
        flash("Only superadmin can delete user accounts.", "error")
        return redirect(_admin_redirect_url())
    raw_id = request.form.get("user_id")
    try:
        user_id = int(raw_id)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        flash("Invalid user ID.", "error")
        return redirect(_admin_redirect_url())
    actor_id = session.get("user", {}).get("id")
    try:
        current_app.system.delete_user(user_id)  # type: ignore[attr-defined]
        logger.info("Superadmin ID %s deleted user ID %s.", actor_id, user_id)
        flash("User account deleted successfully.", "success")
    except (ValueError, SQLAlchemyError) as e:
        current_app.logger.error("User deletion failed: %s", e)
        flash("Failed to delete user.", "error")
    return redirect(_admin_redirect_url())
