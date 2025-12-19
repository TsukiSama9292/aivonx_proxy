"""
Account models removed — using Django's built-in auth.User.

This file intentionally left minimal so the project uses
`django.contrib.auth`'s `User` model. If you need a profile
model later, add a `Profile` model with a OneToOneField to
`settings.AUTH_USER_MODEL`.
"""

from django.conf import settings
from django.db import models

# Placeholder for future account-related models (e.g., Profile)
