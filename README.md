# Twitch Stream Announce Bot

A Telegram bot that monitors Twitch channels and sends notifications when they go live.

## Features

- Monitor multiple Twitch channels.
- Customize notification messages per channel.
- Asynchronous design using `aiogram` and `twitchAPI`.
- SQLite database for persistence.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration:**
   Rename `.env.example` to `.env` and fill in your credentials:
   - `TELEGRAM_BOT_TOKEN`: From @BotFather on Telegram.
   - `TWITCH_APP_ID` & `TWITCH_APP_SECRET`: From the [Twitch Developer Console](https://dev.twitch.tv/console).

3. **Run:**
   ```bash
   python main.py
   ```

## Commands

- `/start` - Introduction.
- `/add <channel_name>` - Subscribe to a Twitch channel.
- `/remove <channel_name>` - Unsubscribe.
- `/list` - List your subscriptions.
- `/template <channel_name> <message>` - Set a custom notification message.
  - Supported placeholders: `{user_name}`, `{game_name}`, `{title}`, `{user_login}`, `{viewer_count}`, `{started_at}`.
