import asyncio
import logging
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from database import get_all_subscriptions, get_chats_for_channel, update_live_status
import config

logger = logging.getLogger(__name__)

class StreamMonitor:
    def __init__(self, notification_callback, twitch_client):
        self.notification_callback = notification_callback
        self.twitch = twitch_client

    async def start(self):
        logger.info("Monitor started")
        
        while True:
            try:
                await self.check_streams()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            await asyncio.sleep(60)  # Check every 60 seconds

    async def check_streams(self):
        channels = await get_all_subscriptions()
        if not channels:
            return

        # Twitch API allows fetching multiple streams at once (limit 100)
        # For simplicity in this v1, we assume < 100 channels. 
        # Production would need chunking.
        
        # We need to map logins to current stream data
        active_streams = {}
        
        # get_streams returns an async generator
        async for stream in self.twitch.get_streams(user_login=channels):
            active_streams[stream.user_login.lower()] = stream

        for channel in channels:
            channel_lower = channel.lower()
            stream_info = active_streams.get(channel_lower)
            
            # Get all chats watching this channel
            subscriptions = await get_chats_for_channel(channel_lower)
            
            for sub in subscriptions:
                chat_id = sub['chat_id']
                was_live = bool(sub['is_live'])
                custom_template = sub['custom_template']
                
                logger.info(f"DEBUG Monitor: chat_id={chat_id}, channel={channel_lower}, template_in_db={custom_template}")
                
                is_now_live = stream_info is not None
                
                if is_now_live and not was_live:
                    # Stream just started
                    await self.notification_callback(chat_id, stream_info, custom_template)
            
            # Update status in DB for all subscriptions of this channel
            # Note: This is a bit inefficient if we have many subscribers for one channel 
            # (updates DB N times), but safe for a simple bot. 
            # Optimization: Update once per channel, not per subscription.
            # I added update_live_status(channel, status) in database.py which handles it by channel.
            await update_live_status(channel_lower, stream_info is not None)

