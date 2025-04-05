"""Authentication routes for handling user login, registration, and logout."""

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from ..utils import encrypt_data, is_email_valid, is_password_strong, is_rate_limited
from ..models import User
from .blueprint import bp


def redirect_if_logged_in():
    """Redirect the user based on their role if already logged in.

    Returns:
        Optional[Any]: A redirect response if the user is logged in, or None.
    """
    if "user" in session:
        user = session["user"]
        if user.get("role") == "Admin":
            return redirect(url_for("bp.admin"))
        return redirect(url_for("bp.events"))
    return None


@bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    """Handles user login with rate limiting.

    Returns:
        Any: The rendered login template for GET requests or a redirect response for POST.
    """
    redirect_response = redirect_if_logged_in()
    if redirect_response:
        return redirect_response

    if request.method == "GET":
        return render_template("authentication/login.html")

    return _handle_login_post()


def _handle_login_post():
    """Processes the POST request for user login and returns a redirect response."""
    try:
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("bp.login"))

        encrypted_email = encrypt_data(
            email.lower()
        )  # Ensure case-insensitive email match
        if is_rate_limited(encrypted_email):
            flash("Too many login attempts. Please try again later.", "error")
            return redirect(url_for("bp.login"))

        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            user = (
                db.query(User).filter(User.email_encrypted == encrypted_email).first()
            )
            if not user or not user.verify_password(password):
                flash("Invalid credentials", "error")
                return redirect(url_for("bp.login"))

            if user.blocked:
                flash("Your account is blocked.", "error")
                return redirect(url_for("bp.login"))

            session["user"] = {
                "id": user.id,
                "name": user.get_name(),
                "email": user.get_email(),
                "role": user.role,
                "admin_rank": user.admin_rank,
            }
            return redirect(
                url_for("bp.admin" if user.role == "Admin" else "bp.events")
            )
    except Exception as error:  # pylint: disable=broad-exception-caught
        current_app.logger.error("Login error: %s", error)
        flash("An error occurred during login.", "error")
        return redirect(url_for("bp.login"))


@bp.route("/register", methods=["GET", "POST"], endpoint="register")
def register():
    """Handles user registration with validation and rate limiting.

    Returns:
        Any: The rendered registration template for GET requests or a redirect response for POST.
    """
    redirect_response = redirect_if_logged_in()
    if redirect_response:
        return redirect_response

    if request.method == "GET":
        return render_template("authentication/register.html")

    # Delegate POST processing to a helper function.
    return _handle_register_post()


def _handle_register_post():  # pylint: disable=too-many-return-statements
    """Processes the POST request for user registration and returns a redirect response.

    Returns:
        Any: A redirect response based on the outcome of the registration process.
    """
    try:
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return redirect(url_for("bp.register"))

        encrypted_email = encrypt_data(email)
        if is_rate_limited(encrypted_email):
            flash("Too many registration attempts. Please try again later.", "error")
            return redirect(url_for("bp.register"))

        system = current_app.system  # type: ignore[attr-defined]
        with system as db:
            encrypted_name = encrypt_data(name)
            if db.query(User).filter(User.name_encrypted == encrypted_name).first():
                flash("Name already in use.", "error")
                return redirect(url_for("bp.register"))

        if not is_email_valid(email):
            flash("Invalid email format.", "error")
            return redirect(url_for("bp.register"))

        with system as db:
            if db.query(User).filter(User.email_encrypted == encrypted_email).first():
                flash("Email already registered.", "error")
                return redirect(url_for("bp.register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("bp.register"))

        if not is_password_strong(password):
            flash(
                "Password must be at least 8 characters long, contain uppercase, lowercase "
                "letters and at least one number.",
                "error",
            )
            return redirect(url_for("bp.register"))

        with system as db:
            user = system.create_user_account(name, email, password)

        session["user"] = {
            "id": user.id,
            "name": user.get_name(),
            "email": user.get_email(),
            "role": user.role,
            "admin_rank": user.admin_rank,
        }
        flash("Registration successful.", "success")
        return redirect(url_for("bp.events"))
    except Exception as error:  # pylint: disable=broad-exception-caught
        current_app.logger.error("Registration error: %s", error)
        flash("An error occurred during registration.", "error")
        return redirect(url_for("bp.register"))


@bp.route("/logout", endpoint="logout")
def logout():
    """Clears the user session and logs out the user.

    Returns:
        Any: A redirect response to the index page.
    """
    session.clear()
    return redirect(url_for("bp.index"))
