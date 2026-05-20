# Product Requirements Document — `yt-event-notifier`

> **Status:** Draft v0.2
> **Language:** Python
> **Last updated:** 2026-05-09

---

## 1. Overview

`yt-event-notifier` is a self-hosted Telegram bot that helps YouTube channel owners notify their Telegram groups and channels about upcoming live streams. Admins configure a weekly stream schedule inside Telegram; the bot automatically checks YouTube for the corresponding broadcast (creating it if needed), then sends a reminder before it starts and a "now live" alert when it goes live.

---

## 2. Goals

- Let channel owners keep their Telegram community informed about upcoming streams without manual effort after initial setup.
- Keep all configuration inside Telegram — zero friction for non-technical admins.
- Run cheaply on AWS Lambda with SQLite on S3, staying well within YouTube API quota limits.

---

## 3. Non-Goals (v1)

- No support for Twitch, YouTube premieres, or VOD notifications.
- No per-member notification preferences.
- No web dashboard or config file management.
- Not a SaaS product; single-instance, self-hosted only.
- No edit-in-place of reminder messages when a stream goes live (separate messages only; see Backlog).

---

## 4. Users & Roles

| Role                     | Description                                              | Permissions                                                                        |
| ------------------------ | -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Group/Channel Admin**  | A Telegram user with admin rights in the configured chat | Full bot configuration: YouTube connection, schedule, templates, reminder settings |
| **Group/Channel Member** | Any other member of the chat                             | Receives notifications; no configuration access                                    |
| **Bot Owner**            | The person who deploys the bot                           | Defined at deploy time via `ADMIN_CHAT_ID`; receives critical system error DMs     |

> Admin status is verified against the Telegram API at command execution time.

---

## 5. Core Features

### 5.1 Stream Schedule Management

- Admins configure **recurring weekly slots** per group (e.g. every Monday at 20:00).
- Each slot stores:
  - Day of week + local time (interpreted in the group's configured timezone)
  - A **title template** for the YouTube stream (supports `{date}` and `{channel}` variables). `{date}` resolves to the slot's scheduled date in `DD-MM-YYYY` format in the group's local timezone; `{channel}` resolves to the connected YouTube channel name.
  - A **custom notification message** (short promo text appended to Telegram reminders)
- A group can have multiple weekly slots.
- Slots are fully independent between groups.

### 5.2 YouTube Integration

- Each group connects **one YouTube channel** via a bot-guided **OAuth 2.0 flow**: the bot sends a Google sign-in link via Telegram; the admin authorises it in a browser; tokens are stored in the database.
- The bot uses the **YouTube Live Streaming API**: `liveBroadcasts.list`, `liveBroadcasts.insert`, `liveStreams.insert`, `liveBroadcasts.bind`.
- A configurable **stream check window** (default: 24 hours before a slot) determines how far in advance the bot looks for or creates the stream on YouTube.
- **Auto-create** (per-group toggle, default: off): if enabled and no broadcast exists for an upcoming slot, the bot creates it on YouTube using the slot's title template. Auto-created broadcasts use per-group configurable settings: **privacy** (public / unlisted / private, default: `public`) and **description** (plain text, default: empty). See `/setbroadcastprivacy` and `/setbroadcastdescription` in §5.4.
- If auto-create is off and no stream is found within the check window, the group's admins are alerted via DM and nothing is sent to the group.
- OAuth access tokens are refreshed automatically before each API call. If refresh fails, group admins are alerted.

### 5.3 Notification System

Two notification types per stream:

| Event                                                                               | Target        | Content                                                                     |
| ----------------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------- |
| `reminder_hours` before `scheduledStartTime` (default: 1 h, configurable per group) | Group/channel | Stream title, scheduled time (local timezone), YouTube link, custom message |
| Stream status transitions to `live`                                                 | Group/channel | "Now live" alert with stream title and YouTube link                         |

- Duplicate notifications are prevented via `reminder_sent` and `live_sent` flags per stream record.
- Each notification type is sent exactly once per stream occurrence.

### 5.4 Telegram Command Interface

Configuration commands require Telegram admin rights. `/start`, `/streams`, and `/help` are available to all members.

| Command                                            | Description                                                                                                            |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `/start`                                           | Register the bot in this group/channel and display setup instructions                                                  |
| `/help`                                            | Display all available commands                                                                                         |
| `/connectyoutube`                                  | Start the OAuth 2.0 flow to link a YouTube channel to this group                                                       |
| `/disconnectyoutube`                               | Remove the YouTube channel connection and delete stored tokens                                                         |
| `/settimezone <tz>`                                | Set the group's timezone (IANA format, e.g. `Europe/London`)                                                           |
| `/setautocreate <on\|off>`                         | Toggle automatic YouTube stream creation for this group                                                                |
| `/setreminder <hours>`                             | Set the reminder window in hours before stream start (default: 1)                                                      |
| `/setcheckwindow <hours>`                          | Set how many hours before a slot to check/create the stream (default: 24)                                              |
| `/addslot <day> <HH:MM> [title_template]`          | Add a weekly recurring slot. Title template is optional inline shortcut; use `/settemplate` to set or update it later. |
| `/removeslot <slot_id>`                            | Remove a scheduled slot by ID                                                                                          |
| `/settemplate <slot_id> <template>`                | Set the YouTube stream title template for a slot                                                                       |
| `/setmessage <slot_id> <message>`                  | Set the custom notification message for a slot                                                                         |
| `/listslots`                                       | List all configured slots with their IDs and settings                                                                  |
| `/streams`                                         | List upcoming tracked streams with scheduled times and YouTube links                                                   |
| `/status`                                          | Show bot health, YouTube connection status, and next scheduled poll time                                               |
| `/check`                                           | Trigger an immediate poll for this group (admin only)                    |
| `/setbroadcastprivacy <public\|unlisted\|private>` | Set the default privacy for auto-created YouTube broadcasts (default: `public`)                                        |
| `/setbroadcastdescription <text>`                  | Set the default description for auto-created YouTube broadcasts (default: empty)                                       |

### 5.5 Admin Error Alerts

Two alert tiers:

| Tier           | Recipient                                     | Triggers                                                                                              |
| -------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Critical**   | Bot owner (DM to `ADMIN_CHAT_ID`)             | Lambda crash, S3 read/write failure, database corruption                                              |
| **Actionable** | All admins of the affected group (DM to each) | No stream found and auto-create is off, OAuth token refresh failure, YouTube API error for that group |

All alerts include a timestamp, error type, and short description.

---

## 6. Technical Architecture

### 6.1 Stack

| Layer              | Technology                                                               |
| ------------------ | ------------------------------------------------------------------------ |
| Language           | Python 3.12                                                              |
| Telegram framework | `python-telegram-bot` v21+                                               |
| YouTube API        | `google-api-python-client` (`liveBroadcasts`, `liveStreams`)             |
| Google Auth        | `google-auth-oauthlib`                                                   |
| Database           | SQLite via `aiosqlite`                                                   |
| DB persistence     | AWS S3 (SQLite file downloaded at start of invocation, uploaded on exit) |
| Deployment         | AWS Lambda (single function)                                             |
| Scheduling         | AWS EventBridge (two cron rules — see §6.4)                              |
| Webhook ingress    | AWS API Gateway (HTTP API)                                               |

### 6.2 Lambda Entry Points

One Lambda function handles three event sources, distinguished by event shape:

| Source                         | Detection                                                        | Handler                                                                                                                                             |
| ------------------------------ | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| API Gateway — Telegram webhook | `"httpMethod" in event` and `event["path"] != "/oauth/callback"` | Validate `X-Telegram-Bot-Api-Secret-Token` header; reject with HTTP 403 if missing or invalid. Parse Telegram update; dispatch to command handlers. |
| API Gateway — OAuth callback   | `event["path"] == "/oauth/callback"`                             | Exchange Google auth code for tokens; store; notify group                                                                                           |
| EventBridge cron               | `event.get("source") == "aws.events"`                            | Run YouTube poll loop (§6.4)                                                                                                                        |

### 6.3 Database Schema

**`groups`** — one row per registered Telegram group or channel

| Column               | Type       | Description                                                                                                                                                                          |
| -------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `group_id`           | INTEGER PK | Telegram chat ID                                                                                                                                                                     |
| `timezone`           | TEXT       | IANA timezone string (e.g. `Europe/London`). Validated against the `zoneinfo` database at `/settimezone` time; the bot guides admins with an example prompt if the value is invalid. |
| `reminder_hours`     | REAL       | Hours before stream start to send reminder (default: 1)                                                                                                                              |
| `check_window_hours` | REAL       | Hours before slot to check/create stream (default: 24)                                                                                                                               |
| `auto_create`        | BOOLEAN    | Auto-create streams on YouTube (default: false)                                                                                                                                      |
| `yt_channel_id`      | TEXT       | Connected YouTube channel ID (nullable)                                                                                                                                              |
| `yt_access_token`    | TEXT       | OAuth access token (nullable)                                                                                                                                                        |
| `yt_refresh_token`   | TEXT       | OAuth refresh token (nullable)                                                                                                                                                       |
| `yt_token_expiry`    | INTEGER    | Unix timestamp of access token expiry (nullable)                                                                                                                                     |
| `last_manual_check`  | INTEGER    | Unix timestamp of last `/check` invocation (for rate-limiting)                                                                                                                       |

**`slots`** — weekly schedule slots per group

| Column           | Type                  | Description                                          |
| ---------------- | --------------------- | ---------------------------------------------------- |
| `slot_id`        | INTEGER PK            | Auto-increment                                       |
| `group_id`       | INTEGER FK → `groups` | Parent group                                         |
| `day_of_week`    | INTEGER               | 0 = Monday … 6 = Sunday                              |
| `local_time`     | TEXT                  | `HH:MM` in the group's timezone                      |
| `title_template` | TEXT                  | YouTube stream title; supports `{date}`, `{channel}` |
| `custom_message` | TEXT                  | Promo text appended to Telegram notifications        |

**`streams`** — active/upcoming streams only; ended streams are deleted on the next poll

| Column            | Type                  | Description                                         |
| ----------------- | --------------------- | --------------------------------------------------- |
| `broadcast_id`    | TEXT PK               | YouTube broadcast ID                                |
| `group_id`        | INTEGER FK → `groups` | Parent group                                        |
| `slot_id`         | INTEGER FK → `slots`  | Source slot                                         |
| `scheduled_start` | INTEGER               | Unix timestamp of scheduled start (UTC)             |
| `status`          | TEXT                  | `scheduled`, `live`, or `ended`                     |
| `yt_url`          | TEXT                  | YouTube watch URL                                   |
| `reminder_sent`   | BOOLEAN               | Whether the pre-stream reminder has been dispatched |
| `live_sent`       | BOOLEAN               | Whether the "now live" alert has been dispatched    |

### 6.4 Cron Poll Loop

**Adaptive polling** uses two EventBridge rules:

- **Rule A** — fires every 15 minutes; always runs a full poll.
- **Rule B** — fires every 5 minutes; Lambda checks whether any stream is scheduled to start within the next 30 minutes. If yes, runs a full poll. If no, exits immediately.

On each active poll run, for every registered group (in parallel where possible):

1. **Stream check / creation** — for each slot, compute its next scheduled occurrence. If that occurrence falls within `check_window_hours` from now and has no matching row in `streams`, proceed:
   - Call `liveBroadcasts.list` to search for an existing broadcast at that time.
   - If found: insert a `streams` row.
   - If not found and `auto_create = true`: call `liveBroadcasts.insert` + `liveStreams.insert` + `liveBroadcasts.bind`; insert a `streams` row.
   - If not found and `auto_create = false`: DM all group admins with an alert.

2. **Reminder dispatch** — for each `streams` row where `scheduled_start − now ≤ reminder_hours` and `reminder_sent = false`:
   - Send reminder to the group/channel (title, localised time, YouTube link, custom message).
   - Set `reminder_sent = true`.

3. **Live detection** — for each `streams` row where `scheduled_start` is in the past and `live_sent = false`:
   - Call `liveBroadcasts.list` to fetch current broadcast status.
   - If `live`: send "now live" alert to group/channel; set `live_sent = true`.
   - If `complete` / `revoked`: update `status = ended`.

4. **Cleanup** — delete all `streams` rows where `status = ended`.

### 6.5 OAuth Flow

1. Admin runs `/connectyoutube` in the group.
2. Bot generates a Google OAuth authorisation URL with a signed `state` parameter encoding `group_id`.
3. Admin receives the URL as a Telegram message, opens it in a browser, and grants YouTube permissions.
4. Google redirects to the bot's `GOOGLE_REDIRECT_URI` (API Gateway endpoint `/oauth/callback`).
5. Lambda exchanges the authorisation code for access and refresh tokens; stores them in the `groups` table.
6. Lambda sends a confirmation message to the group.

---

## 7. Environment Variables

| Variable               | Description                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN`   | Bot token from BotFather                                                      |
| `GOOGLE_CLIENT_ID`     | OAuth 2.0 client ID from Google Cloud Console                                 |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret                                                       |
| `GOOGLE_REDIRECT_URI`  | Full HTTPS URL of the API Gateway OAuth callback endpoint                     |
| `ADMIN_CHAT_ID`        | Telegram user ID of the bot owner (for critical error DMs)                    |
| `S3_BUCKET`            | Name of the S3 bucket holding the SQLite file                                 |
| `S3_DB_KEY`            | S3 object key for the SQLite file (default: `db/streams.db`)                  |
| `LOG_BUCKET`           | S3 bucket for rotated log files; enables file logging when set outside Lambda |
| `LOG_FILE`             | Local path for the active log file (default: `logs/app.log`)                  |
| `LOCAL_PORT`           | TCP port for the local development server (default: `8080`)                   |

---

## 8. Constraints & Risks

| Risk                                    | Mitigation                                                                                                                                                                        |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S3 concurrent write collision           | At this scale (5 groups, ~5 streams/week), truly concurrent invocations are rare. Enable S3 object versioning; detect version conflict on upload and retry with a fresh download. |
| OAuth token expiry mid-poll             | Refresh token before every API call using the stored refresh token; alert group admins if refresh fails.                                                                          |
| YouTube API quota                       | `liveBroadcasts.list` costs 1 unit/call. Estimated peak usage: ~300 units/day. No quota tracking needed for v1.                                                                   |
| Telegram rate limits (429)              | Catch `RetryAfter` responses from `python-telegram-bot`; the library handles backoff automatically.                                                                               |
| Live detection lag                      | Acceptable: up to 5 minutes near stream start (adaptive polling window).                                                                                                          |
| Lambda cold start + S3 download latency | Acceptable for this workload; no sub-second SLA on cron-triggered runs.                                                                                                           |

---

## 9. Backlog (Post-v1)

- Edit the reminder message in place when the stream goes live, instead of sending a separate "now live" message.
- Multiple YouTube channels per group (each with its own OAuth connection).
- Per-slot reminder window override (currently reminder window is group-level only).
- Additional title template variables beyond `{date}` and `{channel}`.
- Stream notification history and basic analytics.
