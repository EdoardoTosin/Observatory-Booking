"""Admin Dashboard routes for managing configurations, events, and users."""

import json
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
)

from ..booking_system import Configuration, User, Slot, Booking
from ..data_transfer_objects import ConfigurationUpdate, EventData
from .blueprint import bp
from .security_decorators import admin_required
from .static_pages import render_static_page


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


def build_events_data(slots, config_timezone):
    """Build events data for calendar display."""
    events_data = []
    for slot in slots:
        start_local = slot.start_time.astimezone(config_timezone)
        end_local = slot.end_time.astimezone(config_timezone)
        effective_date = slot.start_time.date().isoformat()

        rating = (
            slot.weather_rating
            if slot.weather_forecast and slot.weather_rating is not None
            else "No Data"
        )

        events_data.append(
            {
                "id": slot.id,
                "effective_date": effective_date,
                "opening_time": start_local.strftime("%H:%M"),
                "closing_time": end_local.strftime("%H:%M"),
                "max_bookings": slot.max_bookings,
                "weather_rating": rating,
                "num_bookings": len(slot.bookings),
                "title": getattr(slot, "title", ""),
                "description": getattr(slot, "description", ""),
            }
        )
    return events_data


@bp.route("/admin", methods=["GET"], endpoint="admin")
@admin_required
def admin():
    """
    Render the admin dashboard page with full configuration, user, booking,
    and event slot data.
    """
    system = current_app.system  # type: ignore[attr-defined]
    try:
        with system as db:
            config = Configuration.get_config(db)
            config_timezone = ZoneInfo(str(config.timezone))
            config_dict = get_config_details(db)
            users = db.query(User).all()
            bookings = db.query(Booking).all()
            slots = db.query(Slot).options(joinedload(Slot.bookings)).all()
            events_json = json.dumps(build_events_data(slots, config_timezone))
        return render_template(
            "admin/admin.html",
            config=config_dict,
            users=users,
            bookings=bookings,
            slots=slots,
            events_json=events_json,
        )
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Admin dashboard error: %s", error)
        flash("An error occurred while loading the admin dashboard.", "error")
        return redirect(url_for("bp.admin"))


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
        flash(f"Input error: {error}", "error")
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
    return redirect(url_for("bp.admin"))


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
        flash(f"Error processing event: {error}", "error")
    return redirect(url_for("bp.admin"))


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
        return redirect(url_for("bp.admin"))
    if len(description) > 255:
        flash("Description cannot exceed 255 characters.", "error")
        return redirect(url_for("bp.admin"))
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
    return redirect(url_for("bp.admin"))


@bp.route("/admin/delete_event/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):
    """Deletes an event if it has no existing bookings and hasn't started yet."""
    try:
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            slot = db.query(Slot).filter(Slot.id == event_id).first()
            if not slot:
                flash("Event not found", "error")
                return redirect(url_for("bp.admin"))
            slot_start_time_aware = slot.start_time.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            if slot_start_time_aware <= now_utc:
                flash(
                    "Cannot delete an event that has finished or already started.",
                    "error",
                )
                return redirect(url_for("bp.admin"))
            if slot.bookings:
                flash("Cannot delete event with existing bookings", "error")
                return redirect(url_for("bp.admin"))
            db.delete(slot)
            db.commit()
            flash("Event deleted successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Delete event error: %s", error)
        flash(f"Error deleting event: {error}", "error")
    return redirect(url_for("bp.admin"))


@bp.route("/admin/user/role", methods=["POST"])
@admin_required
def update_user_role():
    """Updates a user's role via the admin dashboard."""
    try:
        user_id = str(request.form.get("user_id"))
        new_role = request.form.get("new_role")
        current_app.system.update_user_role(user_id, new_role)  # type: ignore[attr-defined]
        flash("User role updated successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Update role error: %s", error)
        flash(str(error), "error")
    return redirect(url_for("bp.admin"))


@bp.route("/admin/user/block", methods=["POST"])
@admin_required
def block_user():
    """Blocks or unblocks a user via the admin dashboard."""
    try:
        user_id = str(request.form.get("user_id"))
        if user_id is None:
            raise ValueError("Missing 'user_id' value in request.")
        block_value = request.form.get("block")
        if block_value is None:
            raise ValueError("Missing 'block' value in request.")
        block = handle_block_user_logic(user_id, block_value)
        current_app.system.block_user(user_id, block)  # type: ignore[attr-defined]
        flash(f"User {'blocked' if block else 'unblocked'} successfully", "success")
    except (SQLAlchemyError, ValueError) as error:
        current_app.logger.error("Block user error: %s", error)
        flash(str(error), "error")
    return redirect(url_for("bp.admin"))


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
        return redirect(url_for("bp.admin"))
    user_id = request.form.get("user_id")
    try:
        current_app.system.delete_user(user_id)  # type: ignore[attr-defined]
        flash("User account deleted successfully.", "success")
    except (ValueError, SQLAlchemyError) as e:
        current_app.logger.error("User deletion failed: %s", e)
        flash(f"Failed to delete user: {str(e)}", "error")
    return redirect(url_for("bp.admin"))
