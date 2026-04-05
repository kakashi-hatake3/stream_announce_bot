import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
import config
import database

# Initialize Bot
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

async def send_stream_notification(chat_id, stream_info, template=None):
    """
    Sends a notification to the chat.
    stream_info is a twitchAPI Stream object.
    """
    default_template = "🔴 {user_name} is now live!\n\nPlaying: {game_name}\nTitle: {title}\n\nhttps://twitch.tv/{user_login}"
    
    # Try fetching custom template if not passed
    if not template:
        template = await database.get_custom_template(chat_id, stream_info.user_login)
        print(template)

    msg_text = template if template else default_template
    
    # Safe formatting
    try:
        formatted_text = msg_text.format(
            user_name=stream_info.user_name,
            game_name=stream_info.game_name,
            title=stream_info.title,
            user_login=stream_info.user_login,
            viewer_count=stream_info.viewer_count,
            started_at=stream_info.started_at
        )
        print("norm")
    except Exception:
        print('fall')
        # Fallback if user used invalid keys
        formatted_text = f"🔴 {stream_info.user_name} is live! (Template error)\nhttps://twitch.tv/{stream_info.user_login}"

    try:
        # Added parse_mode="Markdown" to support [text](url)
        await bot.send_message(chat_id=chat_id, text=formatted_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Failed to send message to {chat_id}: {e}")

async def check_permissions(message: Message, target_chat_id: int) -> bool:
    """
    Checks if the user has permission to manage the target chat.
    Returns True if allowed, False otherwise (and sends a rejection message).
    """
    user_id = message.from_user.id
    
    # 1. User managing their own private chat -> Allowed
    if target_chat_id == user_id:
        return True

    # 2. User managing a group/channel (remote or local)
    try:
        member = await bot.get_chat_member(target_chat_id, user_id)
        if member.status in ['administrator', 'creator']:
            return True
        else:
            await message.answer("⛔ You must be an administrator of that chat to perform this action.")
            return False
    except Exception as e:
        # Bot might not be in the chat or other error
        await message.answer(f"⚠ Could not verify permissions for chat {target_chat_id}. Ensure I am a member/admin there.\nError: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Hello! I can notify you when a Twitch channel goes live.\n"
        "Commands:\n"
        "/add <channel> [chat_id] - Subscribe to a channel\n"
        "/remove <channel> [chat_id] - Unsubscribe\n"
        "/list [chat_id] - List subscriptions\n"
        "/template <channel> [chat_id] <message> - Set custom notification message\n"
        "  (Variables: {user_name}, {game_name}, {title}, {user_login})"
    )

@dp.message(Command("add"))
@dp.channel_post(Command("add"))
async def cmd_add(message: Message, twitch: Twitch):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /add <channel_name> [chat_id]")
        return
    
    channel = args[1]
    target_chat_id = message.chat.id

    if len(args) >= 3:
        input_id = args[2]
        try:
            target_chat_id = int(input_id)
        except ValueError:
            # Not an integer, try resolving as username (e.g. @channelname)
            try:
                chat = await bot.get_chat(input_id)
                target_chat_id = chat.id
            except Exception as e:
                await message.answer(f"❌ Invalid Chat ID or Username '{input_id}'. Error: {str(e)}")
                return
    
    # PERMISSION CHECK
    if not await check_permissions(message, target_chat_id):
        return

    # Check if channel exists on Twitch
    try:
        user = await first(twitch.get_users(logins=[channel]))
        if not user:
            await message.answer(f"❌ Channel '{channel}' not found on Twitch.")
            return
        
        # Use the correct casing from Twitch
        channel = user.login
    except Exception as e:
        logging.error(f"Error checking channel {channel}: {e}")
        await message.answer("⚠ Error verifying channel existence. Please try again later.")
        return

    if await database.add_subscription(target_chat_id, channel):
        if target_chat_id != message.chat.id:
            await message.answer(f"✅ Subscribed to {channel} in chat {target_chat_id}.")
        else:
            await message.answer(f"✅ Subscribed to {channel}.")
    else:
        if target_chat_id != message.chat.id:
            await message.answer(f"⚠ Chat {target_chat_id} is already subscribed to {channel}.")
        else:
            await message.answer(f"⚠ You are already subscribed to {channel}.")

@dp.message(Command("remove"))
@dp.channel_post(Command("remove"))
async def cmd_remove(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /remove <channel_name> [chat_id]")
        return
    
    channel = args[1]
    target_chat_id = message.chat.id

    if len(args) >= 3:
        input_id = args[2]
        try:
            target_chat_id = int(input_id)
        except ValueError:
            # Not an integer, try resolving as username
            try:
                chat = await bot.get_chat(input_id)
                target_chat_id = chat.id
            except Exception as e:
                await message.answer(f"❌ Invalid Chat ID or Username '{input_id}'. Error: {str(e)}")
                return
    
    # PERMISSION CHECK
    if not await check_permissions(message, target_chat_id):
        return

    await database.remove_subscription(target_chat_id, channel)
    
    response = f"🗑 Unsubscribed from {channel}."
    if target_chat_id != message.chat.id:
        response += f" (Chat ID: {target_chat_id})"
    await message.answer(response)

@dp.message(Command("list"))
@dp.channel_post(Command("list"))
async def cmd_list(message: Message):
    args = message.text.split()
    target_chat_id = message.chat.id

    if len(args) >= 2:
        input_id = args[1]
        try:
            target_chat_id = int(input_id)
        except ValueError:
            # Not an integer, try resolving as username
            try:
                chat = await bot.get_chat(input_id)
                target_chat_id = chat.id
            except Exception as e:
                await message.answer(f"❌ Invalid Chat ID or Username '{input_id}'. Error: {str(e)}")
                return
    
    # PERMISSION CHECK
    if not await check_permissions(message, target_chat_id):
        return

    subs = await database.get_subscriptions_by_chat(target_chat_id)
    
    chat_label = "Your" if target_chat_id == message.chat.id else f"Chat {target_chat_id}"
    
    if not subs:
        await message.answer(f"{chat_label} has no active subscriptions.")
        return
    
    text = f"{chat_label} subscriptions:\n"
    for sub in subs:
        text += f"- {sub['twitch_login']}\n"
    await message.answer(text)

@dp.message(Command("template"))
@dp.channel_post(Command("template"))
async def cmd_template(message: Message):
    # Usage: /template <channel> [chat_id] <new_message_text>
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Usage: /template <channel> [chat_id] <new_message_text>")
        return
    
    channel = args[1]
    target_chat_id = message.chat.id
    template_start_index = 2

    # Check if the second argument is a chat_id (starts with -100, is a number, or starts with @)
    potential_id = args[2]
    is_chat_id = False
    
    if potential_id.startswith("-") or potential_id.isdigit() or potential_id.startswith("@"):
        try:
            # Try to resolve it
            if potential_id.startswith("@"):
                chat = await bot.get_chat(potential_id)
                target_chat_id = chat.id
            else:
                target_chat_id = int(potential_id)
            is_chat_id = True
            template_start_index = 3
        except Exception:
            # Not a chat_id, treat as start of template
            pass

    # Re-parse the full text to get the template exactly (preserving spaces)
    # We split the original text by the number of arguments we've identified
    parts = message.text.split(maxsplit=template_start_index)
    if len(parts) <= template_start_index:
        await message.answer("Usage: /template <channel> [chat_id] <new_message_text>")
        return
        
    new_template = parts[template_start_index].replace('\\n', '\n')
    
    logging.info(f"Command /template: chat={target_chat_id}, channel={channel}, template={new_template}")

    # PERMISSION CHECK
    if not await check_permissions(message, target_chat_id):
        return
    
    if await database.set_template(target_chat_id, channel, new_template):
        await message.answer(f"✅ Template updated for {channel} (Chat: {target_chat_id}).")
    else:
        await message.answer(f"❌ Could not update template. Ensure {channel} is subscribed in chat {target_chat_id}.")
