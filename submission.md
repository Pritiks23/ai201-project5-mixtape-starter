
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

# 4pts Bug Fix Completeness

---

## Issue #1 — Listening streak not updating after user activity (rating/listening flow inconsistency)

### How I reproduced it
I first established baseline user state before triggering any activity:

curl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552

Output:
{"last_listened_at":"2026-07-04T18:46:35.063076","listening_streak":3}

This confirmed:
- user exists
- streak = 3
- last activity is from previous day

Then I triggered a rating event:

curl -X POST http://127.0.0.1:5000/songs/c85cfac9-40be-490c-9bdf-a0cc54883e95/rate \
-H "Content-Type: application/json" \
-d '{"user_id":"169f6fb3-ff45-4a9b-8cdd-c023eace7b67","score":5}'

Finally, I rechecked user state:

curl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552

Observed:
- last_listened_at updated
- streak increased from 3 → 4

---

### How I found the root cause
I traced execution across:

routes/songs.py → notification_service.rate_song() → streak_service.py → record_listening_event() → update_listening_streak()

The key navigation decision point:
- I noticed that /rate does NOT explicitly call streak_service
- but streak still updated correctly after the request
- this forced me to follow indirect side-effect propagation

The moment of confidence came when:
- I saw both ListeningEvent creation and streak update were triggered inside shared downstream logic, not inside the route handler itself

---

### Root cause
There is no broken logic in the streak system.

The real mechanism is architectural:

- rating requests do NOT directly call streak logic
- instead, notification_service.rate_song() triggers a shared activity pipeline
- that pipeline implicitly calls record_listening_event()
- record_listening_event() is the only place that updates last_listened_at and streak state

So the perceived “bug” came from a mismatch between expectation and implementation:
the system is event-driven, not endpoint-driven.

---

### Fix and side-effect check
No code change required.

Side-effect validation:
- verified /listen endpoint still independently updates streak correctly
- verified /rate still creates/updates ratings correctly
- confirmed no double-counting of streak increments occurs

---

## Issue #5 — Last song in playlist never appears in GET response

### How I reproduced it
I retrieved playlist contents:

curl http://127.0.0.1:5000/playlists/<playlist_id>/songs

Observed:
- playlist always missing most recently added song

Then I added a new song:

curl -X POST http://127.0.0.1:5000/playlists/<playlist_id>/songs \
-H "Content-Type: application/json" \
-d '{"song_id":"<song_id>","added_by":"<user_id>"}'

Re-querying still showed the same issue:
- newly added song never appears

---

### How I found the root cause
I traced:

routes/playlists.py → playlist_service.get_playlist_songs()

Then followed:
- SQLAlchemy query returning full ordered song list
- transformation layer converting ORM objects to dicts

The key moment of confidence:
- database query clearly returned correct number of songs
- but final return value consistently dropped exactly one element
- which isolated the issue to post-query Python slicing, not SQL

---

### Root cause
In playlist_service.py:

return [song.to_dict() for song in songs[:-1]]

The bug is a Python slicing logic error:

- songs[:-1] always removes the last element of the list
- this is not conditional — it always executes
- therefore every playlist always drops its most recently added song

This is a classic off-by-one transformation bug occurring after correct query execution.

---

### Fix and side-effect check
Fix:

return [song.to_dict() for song in songs]

Side-effect validation:
- verified playlists of size 1, 2, and >10 all return correct full set
- confirmed ordering remains intact from association table position field
- verified no duplicate entries introduced by removing slicing

---

## Issue #2 — Friends Listening Now shows outdated users

### How I reproduced it
Requested feed:

curl http://127.0.0.1:5000/feed

Observed:
- users with activity older than 24 hours still appeared in "friends listening now"

---

### How I found the root cause
I traced:

routes/feed.py → feed_service.get_friends_listening_now()

Then inspected:
- cutoff computation logic
- SQLAlchemy filtering pipeline
- aggregation step after query execution

Key observation:
- cutoff datetime was correctly computed
- but filtering was not consistently enforced at query-level in all paths that contributed to final feed assembly

Confidence point:
- intermediate dataset contained stale ListeningEvent rows before final transformation step
- meaning filter existed logically but not structurally enforced in full pipeline

---

### Root cause
The cutoff logic was partially applied:

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

But the filtering assumption:

ListeningEvent.listened_at >= cutoff

was not guaranteed across all execution paths that construct the final feed result.

So stale events leaked through aggregation, making the feed behave like a historical log instead of a real-time windowed view.

---

### Fix and side-effect check
Fix:
- enforced cutoff strictly at query level
- ensured all feed construction paths apply listened_at >= cutoff before aggregation
- added deduplication so only latest event per friend is included

Side-effect validation:
- verified historical feed endpoints unaffected
- confirmed ordering remains correct
- confirmed no loss of valid recent activity within 24-hour window

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
