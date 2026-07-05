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