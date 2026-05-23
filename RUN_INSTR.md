# Running the Project Locally (with Web App)

Here are the complete, step-by-step instructions to run the application locally with the newly integrated Web App functionality:

### 1. Install Dependencies
The project uses `uv` for lightning-fast dependency management. Make sure you have it installed, then run:
```bash
uv sync
```

### 2. Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```
Inside your `.env` file, ensure the following critical variables are set:
```ini
APP_PROFILE=dev
TELEGRAM_BOT_TOKEN=<your_bot_token>
GOOGLE_CLIENT_ID=<your_google_oauth_id>
GOOGLE_CLIENT_SECRET=<your_google_oauth_secret>

# This tells the server what shortname to use when generating the direct link inside the group
WEBAPP_SHORT_NAME=config

# Leave these blank or default for local SQLite usage
S3_BUCKET=
```

### 3. Start a Secure Tunnel
Telegram Web Apps **require** an HTTPS connection. You must expose your local port `8080` (the default port) to the internet. 

**Using localtunnel (Recommended for persistent subdomains):**
```bash
npx localtunnel --port 8080 --subdomain my-yt-notifier
```
*(This gives you `https://my-yt-notifier.loca.lt`)*

### 4. Register the Web App with BotFather
1. Open Telegram and message **@BotFather**.
2. Send the command `/newapp`.
3. Choose your bot from the list.
4. Provide a Title (e.g., "Settings") and a short description.
5. Upload a 644x316 photo and a logo (or type `/empty` to skip).
6. **Important:** When asked for the Web App URL, provide the full path to the HTML file using your tunnel:
   `https://my-yt-notifier.loca.lt/ui/index.html`
7. Set the short name. You **must** set it to `config` (or whatever you set `WEBAPP_SHORT_NAME` to in your `.env`).

### 5. Update Webhook and OAuth URIs
Now that you have your HTTPS tunnel URL, update your `.env` file with the callbacks:
```ini
# Add the /oauth/callback path to your tunnel URL
GOOGLE_REDIRECT_URI=https://my-yt-notifier.loca.lt/oauth/callback
```
*Note: In development mode (`APP_PROFILE=dev`), `src/main.py` uses `python-telegram-bot`'s long-polling locally, so you don't actually need to register the Telegram webhook via curl unless you are testing the AWS Lambda handler natively.*

### 6. Run the Application
Start the bot server:
```bash
uv run python src/main.py
```

### 7. Setup in Telegram
1. Add your bot to a Telegram group.
2. Promote the bot to an **Administrator** (required to manage settings).
3. Send `/start` in the group to initialize it in the database.
4. Send `/webapp` in the group. 
5. Click the "Open Settings" button that the bot replies with.
6. The glassmorphic configuration Web App will open directly over the chat!
