"""
Utility module providing encryption, rate limiting, and caching functionalities.

This module loads environment variables, configures logging, manages AES encryption
keys, and supplies helper functions for encrypting/decrypting data, rate limiting,
and caching results.
"""

import os
import base64
import secrets
import logging
import re
from time import time
from collections import defaultdict
from functools import wraps
from threading import Lock
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    TypeVar,
    Tuple,
    cast,
)

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv, set_key

ENV_FILE = ".env"
load_dotenv(ENV_FILE)

RATE_LIMIT_SECONDS = 20
MAX_REQUESTS = 10
_rate_limit_store: DefaultDict[int, List[float]] = defaultdict(list)
_RATE_LIMIT_LOCK = Lock()

EMAIL_REGEX = re.compile(r"^[\w\-\.]+@([\w-]+\.)+[\w-]{2,}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9]).{8,30}$")


def setup_logging():
    """
    Configure and return a logger instance using environment settings.

    Environment Variables:
        LOGGING_LEVEL (str): Logging verbosity level. Defaults to 'INFO'.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_level = os.getenv("LOGGING_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def get_or_generate_env_key(key_name, length, is_base64=False):
    """
    Retrieve an environment key. If not found, generate and persist a new key.

    Args:
        key_name (str): The name of the environment variable.
        length (int): Length in bytes of the key to generate if missing.
        is_base64 (bool, optional): If True, key is base64 encoded; otherwise hex.

    Returns:
        str: The retrieved or generated key as a string.
    """
    key = os.getenv(key_name)
    if not key:
        raw_key = secrets.token_bytes(length)
        key = base64.b64encode(raw_key).decode("utf-8") if is_base64 else raw_key.hex()
        set_key(ENV_FILE, key_name, key)
        logger.warning(
            "%s not found in environment. Generated a new key and updated .env.",
            key_name,
        )
    return key


def get_secret_key():
    """
    Retrieve Flask's SECRET_KEY from environment or generate one if missing.

    Returns:
        str: The Flask SECRET_KEY.
    """
    return get_or_generate_env_key("SECRET_KEY", 32)


def get_encryption_keys():
    """
    Retrieve AES encryption key and IV from environment variables.

    Returns:
        Tuple[bytes, bytes]: AES key (32 bytes) and initialization vector (16 bytes).
    """
    secret_key = get_or_generate_env_key("AES_SECRET_KEY", 32, is_base64=True)
    iv = get_or_generate_env_key("AES_IV", 16, is_base64=True)
    return base64.b64decode(secret_key), base64.b64decode(iv)


def get_env_value(key_name, default=None):
    """
    Retrieve an environment variable or return a default value.

    Args:
        key_name (str): The environment variable name.
        default (Optional[str]): Fallback value if key is not found.

    Returns:
        str: The retrieved or default value as a string.
    """
    value = os.getenv(key_name, default)
    if value is None and default is not None:
        return str(default)
    return value


AES_SECRET_KEY, AES_IV = get_encryption_keys()


def encrypt_data(data):
    """
    Encrypt plaintext using AES encryption (CBC mode, PKCS#7 padding).

    Args:
        data (str): Plaintext to encrypt.

    Returns:
        str: Base64-encoded encrypted data.
    """
    cipher = Cipher(
        algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=default_backend()
    )
    encryptor = cipher.encryptor()
    pad_length = 16 - (len(data.encode()) % 16)
    padded_data = data.encode() + bytes([pad_length] * pad_length)
    encrypted_bytes = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(encrypted_bytes).decode()


def decrypt_data(encrypted_data):
    """
    Decrypt AES CBC mode encrypted data.

    Args:
        encrypted_data (str): Base64-encoded ciphertext.

    Returns:
        str: Decrypted plaintext.
    """
    cipher = Cipher(
        algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted_bytes = (
        decryptor.update(base64.b64decode(encrypted_data)) + decryptor.finalize()
    )
    return decrypted_bytes[: -decrypted_bytes[-1]].decode()


def is_rate_limited(user_id):
    """
    Determine if a user has exceeded the request rate limit.

    Args:
        user_id (int): Unique identifier for the user.

    Returns:
        bool: True if rate limit exceeded, else False.
    """
    current_time = time()
    with _RATE_LIMIT_LOCK:
        _rate_limit_store[user_id] = [
            t
            for t in _rate_limit_store[user_id]
            if current_time - t < RATE_LIMIT_SECONDS
        ]
        if len(_rate_limit_store[user_id]) >= MAX_REQUESTS:
            return True
        _rate_limit_store[user_id].append(current_time)
    return False


F = TypeVar("F", bound=Callable[..., Any])


def ttl_cache(ttl):
    """
    Decorator for caching function results for a specified TTL (in hours).

    Args:
        ttl (int): Time-to-live for the cache in hours.

    Returns:
        Callable: Decorated function with caching behavior.
    """
    cache: Dict[Tuple[Any, Tuple[Tuple[str, Any], ...]], Tuple[Any, float]] = {}
    cache_lock: Lock = Lock()

    def decorator(func: F):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(kwargs.items()))
            current_time = time()
            with cache_lock:
                if key in cache and current_time - cache[key][1] < ttl * 3600:
                    return cache[key][0]
                result = func(*args, **kwargs)
                cache[key] = (result, current_time)
                return result

        return cast(F, wrapper)

    return decorator


def is_email_valid(email):
    """
    Validate the format of an email address.

    Args:
        email (str): The email string to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    return bool(EMAIL_REGEX.match(email))


def is_password_strong(password):
    """
    Validate password strength.

    Criteria:
    - At least one uppercase letter.
    - At least one lowercase letter.
    - At least one number.
    - Length between 8 and 30 characters.

    Args:
        password (str): Password to validate.

    Returns:
        bool: True if password is strong, False otherwise.
    """
    return bool(PASSWORD_REGEX.match(password))
