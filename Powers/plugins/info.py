from pyrogram.types import LinkPreviewOptions
import os
from asyncio import sleep
from datetime import datetime
from traceback import format_exc

from pyrogram import enums
from pyrogram.errors import EntityBoundsInvalid, MediaCaptionTooLong, RPCError
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.users import GetFullUser
from pyrogram.raw.types import Channel, UserFull, users
from pyrogram.types import Message

from Powers import BDB_URI, LOGGER, OWNER_ID
from Powers.bot_class import Gojo
from Powers.database.antispam_db import GBan
from Powers.database.approve_db import Approve
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import command
from Powers.utils.extract_user import extract_user

gban_db = GBan()

if BDB_URI:
    from Powers.plugins import bday_info

async def count(c: Gojo, chat):
    try:
        administrator = []
        async for admin in c.get_chat_members(
                chat_id=chat, filter=enums.ChatMembersFilter.ADMINISTRATORS
        ):
            administrator.append(admin)
        total_admin = administrator
        bot = []
        async for tbot in c.get_chat_members(
                chat_id=chat, filter=enums.ChatMembersFilter.BOTS
        ):
            bot.append(tbot)

        total_bot = bot
        bot_admin = 0
        ban = []
        async for banned in c.get_chat_members(
                chat, filter=enums.ChatMembersFilter.BANNED
        ):
            ban.append(banned)

        total_banned = ban
        for x in total_admin:
            for y in total_bot:
                if x == y:
                    bot_admin += 1
        total_admin = len(total_admin)
        total_bot = len(total_bot)
        total_banned = len(total_banned)
        return total_bot, total_admin, bot_admin, total_banned
    except Exception as e:
        total_bot = total_admin = bot_admin = total_banned = "`Can't fetch because I am not part of the chat.`"

    return total_bot, total_admin, bot_admin, total_banned


async def user_info(c: Gojo, user, already=False):
    user_all: users.UserFull = await c.invoke(
        GetFullUser(
            id=await c.resolve_peer(user)
        )
    )
    user = await c.get_users(user)
    full_user: UserFull = user_all.full_user
    channel: Channel = user_all.chats
    if user.is_deleted:
        return "Deleted account", None

    
    gbanned, reason_gban = gban_db.get_gban(user.id)
    if gbanned:
        gban = True
        reason = reason_gban
    else:
        gban = False
        reason = "User is not gbanned"

    user_id = user.id
    about = full_user.about
    SUPPORT_STAFF = get_support_staff()
    username = user.username
    full_name = user.full_name
    dc_id = user.dc_id
    vs = getattr(user, "verification_status", None)
    is_verified = vs.is_verified if vs else False
    mention = user.mention
    dob = False
    if dob := full_user.birthday:
        dob = datetime(int(dob.year), int(dob.month), int(dob.day)).strftime("%d %B %Y")
    else:
        if BDB_URI:  
            try:      
                if result := bday_info.find_one({"user_id": user.id}):
                    u_dob = datetime.strptime(result["dob"], "%d/%m/%Y")
                    day = u_dob.day
                    formatted = u_dob.strftime("%B %Y")
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    dob = f"{day}{suffix} {formatted}"
            except:
                pass

    is_restricted = user.is_restricted
    photo_id = user.photo.big_file_id if user.photo else None
    is_support = user_id in SUPPORT_STAFF
    if user_id == c.me.id:
        is_support = "A person is a great support to himself"
    omp = "Hmmm.......Who is that again?"
    if is_support or user_id == c.me.id:
        if user_id in get_support_staff("dev"):
            omp = "Dev"
        elif user_id in get_support_staff("sudo"):
            omp = "Sudoer"
        elif user_id in get_support_staff("whitelist"):
            omp = "Whitelist"
        elif user_id == c.me.id:
            omp = "I am the targeted user"
        elif user_id == OWNER_ID:
            omp = "Owner of the bot"
        if user_id in get_support_staff("dev") and user_id == OWNER_ID:
            omp = "Dev and Owner"
    vs = getattr(user, "verification_status", None)
    is_scam = vs.is_scam if vs else False
    is_fake = vs.is_fake if vs else False
    is_bot = user.is_bot
    status = user.status
    last_date = "Unable to fetch"
    if is_bot is True:
        last_date = "Targeted user is a bot"
    if status == enums.UserStatus.RECENTLY:
        last_date = "User was seen recently"
    if status == enums.UserStatus.LAST_WEEK:
        last_date = "User was seen last week"
    if status == enums.UserStatus.LAST_MONTH:
        last_date = "User was seen last month"
    if status == enums.UserStatus.LONG_AGO:
        last_date = "User was seen long ago or may be I am blocked by the user  :("
    if status == enums.UserStatus.ONLINE:
        last_date = "User is online"
    if status == enums.UserStatus.OFFLINE:
        try:
            last_date = user.last_online_date.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            last_date = "User is offline"

    caption = f"""
<b><i><u>⚡️ Extracted User info From Telegram ⚡️</b></i></u>

<b>🆔 User ID</b>: <code>{user_id}</code>
<b>🫵 Mention</b>: {mention}
<b>🗣 Full Name</b>: <code>{full_name}</code>
<b>🔍 Username</b>: {("@" + username) if username else "NA"}
<b>✍️ Bio</b>: `{about}`\n"""
    if dob:
        caption += f"<b>🎂 Birthday</b>: {dob}\n<b>🧑‍💻 Support</b>: {is_support}\n"
    else:
        caption += f"<b>🧑‍💻 Support</b>: {is_support}\n"
    if is_support:
        caption += f"<b>🥷 Support user type</b>: <code>{omp}</code>\n<b>💣 Gbanned</b>: {gban}\n"
    else:
        caption += f"<b>💣 Gbanned</b>: {gban}\n"

    if gban:
        caption += f"<b>☠️ Gban reason</b>: <code>{reason}</code>"
    caption += f"""<b>🌐 DC ID</b>: {dc_id}
<b>✋ RESTRICTED</b>: {is_restricted}
<b>✅ VERIFIED</b>: {is_verified}
<b>❌ FAKE</b> : {is_fake}
<b>⚠️ SCAM</b> : {is_scam}
<b>🤖 BOT</b>: {is_bot}
<b>👀 Last seen</b>: <code>{last_date}</code>
"""

    return caption, photo_id


async def chat_info(c: Gojo, chat, already=False):
    u_name = False
    if not already:
        try:
            chat = await c.get_chat(chat)
            try:
                chat_r = (await c.resolve_peer(chat.id))
                ll = await c.invoke(
                    GetFullChannel(
                        channel=chat_r
                    )
                )
                u_name = ll.chats[0].usernames
            except Exception:
                pass
        except Exception:
            try:
                chat_r = await c.resolve_peer(chat)
                chat = await c.get_chat(chat_r.channel_id)
                try:
                    ll = await c.invoke(
                        GetFullChannel(
                            channel=chat_r
                        )
                    )
                    u_name = ll.chats[0].usernames
                except Exception:
                    pass
            except KeyError as e:
                caption = f"Failed to find the chat due to\n{e}"
                return caption, None
    chat_id = chat.id
    username = " ".join([f"@{i.username}" for i in u_name]) if u_name else chat.username
    total_bot, total_admin, total_bot_admin, total_banned = await count(c, chat.id)
    title = chat.title
    type_ = str(chat.type).split(".")[1]
    vs = getattr(chat, "verification_status", None)
    is_scam = vs.is_scam if vs else False
    is_fake = vs.is_fake if vs else False
    description = chat.description
    members = chat.members_count
    is_restricted = chat.is_restricted
    dc_id = chat.dc_id
    photo_id = chat.photo.big_file_id if chat.photo else None
    can_save = chat.has_protected_content
    linked_chat = chat.linked_chat

    caption = f"""
🔰 <b>CHAT INFO</b> 🔰

<b>🆔 ID</b>: <code>{chat_id}</code>
<b>🚀 Chat Title</b>: {title}
<b>✨ Chat Type</b>: {type_}
<b>🌐 DataCentre ID</b>: {dc_id}
<b>🔍 Username</b>: {f"@{username}" if username else "NA"}
<b>⚜️ Administrators</b>: {total_admin}
<b>🤖 Bots</b>: {total_bot}
<b>🚫 Banned</b>: {total_banned}
<b>⚜️ Admin 🤖 Bots</b>: {total_bot_admin}
<b>⁉️ Scam</b>: {is_scam}
<b>❌ Fake</b>: {is_fake}
<b>✋ Restricted</b>: {is_restricted}
<b>👨🏿‍💻 Description</b>: <code>{description}</code>
<b>👪 Total members</b>: {members}
<b>🚫 Has Protected Content</b>: {can_save}
<b>🔗 Linked Chat</b>: <code>{linked_chat.id if linked_chat else "Not Linked"}</code>

"""

    return caption, photo_id


@Gojo.on_message(command(["info", "whois"]))
async def info_func(c: Gojo, message: Message):
    if message.reply_to_message and message.reply_to_message.sender_chat:
        await message.reply_text("This is not a user, but rather a channel. Use `/chinfo` to fetch its information.")
        return
    try:
        user, _, user_name = await extract_user(c, message)
    except Exception as e:
        await message.reply_text(f"Got Some errors failed to fetch user info\n{e}")
        LOGGER.error(e)
        LOGGER.error(format_exc())
        return

    m = await message.reply_text(
        f"Fetching {f'@{user_name}' if user_name else 'user'} info from telegram's database..."
    )

    try:
        info_caption, photo_id = await user_info(c, user)

    except Exception as e:
        LOGGER.error(e)
        LOGGER.error(format_exc())
        return await m.edit(str(e))
    

    status = False
    if m.from_user and (m.chat.id != m.from_user.id):
        try:
            member = await m.chat.get_member(user)
            if member:
                status = str(member.status.value).capitalize()
        except:
            pass
        if not status or status == "Member":
            approved_users = Approve(m.chat.id).check_approve(user)
            if Approve(m.chat.id).check_approve(user):
                status = "Member, Approved"

    if status:
        info_caption += f"<b>👥 Status </b>: {status}"

    if not photo_id:
        await m.delete()
        await sleep(2)
        return await message.reply_text(info_caption, link_preview_options=LinkPreviewOptions(is_disabled=True))
    photo = await c.download_media(photo_id)

    await m.delete()
    await sleep(2)
    try:
        await message.reply_photo(photo, caption=info_caption)
    except MediaCaptionTooLong:
        x = await message.reply_photo(photo)
        try:
            await x.reply_text(info_caption)
        except EntityBoundsInvalid:
            await x.delete()
            await message.reply_text(info_caption)
        except RPCError as rpc:
            await message.reply_text(rpc)
            LOGGER.error(rpc)
            LOGGER.error(format_exc())
    except Exception as e:
        if e == "User not found ! Error: 'InputPeerChannel' object has no attribute 'user_id'":
            await m.reply_text(
                "Looks like you are trying to fetch info of a chat not an user. In that case please use /chinfo")
            return

        await message.reply_text(text=e)
        LOGGER.error(e)
        LOGGER.error(format_exc())

    os.remove(photo)

    return


@Gojo.on_message(command(["chinfo", "chatinfo", "chat_info"]))
async def chat_info_func(c: Gojo, message: Message):
    splited = message.text.split()
    if len(splited) == 1:
        if message.reply_to_message and message.reply_to_message.sender_chat:
            chat = message.reply_to_message.sender_chat.id
        else:
            chat = message.chat.id

    else:
        chat = splited[1]

    try:
        chat = int(chat)
    except Exception as ef:
        if "invalid literal for int() with base 10:" not in str(ef):
            return await message.reply_text(
                f"Got and exception {ef}\n**Usage:**/chinfo [USERNAME|ID]"
            )

        chat = str(chat)
        if chat.startswith("https://"):
            chat = '@' + chat.split("/")[-1]
    m = await message.reply_text(
        "Fetching chat info of chat from telegram's database....."
    )

    try:
        info_caption, photo_id = await chat_info(c, chat=chat)
        if info_caption.startswith("Failed to find the chat due"):
            await message.reply_text(info_caption)
            return
    except Exception as e:
        await m.delete()
        await sleep(0.5)
        return await message.reply_text(f"**GOT AN ERROR:**\n {e}")
    if not photo_id:
        await m.delete()
        await sleep(2)
        return await message.reply_text(info_caption, link_preview_options=LinkPreviewOptions(is_disabled=True))

    photo = await c.download_media(photo_id)
    await m.delete()
    await sleep(2)
    try:
        await message.reply_photo(photo, caption=info_caption)
    except MediaCaptionTooLong:
        x = await message.reply_photo(photo)
        try:
            await x.reply_text(info_caption)
        except EntityBoundsInvalid:
            await x.delete()
            await message.reply_text(info_caption)
        except RPCError as rpc:
            await message.reply_text(rpc)
            LOGGER.error(rpc)
            LOGGER.error(format_exc())
    except Exception as e:
        await message.reply_text(text=e)
        LOGGER.error(e)
        LOGGER.error(format_exc())

    os.remove(photo)

    return


__PLUGIN__ = "info"
__alt_name__ = [
    "info",
    "chinfo",
]

__HELP__ = """
**Information**

• /info - To get info about the user
• /chinfo - To get info about the chat
"""
