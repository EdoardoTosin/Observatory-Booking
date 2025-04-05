"""
User Service Module

This module provides the UserService class for handling user-related operations,
including:

- Account creation
- Input validation
- Password management

It ensures validation and secure interactions with the database.
"""

from sqlalchemy.exc import SQLAlchemyError

from ..utils import logger, is_email_valid, is_password_strong, encrypt_data
from ..models import User


class UserService:
    """
    Service class for user-related operations such as:
    - Creating user accounts
    - Validating user input
    - Updating user passwords
    """

    def __init__(self, db_session, lock):
        """
        Initialize the UserService.

        Args:
            db_session (Callable[[], Session]): A callable returning a new database session.
            lock (Any): A lock object to ensure thread-safe operations.
        """
        self.db_session = db_session
        self.lock = lock

    @staticmethod
    def validate_input(value, expected_type: type):
        """
        Validate that the input value is of the expected type.

        Args:
            value (Any): The data to validate.
            expected_type (type): The expected data type.

        Returns:
            Any: The validated data.

        Raises:
            ValueError: If the data type is incorrect.
        """
        if not isinstance(value, expected_type):
            raise ValueError(
                f"Invalid input type. Expected {expected_type}, got {type(value)}"
            )
        return value

    def create_user_account(self, name, email, password):
        """
        Create a new user account.

        Ensures:
        - Name is valid
        - Email follows proper format
        - Password meets security requirements

        Args:
            name (str): The user's full name.
            email (str): The user's email address.
            password (str): The user's password.

        Returns:
            User: The created user object.

        Raises:
            SQLAlchemyError: If any error occurs during account creation.
            ValueError: If validation fails.
        """
        with self.lock:
            session = self.db_session()
            try:
                name = self.validate_input(name, str)
                email = self.validate_input(email, str)
                password = self.validate_input(password, str)

                if not is_email_valid(email):
                    raise ValueError("Invalid email format.")
                if not is_password_strong(password):
                    raise ValueError("Password does not meet security requirements.")

                encrypted_email = encrypt_data(email)

                if (
                    session.query(User)
                    .filter_by(email_encrypted=encrypted_email)
                    .first()
                ):
                    raise ValueError("Email already registered.")

                user = User(name=name, email=email, password=password)
                session.add(user)
                session.commit()
                session.refresh(user)

                logger.info("User account created successfully for email: %s", email)
                return user
            except (SQLAlchemyError, ValueError) as e:
                session.rollback()
                logger.error("Error creating user account for %s: %s", email, e)
                raise
            finally:
                session.close()

    def change_user_password(self, user_id, new_password):
        """
        Change a user's password.

        Args:
            user_id (int): The user's ID.
            new_password (str): The new password.

        Returns:
            str: A message indicating the result of the operation.

        Raises:
            ValueError: If validation fails.
            SQLAlchemyError: If any error occurs during password update.
        """
        with self.lock:
            session = self.db_session()
            try:
                if not is_password_strong(new_password):
                    raise ValueError("Password does not meet security requirements.")

                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error("User %s not found.", user_id)
                    raise ValueError("User not found.")

                user.set_password(new_password)
                session.commit()

                logger.info("Password changed successfully for user %s.", user_id)
                return "Password updated successfully."
            except (SQLAlchemyError, ValueError) as e:
                session.rollback()
                logger.error("Error updating password for user %s: %s", user_id, e)
                raise
            finally:
                session.close()
