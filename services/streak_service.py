"""
services/streak_service.py — Mixtape

Handles listening streak logic for users.
A streak increments when a user listens on consecutive calendar days.
It resets to 1 if a day is skipped.
"""

from datetime import datetime, timezone
from app import db
from models import User, ListeningEvent


def record_listening_event(user_id: str, song_id: str) -> ListeningEvent:
    """
    Record that a user listened to a song and update their streak.

    Args:
        user_id: The ID of the user who listened.
        song_id: The ID of the song that was listened to.

    Returns:
        The created ListeningEvent.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    now = datetime.now(timezone.utc)

    # Create the listening event
    event = ListeningEvent(user_id=user_id, song_id=song_id, listened_at=now)
    db.session.add(event)

    # Update the streak
    update_listening_streak(user, now)

    db.session.commit()
    return event


def update_listening_streak(user: User, now: datetime) -> None:
    today = now.date()

    if user.last_listened_at is None:
        user.listening_streak = 1
        user.last_listened_at = now
        return

    last_listened = user.last_listened_at
    if last_listened.tzinfo is None:
        last_listened = last_listened.replace(tzinfo=timezone.utc)

    last_date = last_listened.date()
    days_since_last = (today - last_date).days

    if days_since_last == 0:
        return

    elif days_since_last == 1:
        user.listening_streak += 1

    else:
        user.listening_streak = 1

    user.last_listened_at = now


def get_streak(user_id: str) -> int:
    """
    Get the current listening streak for a user.

    Args:
        user_id: The ID of the user.

    Returns:
        The user's current listening streak as an integer.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user.listening_streak
