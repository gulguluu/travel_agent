#!/usr/bin/env python3
"""
Date utilities for the travel agent.
Provides current date functionality.
"""

from datetime import datetime

from dateutil import parser as dateparser


def get_current_date():
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def infer_future_date(date_str):
    """
    Parses a date string and infers the correct future year. If the parsed date is
    in the past, it assumes the date is for the next year.
    """
    try:
        parsed_date = dateparser.parse(
            date_str,
            default=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        )
        today = datetime.now()
        year_was_specified = any(
            char.isdigit() and len(word) >= 2
            for word in date_str.split()
            for char in word
        ) and any(len(word) >= 2 for word in date_str.split())

        if parsed_date < today:
            if not year_was_specified:
                return parsed_date.replace(year=today.year + 1).strftime("%Y-%m-%d")
            return parsed_date.replace(year=parsed_date.year + 1).strftime("%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str
