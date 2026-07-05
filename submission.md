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


# Milestone 3 Reproducibility Issue #4 — Notifications not created when a song is ratedHow I reproduced itI first identified a valid song_id from the search endpoint and used a different user than the song owner.Step 1 — Rate a song (successful request)curl -X POST http://127.0.0.1:5000/songs/c85cfac9-40be-490c-9bdf-a0cc54883e95/rate \
-H "Content-Type: application/json" \
-d '{"user_id":"f686f779-8d31-46d4-b420-86c3b0c4603a","score":5}'Output:{"id":"c4ce7b68-14e9-419b-95dd-d8500e899f2b","rated_at":"2026-07-05T19:31:59.642523","score":5,"song_id":"c85cfac9-40be-490c-9bdf-a0cc54883e95","user_id":"f686f779-8d31-46d4-b420-86c3b0c4603a"}This confirms:Rating was successfully createdNo errors occurred in the request flowStep 2 — Check notifications for the song ownercurl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552/notificationsOutput:{"count":0,"notifications":[]}What this provesThe rating action completes successfully and persists the rating in the database, but no notification is generated for the song owner.This confirms a missing notification trigger in the rating workflow, since other interaction flows (like playlist additions) successfully generate notifications for song owners.Why this reproduction is validThe rating endpoint works correctly (returns created Rating)The song owner exists and is reachable via /users/<id>Notification system works in other flows (playlist additions)Only rating → notification path is missing

# Issue #5 — Song not added to playlist (500 Internal Server Error on playlist song addition)How I reproduced itI first created and verified a valid playlist, then attempted to add existing songs to that playlist using valid song IDs and a valid user ID.Step 1 — Verify playlist exists and is initially emptycurl http://127.0.0.1:5000/playlists/d0afebda-3b1c-4ef2-be42-69b81782bdb0/songsOutput:{"count":0,"songs":[]}This confirms:Playlist existsNo songs have been added yetEndpoint is reachable and functioningStep 2 — Attempt to add first song to playlist (fails with 500 error)curl -X POST http://127.0.0.1:5000/playlists/d0afebda-3b1c-4ef2-be42-69b81782bdb0/songs \
-H "Content-Type: application/json" \
-d '{"song_id":"7c9ae4b2-ffbb-4613-93dc-325473e0b433","added_by":"169f6fb3-d3f2-474b-b696-5fdea12ae552"}'Output:<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>Step 3 — Attempt to add second valid song (same failure behavior)curl -X POST http://127.0.0.1:5000/playlists/d0afebda-3b1c-4ef2-be42-69b81782bdb0/songs \
-H "Content-Type: application/json" \
-d '{"song_id":"56573c3a-f506-4626-87cb-1343f633b066","added_by":"169f6fb3-d3f2-474b-b696-5fdea12ae552"}'Output:<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>What this provesPlaylist endpoint is functional and accessibleValid song IDs exist in the systemValid user ID is provided in requestsHowever, every attempt to add a song to a playlist results in a 500 Internal Server ErrorThis confirms a backend failure in the playlist song addition workflow, likely inside the service layer (playlist_service.py or notification integration logic).Why this reproduction is validPlaylist retrieval works correctly (GET /playlists/<id>/songs)Song and user IDs are valid and verified via other endpointsFailure occurs consistently across multiple valid inputsIssue is isolated specifically to playlist song insertion logic, not input validation or missing data

# Issue #1 — Listening streak does not update after user activityHow I reproduced itI first retrieved a valid user to establish their current listening streak and last activity timestamp. I then triggered a new user activity by rating a song using the same user ID, and finally re-fetched the user to check whether the streak or last_listened_at values had changed.Step 1 — Check current user streak baselinecurl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552Output:{"id":"169f6fb3-d3f2-474b-b696-5fdea12ae552","last_listened_at":"2026-07-04T18:46:35.063076","listening_streak":3,"username":"darius"}This confirms:User exists and is validListening streak is currently 3last_listened_at is in the past, meaning streak logic should be evaluableStep 2 — Trigger a user activity (rate a song)curl -X POST http://127.0.0.1:5000/songs/c85cfac9-40be-490c-9bdf-a0cc54883e95/rate \
-H "Content-Type: application/json" \
-d '{"user_id":"169f6fb3-d3f2-474b-b696-5fdea12ae552","score":5}'Output:{"id":"6062229b-ff45-4a9b-8cdd-c023eace7b67","rated_at":"2026-07-05T20:07:12.064068","score":5,"song_id":"c85cfac9-40be-490c-9bdf-a0cc54883e95","user_id":"169f6fb3-d3f2-474b-b696-5fdea12ae552"}This confirms:Rating request succeedsUser activity is recorded correctly via rated_atStep 3 — Re-check user streak after activitycurl http://127.0.0.1:5000/users/169f6fb3-d3f2-474b-b696-5fdea12ae552Output:{"id":"169f6fb3-d3f2-474b-b696-5fdea12ae552","last_listened_at":"2026-07-04T18:46:35.063076","listening_streak":3,"username":"darius"}What this provesThe listening streak does not update after a valid user activity (song rating). Although the rating request succeeds and creates a valid record, the user’s last_listened_at and listening_streak remain unchanged when re-fetching the user profile.This confirms that the streak update logic is not being triggered or persisted during the rating workflow.Why this reproduction is validUser state is consistent before the testA valid activity is successfully executedNo change occurs in user streak data afterwardThe issue is reproducible and independent of input variation