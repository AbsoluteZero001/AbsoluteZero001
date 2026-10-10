"""
Age calculation utility.

Read birth date from GitHub Actions Secrets.
Calculate age using Beijing time (UTC+08:00).

The actual birth date is never hardcoded or printed.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import os


# Beijing timezone
BEIJING_TZ = timezone(timedelta(hours=8))


def calculate_age(today: date | None = None) -> int:
    """Calculate completed years using Beijing local date."""

    birth_date_value = os.environ.get("BIRTH_DATE", "")

    if not birth_date_value:
        raise RuntimeError(
            "Missing BIRTH_DATE environment variable"
        )

    try:
        birthday = date.fromisoformat(birth_date_value)

        if birthday.isoformat() != birth_date_value:
            raise ValueError("Invalid date format")

    except ValueError:
        raise ValueError(
            "BIRTH_DATE must be a valid YYYY-MM-DD date"
        ) from None

    if today is None:
        today = datetime.now(BEIJING_TZ).date()

    if birthday > today:
        raise ValueError(
            "BIRTH_DATE cannot be in the future"
        )

    age = today.year - birthday.year

    if (today.month, today.day) < (
        birthday.month,
        birthday.day,
    ):
        age -= 1

    return age
