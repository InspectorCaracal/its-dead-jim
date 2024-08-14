"""
Settings file for testing
"""
import logging
import os

# Use the game defaults unless explicitly overridden
from .settings import *

#GLOBAL_SCRIPTS = {}

# Disable file-based logging.
logging.disable(logging.CRITICAL)

# Disable server debug mode.
DEBUG = False

# Use an isolated test database to avoid data leakage from the main one.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(GAME_DIR, "server", "test.db3"),
    }
}

# Use a simple and fast password hasher for testing.
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

# Disable Django's built-in logging.
LOGGING = {}