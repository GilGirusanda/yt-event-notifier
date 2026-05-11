# yt-event-notifier

A self-hosted Telegram bot that helps YouTube channel owners notify their Telegram groups and channels about upcoming live streams. Admins configure a weekly stream schedule inside Telegram. The bot checks YouTube for the corresponding broadcast (creating it if needed), sends a reminder before it starts, and a "now live" alert when it goes live.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Setup Guide](#setup-guide)
5. [First-Time Bot Configuration](#first-time-bot-configuration)
6. [Commands Reference](#commands-reference)
7. [Environment Variables Reference](#environment-variables-reference)
8. [Local Development](#local-development)
9. [Contributing](#contributing)

---

## Overview

yt-event-notifier is a Python bot that bridges a YouTube channel's live stream schedule with one or more Telegram groups. Admins define a recurring weekly schedule (e.g. "every Tuesday at 18:00") directly via Telegram commands. Before each scheduled stream the bot locates the matching YouTube broadcast — creating it automatically if auto-create is enabled — and sends a configurable reminder message to the group. When the stream goes live, the bot sends a second "now live" alert. The bot supports multiple independent Telegram groups, each connected to its own YouTube channel via OAuth 2.0, with its own schedule, timezone, and message templates.

---

## Architecture

### Infrastructure

The bot runs as a single AWS Lambda function exposed through two AWS API Gateway routes and triggered on a schedule by AWS EventBridge.

```
Telegram
   |
   | HTTPS webhook (POST /webhook)
   v
API Gateway (HTTP API)
   |---> Lambda  <---  EventBridge cron (every 15 min / every 5 min near stream)
   |
   | OAuth callback (GET /oauth/callback)
   v
Lambda
   |
   |---> YouTube Live Streaming API (OAuth 2.0)
   |---> S3 (SQLite database file)
   |---> Telegram Bot API
```

### Three Lambda Entry Points

The Lambda handler inspects the incoming event shape to determine what triggered it:

| Trigger          | Event shape                               | Handler behaviour                              |
| ---------------- | ----------------------------------------- | ---------------------------------------------- |
| Telegram webhook | API Gateway event, path `/webhook`        | Dispatch to python-telegram-bot handlers       |
| OAuth callback   | API Gateway event, path `/oauth/callback` | Exchange auth code, store tokens, notify admin |
| Scheduled poll   | EventBridge event (no `requestContext`)   | Check upcoming streams, send reminders/alerts  |

### Adaptive Polling Strategy

Two EventBridge cron rules control the polling cadence:

- **Baseline rule** — fires every 15 minutes at all times. Always runs a full poll for all groups.
- **Near-stream rule** — fires every 5 minutes at all times. On each invocation the Lambda first checks whether any stream is scheduled to start within the next 30 minutes. If yes, it runs a full poll. If no, it exits immediately. This conserves YouTube API quota while providing timely "now live" detection near stream start.

### Database

SQLite is used as the database, accessed via `aiosqlite`. The `.db` file lives in an S3 bucket. On each Lambda cold start the file is downloaded from S3. On exit (after processing the event) the file is uploaded back to S3. The `streams` table holds only upcoming and active entries; records for streams that have ended are deleted on the next poll cycle.

### Multi-Group Support

Each Telegram group the bot is added to is fully independent: its own connected YouTube channel, weekly slot schedule, timezone, reminder timing, and message templates. There is no shared state between groups.

---

## Project Structure

```
yt-event-notifier/
├── src/
│   ├── handler.py          # Lambda entry point — routes events to bot, OAuth, or poller
│   ├── poller.py           # EventBridge cron handler — stream check, reminders, live detection, cleanup
│   ├── local_server.py     # Dev-only HTTP server for local webhook + OAuth testing
│   ├── logging_config.py   # Centralised logging setup — StreamHandler + S3-backed rotating file handler
│   ├── bot/
│   │   ├── commands.py     # python-telegram-bot command handlers (/addslot, /connectyoutube, …)
│   │   └── messages.py     # Telegram notification message rendering and templates
│   ├── db/
│   │   ├── client.py       # aiosqlite connection management + S3 download/upload lifecycle
│   │   ├── schema.py       # CREATE TABLE statements and schema migrations
│   │   └── queries.py      # CRUD helpers for the groups, slots, and streams tables
│   └── youtube/
│       ├── client.py       # YouTube Live Streaming API calls (liveBroadcasts, liveStreams)
│       └── oauth.py        # OAuth URL generation, authorisation code exchange, token refresh
├── tests/
├── .env.example            # Environment variable template
├── requirements.txt
├── prd.md
├── README.md
└── LICENSE
```

### Module Descriptions

| Module | Responsibility |
| --- | --- |
| `src/handler.py` | Single Lambda entry point. Inspects the incoming event shape and dispatches to the Telegram bot application, the OAuth callback handler, or the poll loop. |
| `src/poller.py` | Runs on every EventBridge trigger. For each registered group: checks/creates YouTube broadcasts, sends reminders, detects live status, and cleans up ended stream records. |
| `src/local_server.py` | Lightweight aiohttp-based HTTP server used during local development to receive Telegram webhook updates and OAuth callbacks without deploying to AWS. |
| `src/bot/commands.py` | Registers and implements all Telegram slash commands using `python-telegram-bot`. Validates admin permissions via the Telegram API before executing any configuration command. |
| `src/bot/messages.py` | Renders reminder and "now live" notification text, applying per-slot custom messages and localising stream times to the group's configured timezone. |
| `src/db/client.py` | Manages the SQLite connection lifecycle. Downloads the `.db` file from S3 at the start of each invocation and uploads it back after processing. |
| `src/db/schema.py` | Defines the three core tables (`groups`, `slots`, `streams`) and handles any incremental schema migrations. |
| `src/db/queries.py` | Provides async CRUD functions used by the poller and command handlers, keeping SQL out of business logic. |
| `src/youtube/client.py` | Wraps the YouTube Live Streaming API: searching for existing broadcasts, creating broadcasts and stream objects, binding them, and checking broadcast status. |
| `src/youtube/oauth.py` | Handles the full OAuth 2.0 lifecycle: generating the authorisation URL with a signed `state` parameter, exchanging the callback code for tokens, and refreshing expired access tokens before each API call. |

---

## Prerequisites

Before starting setup, ensure you have access to the following:

- **AWS account** with permissions to create Lambda functions, API Gateway HTTP APIs, EventBridge rules, and S3 buckets.
- **Google Cloud project** with the YouTube Data API v3 enabled and OAuth 2.0 credentials (web application type) created. You will need the client ID, client secret, and a configured redirect URI.
- **Telegram bot token** from [@BotFather](https://t.me/BotFather).
- **Python 3.12** and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed locally for development and packaging.

---

## Setup Guide

### 1. Create a Google Cloud Project and Enable the YouTube API

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project.
2. Navigate to **APIs & Services > Library** and enable **YouTube Data API v3**.
3. Navigate to **APIs & Services > OAuth consent screen**. Configure the consent screen (External or Internal depending on your use case). Add the scope `https://www.googleapis.com/auth/youtube`.
4. Navigate to **APIs & Services > Credentials** and click **Create Credentials > OAuth client ID**.
5. Select **Web application** as the application type.
6. Under **Authorized redirect URIs**, add the URI where your Lambda will receive the OAuth callback. This will be the API Gateway URL with the path `/oauth/callback` (you can update this after deployment). Click **Create**.
7. Note the **Client ID** and **Client Secret**.

### 2. Create a Telegram Bot

1. Open Telegram and start a conversation with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a name and username.
3. Note the **bot token** provided at the end.
4. Optionally, use `/setcommands` in BotFather to register the command list for discoverability.

### 3. Create the S3 Bucket

1. In the AWS Console, create an S3 bucket in your preferred region (e.g. `my-yt-notifier-db`).
2. Block all public access. The Lambda will access it via its IAM role.
3. Note the bucket name and decide on a key for the database file (default: `db/streams.db`).

> **Security note:** The SQLite file contains Google OAuth tokens (access and refresh). Keep the bucket private and restrict IAM access to the Lambda execution role only. Enable S3 server-side encryption (SSE-S3 or SSE-KMS) for defence in depth.

### 4. Set Environment Variables

Create a `.env` file for local development (see [Local Development](#local-development)) and set the same variables in the Lambda function configuration:

```
TELEGRAM_BOT_TOKEN=<your-bot-token>
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
GOOGLE_REDIRECT_URI=https://<api-gateway-id>.execute-api.<region>.amazonaws.com/oauth/callback
ADMIN_CHAT_ID=<your-telegram-user-id>
S3_BUCKET=<your-s3-bucket-name>
S3_DB_KEY=db/streams.db
```

### 5. Deploy the Lambda Function

1. Package the application and its dependencies into a deployment zip:

   ```bash
   uv export --no-dev --no-emit-project -o requirements-deploy.txt
   pip install -r requirements-deploy.txt --target ./package
   cd package && zip -r ../deployment.zip . && cd ..
   zip -g deployment.zip -r src/
   rm requirements-deploy.txt
   ```

2. Create the Lambda function in the AWS Console or via the AWS CLI:

   ```bash
   aws lambda create-function \
     --function-name yt-event-notifier \
     --runtime python3.12 \
     --handler src.handler.lambda_handler \
     --zip-file fileb://deployment.zip \
     --role arn:aws:iam::<account-id>:role/<lambda-execution-role>
   ```

3. Set the environment variables on the function (use the AWS Console or `aws lambda update-function-configuration`).

4. Attach an IAM policy to the Lambda execution role that grants `s3:GetObject` and `s3:PutObject` on your S3 bucket.

5. Create an API Gateway HTTP API and attach it to the Lambda. Add two routes:
   - `POST /webhook`
   - `GET /oauth/callback`

6. Note the API Gateway invoke URL (e.g. `https://<id>.execute-api.<region>.amazonaws.com`).

7. Update `GOOGLE_REDIRECT_URI` in your Lambda environment variables to use the actual API Gateway URL.

### 6. Create EventBridge Rules

Create two EventBridge (Scheduler) rules targeting the Lambda function:

**Baseline rule** — runs every 15 minutes:

```
cron(0/15 * * * ? *)
```

**Near-stream rule** — runs every 5 minutes. Configure this rule's schedule to remain active; the Lambda itself decides whether a stream is imminent before acting on the 5-minute cadence:

```
cron(0/5 * * * ? *)
```

Both rules must have permission to invoke the Lambda function.

### 7. Register the Telegram Webhook

After deployment, register the webhook with Telegram so updates are pushed to your API Gateway endpoint:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<api-gateway-id>.execute-api.<region>.amazonaws.com/webhook"}'
```

Verify the webhook is registered:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

---

## First-Time Bot Configuration

After adding the bot to a Telegram group, an admin runs the following sequence to complete setup:

1. **Connect a YouTube channel** — the bot sends a Google authorization URL:

   ```
   /connectyoutube
   ```

   Open the URL, sign in with the Google account that owns the YouTube channel, and grant the requested permissions. The bot confirms once the OAuth callback is received.

2. **Set the group timezone** — use a standard tz database name:

   ```
   /settimezone Europe/London
   ```

3. **Add a weekly stream slot** — specify the day and time in 24-hour format:

   ```
   /addslot Tuesday 18:00
   ```

   Repeat for each recurring slot. Use `/listslots` to see slot IDs.

4. **Set a stream title template** for a slot:

   ```
   /settemplate 1 Weekly Stream - {{date}}
   ```

   Supported variables: `{{date}}`, `{{channel}}`.

5. **Set a custom reminder or live message** (optional):

   ```
   /setmessage 1 Reminder: stream starts in {{hours}} hours!
   ```

6. **Enable auto-create** if you want the bot to create YouTube broadcasts automatically when none is found:

   ```
   /setautocreate on
   ```

7. **Verify the configuration**:
   ```
   /status
   /listslots
   ```

---

## Commands Reference

| Command                             | Description                                                                                       | Access |
| ----------------------------------- | ------------------------------------------------------------------------------------------------- | ------ |
| `/start`                            | Introduction message and basic usage info                                                         | All    |
| `/help`                             | List available commands                                                                           | All    |
| `/connectyoutube`                   | Start the OAuth flow to link a YouTube channel to this group                                      | Admin  |
| `/disconnectyoutube`                | Revoke and remove the stored YouTube OAuth tokens for this group                                  | Admin  |
| `/settimezone <tz>`                 | Set the group timezone (e.g. `America/New_York`). All slot times are interpreted in this timezone | Admin  |
| `/setautocreate <on\|off>`          | When `on`, the bot creates a YouTube broadcast if none is found for a scheduled slot              | Admin  |
| `/setreminder <hours>`              | How many hours before stream start to send the reminder message                                   | Admin  |
| `/setcheckwindow <hours>`           | How many hours before stream start the bot begins actively checking YouTube for the broadcast     | Admin  |
| `/addslot <day> <HH:MM>`            | Add a recurring weekly stream slot. Day is a full English day name (e.g. `Tuesday`)               | Admin  |
| `/removeslot <slot_id>`             | Remove a weekly slot by its ID (see `/listslots`)                                                 | Admin  |
| `/settemplate <slot_id> <template>` | Set the YouTube broadcast title template for a slot. Supports `{{date}}` and `{{channel}}`        | Admin  |
| `/setmessage <slot_id> <message>`   | Set the Telegram message sent as a reminder or live alert for a slot                              | Admin  |
| `/listslots`                        | List all configured slots with their IDs, times, and templates                                    | Admin  |
| `/streams`                          | List upcoming and active streams the bot is tracking for this group                               | Admin  |
| `/status`                           | Show connection status, timezone, and current settings for this group                             | Admin  |
| `/check`                            | Manually trigger a stream check for this group. Rate-limited                                      | Admin  |

---

## Environment Variables Reference

| Variable               | Required | Default         | Description                                                                                  |
| ---------------------- | -------- | --------------- | -------------------------------------------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN`   | Yes      | —               | Bot token from BotFather                                                                     |
| `GOOGLE_CLIENT_ID`     | Yes      | —               | OAuth 2.0 client ID from Google Cloud Console                                                |
| `GOOGLE_CLIENT_SECRET` | Yes      | —               | OAuth 2.0 client secret from Google Cloud Console                                            |
| `GOOGLE_REDIRECT_URI`  | Yes      | —               | Full URI of the `/oauth/callback` API Gateway endpoint                                       |
| `ADMIN_CHAT_ID`        | Yes      | —               | Telegram user ID of the bot owner. Receives critical error alerts (Lambda crash, S3 failure) |
| `S3_BUCKET`            | Yes      | —               | Name of the S3 bucket used to store the SQLite database file                                 |
| `S3_DB_KEY`            | No       | `db/streams.db` | S3 object key for the SQLite database file                                                   |
| `LOG_BUCKET`           | No       | —               | S3 bucket to receive rotated log files. When set (and not running in Lambda), a rotating file handler is enabled in addition to stdout. Ignored in Lambda — logs go to CloudWatch. |
| `LOG_FILE`             | No       | `logs/app.log`  | Local path for the active log file. Rotated files are written alongside it before upload.    |
| `LOCAL_PORT`           | No       | `8080`          | TCP port the local development server (`local_server.py`) listens on.                        |

### Error Alert Tiers

| Severity   | Examples                                           | Recipient                              |
| ---------- | -------------------------------------------------- | -------------------------------------- |
| Critical   | Lambda crash, S3 read/write failure                | DM to bot owner (`ADMIN_CHAT_ID`)      |
| Actionable | OAuth token expired, no broadcast found for a slot | DM to all admins of the affected group |

---

## Local Development

### Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository and install dependencies:

   ```bash
   git clone <repo-url>
   cd yt-event-notifier
   uv sync
   ```

   This pins Python 3.12, creates a `.venv`, and installs all dependencies from `uv.lock`.

3. Copy the example environment file and fill in your values:

   ```bash
   cp .env.example .env
   ```

### Logging

The local server writes logs to stdout and, when `LOG_BUCKET` is set, to a rotating file at `LOG_FILE` (default `logs/app.log`). Files rotate daily at midnight; the 7 most recent files are kept locally. Each rotated file is uploaded to the configured S3 bucket under the `logs/` prefix immediately after rotation.

In Lambda the file handler is skipped — the runtime captures stdout and sends it to CloudWatch Logs automatically.

### Using a Local SQLite File

Set `S3_BUCKET` to an empty string or add a flag in your local runner to skip the S3 download/upload and use a local file path directly. This avoids the need for AWS credentials during development.

### Webhook Testing with ngrok

Telegram requires a publicly accessible HTTPS URL to deliver webhook updates. Use [ngrok](https://ngrok.com) to expose your local server:

1. Start the local server (adjust the entry point to your project's local runner):

   ```bash
   python -m src.local_server
   ```

2. In a separate terminal, start ngrok:

   ```bash
   ngrok http 8080
   ```

3. Register the ngrok URL as the Telegram webhook:

   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://<ngrok-subdomain>.ngrok.io/webhook"}'
   ```

4. Update `GOOGLE_REDIRECT_URI` in your `.env` to point to the ngrok URL for OAuth callbacks:

   ```
   GOOGLE_REDIRECT_URI=https://<ngrok-subdomain>.ngrok.io/oauth/callback
   ```

Note: ngrok generates a new subdomain each run on the free tier. Re-register the webhook and update the redirect URI each time.

### Simulating EventBridge Triggers

To test the scheduled poll handler locally, invoke the Lambda handler directly with a mock EventBridge event:

```python
from src.handler import lambda_handler

event = {"source": "aws.events", "detail-type": "Scheduled Event"}
context = {}
lambda_handler(event, context)
```

---

## Contributing

Contributions are welcome. Please follow these conventions:

- **Branch naming**: `feature/<short-description>`, `fix/<short-description>`, or `chore/<short-description>`.
- **Pull requests**: Open a PR against `main`. Include a clear description of what changed and why. Reference any related issues.
- Keep PRs focused on a single concern. Large refactors should be discussed in an issue first.

A formal contribution guide and CI setup will be added as the project matures.
