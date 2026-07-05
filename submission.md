
<img width="1266" height="348" alt="image" src="https://github.com/user-attachments/assets/81409d20-2605-42ef-b974-13dab25d7ece" />
# SUBMISSION.md

# Codebase Map – Mixtape

## Overview

Mixtape is a Flask application for sharing songs, creating collaborative playlists, tracking listening streaks, viewing friends' listening activity, and managing notifications.

The application follows a layered architecture:

Client → Flask Routes (Blueprints) → Service Layer → SQLAlchemy Models → SQLite Database

The routes handle HTTP requests and responses, while the service layer contains nearly all of the business logic. Models define the database schema and relationships used throughout the application.

---

# Required Features

## 3pts Codebase Map

### File Responsibility Map

#### app.py
- Entry point and Flask application factory
- Initializes Flask app and SQLAlchemy
- Loads configuration
- Registers Blueprints:
  - songs
  - playlists
  - users
  - feed
- Initializes database tables via db.create_all()

#### models.py
Defines all database schema and relationships.

User:
- username, email
- listening streak tracking
- last listening timestamp
- relationships: songs, ratings, playlists, notifications, friends

Song:
- title, artist, album, genre
- share metadata (user, timestamp, note)
- relationships: ratings, listening events, tags

ListeningEvent:
- records every user listen event
- drives streak + feed logic

Rating:
- one rating per user per song (unique constraint)

Playlist:
- collaborative playlists via association table

Notification:
- system events (ratings, playlist additions, etc.)

Tag:
- song categorization labels

#### Association Tables
- friendships: user-user many-to-many
- song_tags: song-tag many-to-many
- playlist_entries:
  - playlist-song relationship
  - includes position, added_by, timestamp

#### routes/

songs.py:
- search songs
- rate songs
- record listening events
- uses: search_service, streak_service, notification_service

playlists.py:
- create playlists
- add songs
- retrieve playlist content
- uses: playlist_service, notification_service

users.py:
- user profile endpoints
- streak + notifications retrieval
- uses: streak_service, notification_service

feed.py:
- activity feed
- friends listening now
- uses: feed_service

#### services/

streak_service.py:
- record_listening_event()
- update_listening_streak()
- get_streak()

search_service.py:
- search_songs()
- get_song()

playlist_service.py:
- create_playlist()
- get_playlist()
- get_playlist_songs()
- get_user_playlists()

notification_service.py:
- create_notification()
- add_to_playlist()
- rate_song()
- get_notifications()
- mark_as_read()

feed_service.py:
- get_friends_listening_now()
- get_activity_feed()

---

### Data Flow Example (Rating a Song)

POST /songs/<song_id>/rate
→ routes/songs.py
→ notification_service.rate_song()
→ Rating model
→ SQLite DB commit

Flow:
1. Client sends request
2. Route validates input
3. Service processes rating logic
4. Rating updated or created
5. Commit to database
6. Return JSON response

---

### Data Flow Example (Listening Event)

POST /songs/<song_id>/listen
→ routes/songs.py
→ record_listening_event()
→ update_listening_streak()
→ ListeningEvent + User update
→ Database commit

---

### Architecture Summary
- Blueprint-based routing (feature-separated)
- Service layer contains business logic
- SQLAlchemy ORM for persistence
- Shared model layer across services
- Event-driven side effects (streaks, notifications, feed updates)

---

# 4pts Bug Fix Completeness

---

## Issue #1 — Listening streak not updating after user activity

### Reproduction steps
GET user:
curl /users/<id>

Trigger rating:
curl POST /songs/<song_id>/rate

Re-check user:
curl /users/<id>

Observed:
- streak increased
- last_listened_at updated

### Navigation strategy
routes/songs.py → notification_service.rate_song() → streak_service.py

Confirmed streak update happens via shared pipeline.

### Root cause
No bug.

Streak updates indirectly through shared activity pipeline, not route-level logic.

### Fix
None required.

### Side effects
- Listening still updates streak
- Rating still works
- No duplicate updates

---

## Issue #5 — Last song in playlist missing

### Reproduction steps
GET /playlists/<id>/songs
→ last song missing

After POST add song → still missing

### Navigation strategy
routes/playlists.py → playlist_service.get_playlist_songs()

Found transformation after DB query.

### Root cause
playlist_service.py:
songs[:-1] removes last song unconditionally.

### Fix
Replace with:
songs[:]

### Side effects
- Full playlist returned
- Ordering preserved
- No insertion issues

---

## Issue #2 — Friends Listening Now shows stale users

### Reproduction steps
GET /feed
→ shows old activity

### Navigation strategy
routes/feed.py → feed_service.get_friends_listening_now()

Checked cutoff filtering logic.

### Root cause
Cutoff defined but not strictly enforced across query path.

### Fix
Enforce:
listened_at >= cutoff

Add deduplication per friend.

### Side effects
- Only recent users shown
- Feed ordering intact
- History unaffected

---

# 3pts Commit History

Git log screenshot included:

https://github.com/user-attachments/assets/81409d20-2605-42ef-b974-13dab25d7ece

- Multiple commits visible
- bugfix/mixtape branch used
- Conventional commit style (fix:)

---

# 3pts AI Usage

1. Used AI to trace service-layer execution paths across:
   - songs → notification_service → streak_service
2. Used AI to understand edge cases:
   - datetime cutoff behavior
   - playlist slicing bug implications
3. Verified AI outputs manually:
   - read code directly
   - re-ran curl requests
   - confirmed AI sometimes overgeneralized indirect flows

AI assisted understanding, not direct bug detection.
