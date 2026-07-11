from datetime import datetime
from io import BytesIO
from traceback import format_exc

from pyrogram import filters
from pyrogram.errors import MessageTooLong
from pyrogram.types import Message

from Powers import LOGGER, MESSAGE_DUMP
from Powers.bot_class import Gojo
from Powers.database.antispam_db import GBan
from Powers.database.users_db import Users
from Powers.database.chats_db import Chats
from Powers.supports import get_support_staff
from Powers.utils.clean_file import remove_markdown_and_html
from Powers.utils.custom_filters import command
from Powers.utils.extract_user import extract_user
from Powers.utils.parser import mention_html

db = GBan()

# ==============================
# 🔥 GLOBAL BAN COMMAND
# ==============================

@Gojo.on_message(command(["gban", "globalban"], sudo_cmd=True))
async def gban(c: Gojo, m: Message):

    if len(m.text.split()) == 1:
        return await m.reply_text(
            "<b>Usage:</b> <code>/gban user_id/reply reason</code>"
        )

    user_id, user_first_name, _ = await extract_user(c, m)

    args = m.text.split(None, 1)
    gban_reason = args[1] if len(args) > 1 else "No Reason"

    SUPPORT_STAFF = get_support_staff()

    if user_id in SUPPORT_STAFF:
        return await m.reply_text("This user is part of support staff!")

    if user_id == c.me.id:
        return await m.reply_text("You can't use this command on me.")

    if db.check_gban(user_id):
        db.update_gban_reason(user_id, gban_reason)
        return await m.reply_text(
            f"Updated reason: <code>{gban_reason}</code>"
        )

    db.add_gban(user_id, gban_reason, m.from_user.id)

    await m.reply_text(
        f"⚡ <b>{user_first_name}</b> has been globally banned!"
    )

    # Logging
    date = datetime.utcnow().strftime("%H:%M - %d-%m-%Y")

    log_msg = f"""
#GBAN
<b>Chat:</b> {m.chat.id}
<b>Admin:</b> {await mention_html(m.from_user.first_name, m.from_user.id)}
<b>User:</b> {await mention_html(user_first_name, user_id)}
<b>ID:</b> {user_id}
<b>Reason:</b> {gban_reason}
<b>Time:</b> {date}
"""

    await c.send_message(MESSAGE_DUMP, log_msg)

    # ⚡ GLOBAL BAN EXECUTION
    progress = await m.reply_text("⚡ Applying global ban across all chats...")

    all_chats = Chats.list_chats_full()

    success = 0
    failed = 0
    banned_chats = []

    for chat in all_chats:
        try:
            await c.ban_chat_member(chat["_id"], user_id)

            success += 1

            # 👇 Store chat name
            chat_name = chat.get("chat_name") or str(chat["_id"])
            banned_chats.append(chat_name)

        except Exception:
            failed += 1

    # 👇 Create list text
    chat_list_text = "\n".join([f"• {name}" for name in banned_chats[:20]])

    if len(banned_chats) > 20:
        chat_list_text += f"\n\n...and {len(banned_chats) - 20} more"

    final_msg = f"""
✅ <b>GBan Completed!</b>

<b>User:</b> {user_first_name}
<b>Success:</b> {success}
<b>Failed:</b> {failed}

<b>🔨 Banned in Groups:</b>
{chat_list_text if chat_list_text else 'No groups'}
"""

    try:
        await progress.edit_text(final_msg)
    except:
        await m.reply_text(final_msg)
# ==============================
# 🔥 GLOBAL UNBAN
# ==============================

@Gojo.on_message(command(["ungban", "unglobalban"], sudo_cmd=True))
async def ungban(c: Gojo, m: Message):

    if len(m.text.split()) == 1:
        return await m.reply_text("Provide user id or reply!")

    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except:
        return await m.reply_text("User not found.")

    SUPPORT_STAFF = get_support_staff()

    if user_id in SUPPORT_STAFF:
        return await m.reply_text("This user is support staff!")

    if user_id == c.me.id:
        return await m.reply_text("You can't unban me.")

    if not db.check_gban(user_id):
        return await m.reply_text("User is not gbanned!")

    db.remove_gban(user_id)

    await m.reply_text(f"✅ {user_first_name} has been ungbanned.")

    # Logging
    time = datetime.utcnow().strftime("%H:%M - %d-%m-%Y")

    log_msg = f"""
#UNGBAN
<b>Chat:</b> {m.chat.id}
<b>Admin:</b> {await mention_html(m.from_user.first_name, m.from_user.id)}
<b>User:</b> {await mention_html(user_first_name, user_id)}
<b>ID:</b> {user_id}
<b>Time:</b> {time}
"""

    await c.send_message(MESSAGE_DUMP, log_msg)

    # ⚡ GLOBAL UNBAN EXECUTION
    all_chats = Chats.list_chats_full()

    for chat in all_chats:
        try:
            await c.unban_chat_member(chat["_id"], user_id)
        except:
            pass


# ==============================
# 🔥 AUTO GBAN CHECK
# ==============================

@Gojo.on_message(filters.new_chat_members)
async def auto_gban(c: Gojo, m: Message):

    for user in m.new_chat_members:
        if db.check_gban(user.id):
            try:
                await c.ban_chat_member(m.chat.id, user.id)
                await m.reply_text(
                    f"🚫 {user.first_name} is globally banned!"
                )
            except:
                pass


# ==============================
# 🔥 COUNT GBANS
# ==============================

@Gojo.on_message(command(["gbanstats", "gbancount"], sudo_cmd=True))
async def gban_count(_, m: Message):

    count = db.count_gbans()
    await m.reply_text(f"📊 Total GBanned Users: <code>{count}</code>")


# ==============================
# 🔥 GBAN LIST
# ==============================

@Gojo.on_message(command(["gbanlist"], sudo_cmd=True))
async def gban_list(_, m: Message):

    banned_users = db.load_from_db()

    if not banned_users:
        return await m.reply_text("No gbanned users found.")

    text = "🚫 <b>Globally Banned Users:</b>\n\n"

    for user in banned_users:

        USER = Users.get_user_info(user["_id"])

        text += f"• <b>{USER['name'] if USER else 'Unknown'}</b> - <code>{user['_id']}</code>\n"

        if user.get("reason"):
            text += f"   └ Reason: {user['reason']}\n"

    try:
        await m.reply_text(text)

    except MessageTooLong:
        with BytesIO(str.encode(await remove_markdown_and_html(text))) as f:
            f.name = "gbanlist.txt"

            await m.reply_document(
                document=f,
                caption="GBan List"
            )


# ==============================
# 📌 HELP
# ==============================

__PLUGIN__ = "global"

__HELP__ = """
<b>Global Ban System</b>

• /gban [user/reply] [reason]
• /ungban [user/reply]
• /gbanstats
• /gbanlist
"""
