"""User actions routes module.

This module handles event viewing, booking, cancellation, and password management
for authenticated users.
"""

import hmac
from datetime import datetime, timezone
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
)
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from ..booking_system import Slot, Booking, Configuration, User, UserService
from ..utils import is_password_strong
from .blueprint import bp
from .security_decorators import login_required
from .static_pages import render_static_page


@bp.route("/js/events.js", methods=["GET"])
@login_required
def events_js():
    """Load the events javascript.

    Returns:
        Any: The javascript 'events.js' file.
    """
    return render_static_page("static/js/user/events.js")


@bp.route("/events", methods=["GET", "POST"], endpoint="events")
@login_required
def events():
    """
    Handle rendering and interaction with the event booking page.

    GET: Display available, booked, and fully booked events.
    POST: Book a selected slot, if available.
    """
    user_id = session["user"]["id"]
    system = current_app.system  # type: ignore[attr-defined]
    response = None

    if request.method == "POST":
        try:
            slot_id = str(request.form.get("slot_id"))
        except (ValueError, TypeError):
            flash("Invalid event selection", "error")
            response = redirect(url_for("bp.events"))

        if response is None:
            try:
                result = system.book_slot(user_id, slot_id)
                flash(result, "success" if "confirmed" in result.lower() else "error")
                response = redirect(url_for("bp.events"))
            except SQLAlchemyError as e:
                current_app.logger.error(f"Booking error: {e}")
                flash("An error occurred during booking.", "error")
                response = redirect(url_for("bp.events"))
    else:
        try:
            with system as db:
                config_timezone = Configuration.get_config(db).timezone

                now_utc = datetime.now(ZoneInfo("UTC"))

                slots = db.query(Slot).filter(Slot.start_time > now_utc).all()

                user_bookings = {
                    b.slot_id
                    for b in db.query(Booking.slot_id).filter(
                        Booking.user_id == user_id
                    )
                }
                for slot in slots:

                    if slot.start_time.tzinfo is None:
                        slot.start_time = slot.start_time.replace(
                            tzinfo=ZoneInfo("UTC")
                        )
                    if slot.end_time.tzinfo is None:
                        slot.end_time = slot.end_time.replace(tzinfo=ZoneInfo("UTC"))

                    # pylint: disable=not-callable
                    booked_count = (
                        db.query(func.count(Booking.id))
                        .filter(Booking.slot_id == slot.id)
                        .scalar()
                    )
                    slot.is_fully_booked = booked_count >= slot.max_bookings
                    slot.is_user_booked = slot.id in user_bookings

                response = make_response(
                    render_template(
                        "user/events.html",
                        slots=slots,
                        config_timezone=config_timezone,
                        now_utc=now_utc,
                    )
                )
        except SQLAlchemyError as e:
            current_app.logger.error(f"Events error: {e}")
            flash("An error occurred while loading events.", "error")
            response = redirect(url_for("bp.events"))

    return response


@bp.route("/booking", methods=["POST"])
@login_required
def booking():
    """
    Handle slot booking requests.

    Prevents booking if the event has already started or finished.
    """
    try:
        slot_id = str(request.form.get("slot_id"))
    except (ValueError, TypeError):
        flash("Invalid event selection", "error")
        return redirect(url_for("bp.events"))

    try:
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            slot = db.query(Slot).filter(Slot.id == slot_id).first()
            if not slot:
                flash("Event not found", "error")
                return redirect(url_for("bp.events"))

            slot_start_time_aware = slot.start_time.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)

            if slot_start_time_aware <= now_utc:
                flash(
                    "Cannot book an event that has already started or finished.",
                    "error",
                )
                return redirect(url_for("bp.events"))

            result = system.book_slot(session["user"]["id"], slot_id)
            flash(result, "success" if "confirmed" in result.lower() else "error")
    except SQLAlchemyError as e:
        current_app.logger.error(f"Booking error: {e}")
        flash("An error occurred during booking.", "error")
    return redirect(url_for("bp.events"))


@bp.route("/cancel_booking/<int:slot_id>", methods=["POST"])
@login_required
def cancel_booking(slot_id):
    """
    Cancel a booking for a specific slot.

    Prevents cancellation if the event has already started or finished.
    """
    try:
        user_id = session["user"]["id"]
        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            slot = db.query(Slot).filter(Slot.id == slot_id).first()
            if not slot:
                flash("Event not found", "error")
                return redirect(url_for("bp.events"))

            slot_start_time_aware = slot.start_time.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)

            if slot_start_time_aware <= now_utc:
                flash(
                    "Cannot cancel a booking for an event that has already started or finished.",
                    "error",
                )
                return redirect(url_for("bp.events"))

            result = system.cancel_booking(user_id, slot_id)
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

                if not user_obj or not check_password_hash(
                    user_obj.password_hash, old_password
                ):
                    flash("Old password is incorrect.", "error")
                    return redirect(url_for("bp.change_password"))

                UserService(db, lock=False).change_user_password(user_id, new_password)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Change password error: {e}")
            flash("An unexpected error occurred while changing your password.", "error")
            return redirect(url_for("bp.change_password"))

        flash("Password changed successfully.", "success")
        return redirect(url_for("bp.events"))

    return render_template("user/change_password.html")
