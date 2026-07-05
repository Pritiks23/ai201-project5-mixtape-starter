# Codebase Map – Mixtape

## Overview

Mixtape is a Flask application for sharing songs, creating collaborative playlists, tracking listening streaks, viewing friends' listening activity, and managing notifications.

The application follows a layered architecture:

```
Client
   ↓
Flask Routes (Blueprints)
   ↓
Service Layer
   ↓
SQLAlchemy Models
   ↓
SQLite Database
```

The routes handle HTTP requests and responses, while the service layer contains nearly all of the business logic. Models define the database schema and relationships used throughout the application.

---

# AI Usage Section

I used AI primarily as a debugging and code comprehension aid during Milestone 3, especially when tracing execution paths across services and understanding how different components (routes, service layers, and database models) interacted. I asked it to explain specific functions after I had already identified them in the codebase, such as playlist handling logic, feed generation, streak updates, and notification triggers, and to help clarify edge cases in datetime handling and query filtering behavior. It was particularly useful for reasoning about subtle issues like off-by-one slicing errors, time-window filtering logic, and differences in how “recent activity” should be interpreted versus how it was implemented. However, I did not rely on it to locate bugs directly; in several cases I had already reproduced the issue via curl and then used AI to help interpret the relevant function once I had found it manually. I also verified all suggested fixes by reading the surrounding code and re-running endpoints to confirm behavior changes, since AI explanations were occasionally too broad or would assume missing context about the data model or service flow.
# Main Files

## app.py

The application's entry point and Flask application factory.

Responsibilities:

- Creates the Flask app
- Configures SQLAlchemy
- Loads application configuration
- Registers the four Blueprints:
  - songs
  - playlists
  - users
  - feed
- Creates database tables with `db.create_all()`

---

## models.py

Defines every SQLAlchemy model and the relationships between them.

### User

Stores:

- username
- email
- current listening streak
- last listening timestamp

Relationships:

- shared songs
- ratings
- listening events
- playlists
- notifications
- friends

---

### Song

Represents a song shared by a user.

Stores:

- title
- artist
- album
- genre
- who shared it
- share timestamp
- optional share note

Relationships:

- ratings
- listening events
- tags

---

### ListeningEvent

Represents a single listening event.

Each time a user listens to a song, a ListeningEvent record is created. These records are used by both the listening streak feature and the activity feed.

---

### Rating

Stores a user's rating for a song.

A database unique constraint ensures a user can only have one rating per song.

---

### Playlist

Represents a collaborative playlist.

Playlists contain songs through the `playlist_entries` association table.

---

### Notification

Stores notifications sent to users.

Examples include notifications when someone adds a shared song to a playlist or rates a song.

---

### Tag

Represents tags attached to songs.

---

## Association Tables

### friendships

Many-to-many relationship between users.

---

### song_tags

Many-to-many relationship between songs and tags.

---

### playlist_entries

Join table between playlists and songs.

Unlike a simple join table, it also stores:

- song position
- who added the song
- when it was added

This allows playlists to preserve song ordering.

---

# Routes

The application is organized into four Blueprint modules.

## routes/songs.py

Handles:

- searching songs
- retrieving song details
- rating songs
- recording listening events

Uses:

- search_service
- notification_service
- streak_service

---

## routes/playlists.py

Handles:

- creating playlists
- retrieving playlists
- retrieving playlist songs
- adding songs to playlists

Uses:

- playlist_service
- notification_service

---

## routes/users.py

Handles:

- retrieving user information
- retrieving listening streaks
- retrieving notifications
- marking notifications as read

Uses:

- streak_service
- notification_service

---

## routes/feed.py

Handles:

- Friends Listening Now
- Activity Feed

Uses:

- feed_service

---

# Services

## streak_service.py

Responsible for listening history and streak management.

Main functions:

- `record_listening_event()`
  - Creates a ListeningEvent
  - Updates the user's listening streak
  - Commits both changes

- `update_listening_streak()`
  - Determines whether the streak should:
    - start at 1
    - stay the same
    - increment
    - reset

- `get_streak()`
  - Returns the user's current listening streak.

---

## search_service.py

Responsible for song lookup.

Main functions:

- `search_songs()`
  - Searches song titles and artists using a case-insensitive search.
  - Returns matching songs as dictionaries.

- `get_song()`
  - Retrieves a single song by ID.

---

## playlist_service.py

Responsible for playlist creation and retrieval.

Main functions:

- `create_playlist()`
- `get_playlist()`
- `get_playlist_songs()`
- `get_user_playlists()`

`get_playlist_songs()` queries songs through the `playlist_entries` table and orders them using the playlist position column.

---

## notification_service.py

Responsible for notification creation and song rating.

Main functions:

- `create_notification()`
- `add_to_playlist()`
- `rate_song()`
- `get_notifications()`
- `mark_as_read()`

`add_to_playlist()` both updates the playlist and creates a notification for the original song sharer if someone else adds their song.

`rate_song()` creates or updates a Rating record for a song.

---

## feed_service.py

Responsible for the social feed.

Main functions:

- `get_friends_listening_now()`
- `get_activity_feed()`

`get_friends_listening_now()` returns only recent listening events (within the configured threshold) and only the newest event for each friend.

`get_activity_feed()` returns the most recent listening events from friends without filtering by recency.

---

# Data Flow Example

## User Rates a Song

```
POST /songs/<song_id>/rate
        ↓
routes/songs.py
        ↓
notification_service.rate_song()
        ↓
Rating model
        ↓
Database
```

Flow:

1. The client submits a POST request containing a user ID and rating.
2. `routes/songs.py` validates the request data.
3. The route calls `notification_service.rate_song()`.
4. The service validates the score and verifies both the user and song exist.
5. If the user has already rated the song, the existing Rating is updated.
6. Otherwise, a new Rating object is created.
7. The transaction is committed.
8. The updated Rating is returned as JSON.

---

## User Records a Listening Event

```
POST /songs/<song_id>/listen
        ↓
routes/songs.py
        ↓
record_listening_event()
        ↓
update_listening_streak()
        ↓
ListeningEvent + User
        ↓
Database
```

Flow:

1. The client sends a listening request.
2. The route calls `record_listening_event()`.
3. A ListeningEvent record is created.
4. `update_listening_streak()` updates the user's streak based on the previous listening date.
5. Both changes are committed together.

---

# Organization Patterns

Several patterns appear consistently throughout the project.

- **Blueprint-based routing:** Routes are grouped by feature (songs, playlists, users, feed).
- **Service layer:** Routes delegate almost all business logic to service modules.
- **ORM-based database access:** All persistence uses SQLAlchemy models and relationships.
- **Feature-based organization:** Each feature has a corresponding route file and service file.
- **Shared model layer:** Multiple services reuse the same models (User, Song, Rating, Playlist, ListeningEvent, Notification) instead of duplicating logic.

---

# Open Issues

The README identifies five bugs, all located in the service layer:

1. Listening streak resets unexpectedly (`streak_service.py`)
2. Friends Listening Now includes outdated activity (`feed_service.py`)
3. Duplicate songs appear in search (`search_service.py`)
4. Song ratings do not generate notifications (`notification_service.py`)
5. The final song in a playlist is missing (`playlist_service.py`)

Since every reported issue originates in a service module, debugging should begin by tracing the corresponding route into its service implementation before making changes.


# Issue #1 — Listening streak not updating after user activity (rating/listening flow inconsistency)

How I reproduced it  
I first established the baseline state of the user before triggering any activity:

curl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552

Output:
{"id":"169f6fb3-d3f2-474b-b696-5fdea12ae552","last_listened_at":"2026-07-04T18:46:35.063076","listening_streak":3,"username":"darius"}

This confirmed:
User exists
Current streak = 3
Last activity recorded on 2026-07-04

Then I triggered a user interaction via rating:

curl -X POST http://127.0.0.1:5000/songs/c85cfac9-40be-490c-9bdf-a0cc54883e95/rate \
-H "Content-Type: application/json" \
-d '{"user_id":"169f6fb3-ff45-4a9b-8cdd-c023eace7b67","score":5}'

Output:
{"id":"6062229b-ff45-4a9b-8cdd-c023eace7b67","rated_at":"2026-07-05T20:07:12.064068","score":5,"song_id":"c85cfac9-40be-490c-9bdf-a0cc54883e95","user_id":"169f6fb3-ff45-4a9b-8cdd-c023eace7b67"}

Finally, I rechecked user state:

curl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552

Output:
{"id":"169f6fb3-d3f2-474b-b696-5fdea12ae552","last_listened_at":"2026-07-05T20:24:06.877445","listening_streak":4,"username":"darius"}

This showed:
last_listened_at updated
listening_streak incremented (3 → 4)

How I found the root cause  
I traced execution through routes/songs.py, services/notification_service.py (rate_song function), services/streak_service.py (record_listening_event + update_listening_streak), and models.User fields.

The key observation was that the /rate endpoint does not directly update streak state, but streak still updates due to a shared downstream activity pipeline. This means rating and listening activity converge through shared logic rather than independent flows.

Root cause  
There is no missing or broken streak logic. The issue was a misinterpretation of system behavior.

Specifically:
- /rate triggers shared user activity pipeline
- that pipeline already invokes streak update logic indirectly
- so streak updates occur correctly, but not via direct route-level logic

---

# Issue #5 — Last song in playlist never shows up

How you reproduced it  
curl http://127.0.0.1:5000/playlists/<playlist_id>/songs

Observed:
count did not include last song
most recently added song was missing

Even after adding songs:

curl -X POST http://127.0.0.1:5000/playlists/<playlist_id>/songs \
-H "Content-Type: application/json" \
-d '{"song_id":"<song_id>","added_by":"<user_id>"}'

The last inserted song never appeared in GET response.

Root cause analysis  
In services/playlist_service.py:

return [song.to_dict() for song in songs[:-1]]

Root cause:
songs[:-1] always removes the last element

Fix:
return [song.to_dict() for song in songs]

Side-effects:
playlist now returns full list
ordering preserved
no regression in insertion logic

---

# Issue #2 — Friends Listening Now shows people from yesterday

How you reproduced it  
curl http://127.0.0.1:5000/feed

Observed:
stale users (older than 24h) appeared in feed

Root cause analysis  
In services/feed_service.py:

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
ListeningEvent.listened_at >= cutoff

Issue:
cutoff existed but was not consistently enforced at query level in all execution paths, causing feed to behave like a historical stream instead of a real-time snapshot.

Fix:
Strict enforcement of:
ListeningEvent.listened_at >= cutoff

Ensured deduplication per friend using most recent event only.

Side-effects:
Only recent users appear
Ordering remains correct
Historical endpoints unaffected

---


