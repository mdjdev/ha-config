# PlayBee — NFC-Based Music Player for Kids

## Overview

PlayBee is a custom **NFC-tag-driven music player** for children, built on top of Home Assistant and [Music Assistant](https://music-assistant.io/). Physical NFC cards are each linked to a playlist; tapping a card on a reader starts playback, and removing it stops and saves the position for next time. A Zigbee rotary dial provides physical volume and track-skip controls.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Home Assistant                           │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  NFC Readers   │  │  PlayBee Scripts │  │ Automations  │ │
│  │  (ESPHome)     │─▶│  & Jinja Helpers │─▶│              │ │
│  └────────────────┘  └────────┬─────────┘  └──────┬───────┘ │
│                               │                    │         │
│                ┌──────────────▼──────────────┐     │         │
│                │     playbee.db (SQLite)      │     │         │
│                │  - Tag UID → playlist config │     │         │
│                │  - Resume state per tag      │     │         │
│                └─────────────────────────────┘     │         │
│                                                    │         │
│                ┌──────────────────────────────────▼────────┐ │
│                │          Music Assistant API              │ │
│                │          (REST over HTTP)                 │ │
│                └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         ▲                                        │
         │ NFC tap events            ┌────────────▼──────────┐
         │                           │  media_player          │
  ┌──────┴──────┐                    │  .playbee_speaker      │
  │ ESP8266     │                    │  (Music Assistant)     │
  │ + PN532 NFC │                    └───────────────────────┘
  │ (x2 units)  │
  └─────────────┘                    ┌───────────────────────┐
                                    │ Zigbee Dial Remote    │
                                    │ (volume + track ctrl) │
                                    └───────────────────────┘
```

---

## 1. Hardware — NFC Tag Readers

Two ESPHome-based NFC readers, each built on a **Wemos D1 Mini (ESP8266)** with a **PN532 NFC module** (SPI).

| Reader | Configuration File | HA Device ID |
|--------|--------------------|--------------|
| PlayBee TagReader v1 | `esphome/playbee-tagreader.yaml` | `5027c31bfe14b567944562578ee195bd` |
| PlayBee TagReader v2 | `esphome/playbee-tagreader-v2.yaml` | `b9cdc2845d361b7c7ef05d864ad713a1` |

**Behavior:**
- **Tag placed** → fires `tag_scanned` event with the tag UID; publishes UID to a `text_sensor`.
- **Tag removed** → sets `binary_sensor.<reader>_card_present` to `OFF`.

---

## 2. Database — `playbee.db`

Managed by `scripts/playbee_db.py`. A SQLite database with a single `tags` table.

### Table: `tags`

| Column | Type | Description |
|--------|------|-------------|
| `tag_uid` | `TEXT PK` | NFC tag identifier (e.g. `04-0D-C2-EA-40-59-80`) |
| `name` | `TEXT` | Human label used as playlist name prefix (`PlayBee - <name>` / `Dev - <name>`) |
| `media_url` | `TEXT` | Music Assistant media URI (e.g. `deezer://playlist/...`) |
| `shuffle_mode` | `TEXT` | `on` / `off` |
| `repeat_mode` | `TEXT` | `off` / `one` / `all` |
| `resume_mode` | `TEXT` | TTL string (`off`, `12h`, `24h`, `7d`, `365d`) |
| `resume_data` | `TEXT` | JSON: `{last_updated, title, track_id, position, queue_id}` |

### Exposed Shell Commands

| Command | Purpose |
|---------|---------|
| `playbee_db_init` | Create the `tags` table |
| `playbee_db_get_tag_by_id <uid>` | Lookup tag config by UID |
| `playbee_db_get_tag_by_name <name>` | Lookup tag by playlist name (name is base64-encoded in the shell_command template) |
| `playbee_db_save_resume <uid> <queue_id> <track_id> <position> <title>` | Persist playback state (title is base64-encoded in the shell_command template) |
| `playbee_db_clear_resume <uid>` | Clear saved resume data |
| `playbee_export_json` | Export all tables to JSON (hourly, 14-day retention) |

> **Free-text argument encoding:** the `playbee_db_get_tag_by_name` and `playbee_db_save_resume`
> shell_command templates base64-encode the untrusted free-text fields (`name`/`tag_name`,
> `title`) before they reach the Python script, because HA's `shell_command` runs the rendered
> command through `shlex.split` — an embedded double quote in a title/playlist name would split
> into extra argv tokens and exit 1. Callers pass the plain value as service data; the template
> does the encoding, so script `service_data` stays human-readable in traces. The script decodes
> (`base64.b64decode`) before use. `uid`/`queue_id`/`track_id`/`position` are passed as plain
> quoted args.

---

## 3. Core Scripts

All defined in `scripts.yaml`.

### `playbee_play_media_based_on_nfc_tag`

1. Look up the scanned tag UID in the database.
2. Normalize playback settings (shuffle, repeat) and resume context via Jinja templates.
3. Validate the tag exists and has a `media_url`.
4. Clear the current queue, apply shuffle/repeat.
5. Start playback via `music_assistant.play_media` (with `enqueue: replace`).
6. Mark the tag as active in `input_text.playbee_active_tag_uid`.
7. If valid resume data exists within its TTL:
   - Look up the track in the MA queue via `playbee_queue.py`.
   - Seek to the saved position via the MA REST API (`rest_command.playbee_ma_resume`).

### `playbee_stop_media`

1. Save resume state for the current tag.
2. Stop playback and clear the queue.
3. Clear the active tag marker.

### `playbee_save_resume`

- **Triggered on pause** and **every 30 s during playback** (heartbeat).
- Queries MA's active queue via REST.
- Extracts current track URI, queue ID, elapsed position.
- Validates it's a PlayBee-managed playlist (prefix check).
- Resolves playlist name → tag UID → persists resume data.

### `playbee_volume_change`

Accepts a signed delta (`+0.04`, `-0.02`), clamps between `0.05` and the configured max volume (`input_number.playbee_speaker_max_volume`), and applies it.

### `playbee_track_navigation`

Handles `restart_current`, `previous_track`, and `next_track` via standard `media_player` services.

---

## 4. Jinja Template Helpers

Located in `custom_templates/playbee.jinja` and `custom_templates/playbee_fn.jinja`.

| Function | Purpose |
|----------|---------|
| `normalize_on_off(value)` | Returns `"on"` or `"off"` from various truthy/falsy inputs |
| `normalize_repeat_mode(value)` | Maps to `off` / `one` / `all` |
| `normalize_resume_mode(value)` | Parses TTL strings (`24h` → `24h`; invalid → `off`) |
| `fn_is_known_value(value, returns)` | Returns whether value is non-empty, non-unknown |
| `fn_ttl_seconds_from_resume_mode(value, returns)` | Converts `12h` → `43200` seconds |
| `fn_resume_payload_is_valid(payload, returns)` | Validates resume JSON has required `track_id` and `queue_id` |

---

## 5. Automations

All defined in `automations.yaml`.

| Automation | Trigger | Behavior |
|------------|---------|----------|
| **NFC event router** | `tag_scanned` from either reader, or `card_present → off` | Scans → `playbee_play_media...`; removal → `playbee_stop_media`. Guards against starting a new tag while another is active. |
| **Save resume on pause** | `media_player.playbee_speaker → paused` | Persists resume data immediately. |
| **Save resume heartbeat** | Every 30 s while `state == playing` | Periodic resume save (≤30 s of potential data loss). |
| **Volume control** | Zigbee dial rotate (6 gesture levels) | Maps rotation to volume delta → calls `playbee_volume_change`. |
| **Track nav (prev)** | Zigbee button 1 press | Single press → restart current track; double press (within 1 s) → previous track. |
| **Track nav (next)** | Zigbee button 2 press | Next track. |
| **Enforce max volume** | Volume crosses threshold | Clamps to `input_number.playbee_speaker_max_volume`. |
| **Database backup** | Hourly (10:00–23:00) | Runs `playbee_export_json`. |
| **Clear stale active tag** | Card removed for 2 s **or** player idle for 2 s | Clears `input_text.playbee_active_tag_uid` to unblock new tags. |

---

## 6. Physical Controller

A **Zigbee rotary dial** (friendly name: `PlayBee | Controller`) provides physical interaction:

- **Dial rotation** (6 levels) → Volume up/down
- **Button 1** → Single press: restart current track / Double press: previous track
- **Button 2** → Next track

---

## 7. Music Assistant REST API

Two direct REST calls to MA (via `rest_command`), authenticated with `!secret playbee_ma_token`:

| Endpoint | Purpose | Key Payload |
|----------|---------|-------------|
| `player_queues/get` | Fetch current queue state (elapsed time, current track) | `queue_id` |
| `player_queues/play_index` | Jump to a specific queue item and seek | `queue_id`, `index`, `seek_position` |

These are necessary because HA's built-in MA integration does not expose fine-grained queue inspection or seek-to-position.

---

## 8. Playback Resume Flow

```
Tag scanned
    │
    ▼
Lookup tag in DB ──────────► Not found → log warning, abort
    │
    ▼
Check resume_data:
  ├─ Has valid payload?
  ├─ Within TTL? (e.g. 24h)
  └─ Both yes → mute, find queue item, seek, unmute
       No     → start fresh playback
```

Resume is written:
- **On pause** (instant).
- **Every 30 seconds** during active playback (heartbeat).

This means at most 30 seconds of progress can be lost on power loss or crash.

---

## 9. Tag Database Contents

The system manages **12 NFC tags**, configured from:

| Source | Count |
|--------|-------|
| Deezer playlists | 10 |
| Jellyfin playlists | 2 |

**Example tags:**

| Name | Media URL | Shuffle | Repeat | Resume TTL |
|------|-----------|---------|--------|------------|
| PlayBee - herrH Diskografie | `deezer://playlist/15318782523` | on | all | 24h |
| PlayBee - Karius und Baktus | `jellyfin://playlist/9e17bb2c...` | off | off | 12h |
| PlayBee - Die schönsten Kinderlieder... | `deezer://playlist/15416563661` | off | all | 24h |
| Dev - Alles von TiRiLi *(dev card)* | `deezer://playlist/15313601883` | off | off | 7d |

JSON exports are stored in `playbee/exports/tags/` (hourly, 14-day retention).

---

## 10. Key Design Decisions

- **Single-speaker model**: All playback targets `media_player.playbee_speaker`.
- **Tag-locked**: A guard (`input_text.playbee_active_tag_uid`) prevents starting new playback while a tag is active.
- **Dev card**: Tag `04-3D-AA-EA-40-59-80` remaps playlist prefixes (`PlayBee - ` → `Dev - `) for testing without polluting production resume data.
- **Direct MA API**: Queue inspection and seek use REST rather than HA services because MA's native services lack fine-grained queue control.
- **Minimal state loss**: The heartbeat every 30 s bounds potential data loss.
- **No git tracking**: The `playbee/` exports directory contains auto-generated JSON backups; they are likely excluded from git.

---

## File Reference

| File | Role |
|------|------|
| `configuration.yaml` | Shell commands, REST commands, recorder includes |
| `automations.yaml` | All PlayBee automations (NFC routing, volume, nav, backup, cleanup) |
| `scripts.yaml` | Core play/stop/resume/volume/navigation scripts |
| `custom_templates/playbee.jinja` | Normalizer macros |
| `custom_templates/playbee_fn.jinja` | Functional Jinja helpers (used via `\| as_function`) |
| `scripts/playbee_db.py` | SQLite database manager |
| `scripts/playbee_queue.py` | Music Assistant queue item locator |
| `esphome/playbee-tagreader.yaml` | ESPHome config for reader v1 |
| `esphome/playbee-tagreader-v2.yaml` | ESPHome config for reader v2 |
| `playbee/exports/tags/` | Hourly JSON backups of tag table |
| `zigbee2mqtt/configuration.yaml` | Zigbee device: `PlayBee \| Controller` |
