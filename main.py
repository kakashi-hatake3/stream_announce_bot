import asyncio
import logging
import sys
from twitchAPI.twitch import Twitch
from bot import dp, bot, send_stream_notification
from monitor import StreamMonitor
import database
import config

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    # Init DB
    await database.init_db()
    
    # Init Twitch
    twitch = await Twitch(config.TWITCH_APP_ID, config.TWITCH_APP_SECRET)
    
    # Init Monitor
    monitor = StreamMonitor(notification_callback=send_stream_notification, twitch_client=twitch)
    
    # Start Monitor as background task
    asyncio.create_task(monitor.start())
    
    # Start Bot
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, twitch=twitch)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
