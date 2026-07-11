from datetime import datetime, timedelta
from re import escape as re_escape
from time import time
from traceback import format_exc

from pyrogram import filters
from pyrogram.errors import ChatAdminRequired, RPCError, UserAdminInvalid
from pyrogram.types import ChatPermissions, Message

from Powers import LOGGER, MESSAGE_DUMP
from Powers.bot_class import Gojo
from Powers.database.antispam_db import ANTISPAM_BANNED, GBan
from Powers.database.approve_db import Approve
from Powers.database.blacklist_db import Blacklist
from Powers.database.group_blacklist import BLACKLIST_CHATS
from Powers.database.pins_db import Pins
from Powers.database.warns_db import Warns, WarnSettings
from Powers.supports import get_support_staff
from Powers.utils.caching import ADMIN_CACHE, admin_cache_reload
from Powers.utils.parser import mention_html
from Powers.utils.regex_utils import regex_searcher


gban_db = GBan()


# Anti channel pin
@Gojo.on_message(filters.linked_channel)
async def antichanpin_cleanlinked(c: Gojo, m: Message):
    try:
        msg_id = m.id
        pins_db = Pins(m.chat.id)
        curr = pins_db.get_settings()

        if curr["antichannelpin"]:
            await c.unpin_chat_message(m.chat.id, msg_id)

        if curr["cleanlinked"]:
            await c.delete_messages(m.chat.id, msg_id)

    except ChatAdminRequired:
        await m.reply_text(
            "Disabled antichannelpin as I don't have enough admin rights!"
        )
        pins_db.antichannelpin_off()
        LOGGER.warning(
            f"Disabled antichannelpin in {m.chat.id} as i'm not an admin."
        )

    except Exception as ef:
        LOGGER.error(ef)
        LOGGER.error(format_exc())


# Blacklist watcher
@Gojo.on_message(filters.text & filters.group, group=5)
async def bl_watcher(_, m: Message):

    if not m.from_user:
        return

    bl_db = Blacklist(m.chat.id)

    try:

        async def perform_action_blacklist(m: Message, action: str, trigger: str):

            user = m.from_user
            mention = await mention_html(user.first_name, user.id)

            if action == "kick":
                until = datetime.now() + timedelta(minutes=45)
                await m.chat.ban_member(user.id, until_date=until)

                await m.reply_text(
                    f"Kicked {mention} for sending a blacklisted word!"
                )

            elif action == "ban":
                await m.chat.ban_member(user.id)

                await m.reply_text(
                    f"Banned {mention} for sending a blacklisted word!"
                )

            elif action == "mute":
                await m.chat.restrict_member(
                    user.id,
                    ChatPermissions(),
                )

                await m.reply_text(
                    f"Muted {mention} for sending a blacklisted word!"
                )

            elif action == "warn":

                warns_settings_db = WarnSettings(m.chat.id)
                warns_db = Warns(m.chat.id)

                warn_settings = warns_settings_db.get_warnings_settings()
                warn_reason = bl_db.get_reason()

                _, num = warns_db.warn_user(user.id, warn_reason)

                if num >= warn_settings["warn_limit"]:

                    if warn_settings["warn_mode"] == "kick":
                        await m.chat.ban_member(
                            user.id, until_date=int(time() + 45)
                        )
                        action_done = "kicked"

                    elif warn_settings["warn_mode"] == "ban":
                        await m.chat.ban_member(user.id)
                        action_done = "banned"

                    elif warn_settings["warn_mode"] == "mute":
                        await m.chat.restrict_member(user.id, ChatPermissions())
                        action_done = "muted"

                    await m.reply_text(
                        f"Warnings {num}/{warn_settings['warn_limit']}\n"
                        f"{mention} has been <b>{action_done}!</b>"
                    )
                    return

                await m.reply_text(
                    f"{mention} warned {num}/{warn_settings['warn_limit']}\n"
                    f"Last warn was for:\n<i>{warn_reason.format(trigger)}</i>"
                )

        SUPPORT_STAFF = get_support_staff()

        if m.from_user.id in SUPPORT_STAFF:
            return

        chat_blacklists = bl_db.get_blacklists()

        if not chat_blacklists:
            return

        try:
            admin_ids = {i[0] for i in ADMIN_CACHE[m.chat.id]}

        except KeyError:
            admin_ids = {i[0] for i in await admin_cache_reload(m, "blacklist_watcher")}

        if m.from_user.id in admin_ids:
            return

        app_users = Approve(m.chat.id).list_approved()

        if m.from_user.id in {i[0] for i in app_users}:
            return

        action = bl_db.get_action()

        for trigger in chat_blacklists:

            pattern = r"( |^|[^\w])" + re_escape(trigger) + r"( |$|[^\w])"

            match = await regex_searcher(pattern, m.text.lower())

            if not match:
                continue

            try:
                await perform_action_blacklist(m, action, trigger)
                await m.delete()

            except RPCError as ef:
                LOGGER.error(ef)
                LOGGER.error(format_exc())

            break

    except Exception:
        return


# Global ban watcher
@Gojo.on_message(filters.user(list(ANTISPAM_BANNED)) & filters.group, group=5)
async def gban_watcher(c: Gojo, m: Message):

    from Powers import SUPPORT_GROUP

    if not m.from_user:
        return

    try:
        banned = gban_db.check_gban(m.from_user.id)

    except Exception as ef:
        LOGGER.error(ef)
        LOGGER.error(format_exc())
        return

    if banned:

        try:
            await m.chat.ban_member(m.from_user.id)

            await m.delete()

            user_gbanned = await mention_html(
                m.from_user.first_name, m.from_user.id
            )

            await m.reply_text(
                f"This user ({user_gbanned}) has been banned globally!\n\n"
                f"To get unbanned, appeal at @{SUPPORT_GROUP}"
            )

        except (ChatAdminRequired, UserAdminInvalid):
            pass

        except RPCError as ef:

            await c.send_message(
                MESSAGE_DUMP,
                text=f"""<b>Gban Watcher Error!</b>
<b>Chat:</b> <code>{m.chat.id}</code>
<b>Error:</b> <code>{ef}</code>""",
            )


# Blacklisted chats watcher
@Gojo.on_message(filters.chat(BLACKLIST_CHATS))
async def bl_chats_watcher(c: Gojo, m: Message):

    from Powers import SUPPORT_GROUP

    await c.send_message(
        m.chat.id,
        "This is a blacklisted group!\n"
        f"For Support, Join @{SUPPORT_GROUP}\n"
        "Now, I'm leaving!",
    )

    await c.leave_chat(m.chat.id)
