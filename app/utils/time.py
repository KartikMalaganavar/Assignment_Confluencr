from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    IST = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:
    # Fallback for environments without tzdata installed.
    IST = timezone(timedelta(hours=5, minutes=30))


def istnow() -> datetime:
    return datetime.now(IST)


def utcnow() -> datetime:
    # Backward-compatible alias used across services/routes.
    return istnow()
