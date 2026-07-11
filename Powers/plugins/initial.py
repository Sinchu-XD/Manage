from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.database.approve_db import Approve
from Powers.database.blacklist_db import Blacklist
from Powers.database.chats_db import Chats
from Powers.database.disable_db import Disabling
from Powers.database.filters_db import Filters
from Powers.database.greetings_db import Greetings
from Powers.database.notes_db import Notes, NotesSettings
from Powers.database.pins_db import Pins
from Powers.database.reporting_db import Reporting
from Powers.database.rules_db import Rules
from Powers.database.users_db import Users


@Gojo.on_message(filters.group, group=4)
async def initial_works(_, m: Message):
    chatdb = Chats(m.chat.id)

    try:
        if getattr(m, "migrate_to_chat_id", None) or getattr(m, "migrate_from_chat_id", None):
            new_chat = getattr(m, "migrate_to_chat_id", None) or m.chat.id
            try:
                await migrate_chat(m, new_chat)
            except RPCError as ef:
                LOGGER.error(ef)
                return

        # -----------------------------
        # Reply (normal message, not forwarded)
        # -----------------------------
        elif m.reply_to_message and not getattr(m, "forward_origin", None):
            user = m.reply_to_message.from_user
            if user:
                chatdb.update_chat(m.chat.title, user.id)
                Users(user.id).update_user(
                    f"{user.first_name} {user.last_name}"
                    if user.last_name
                    else user.first_name,
                    user.username,
                )

        # -----------------------------
        # Forwarded message (not reply)
        # -----------------------------
        elif getattr(m, "forward_origin", None) and getattr(m.forward_origin, "sender_user", None) and not m.reply_to_message:
            fwd_user = m.forward_origin.sender_user

            chatdb.update_chat(m.chat.title, fwd_user.id)
            Users(fwd_user.id).update_user(
                f"{fwd_user.first_name} {fwd_user.last_name}"
                if fwd_user.last_name
                else fwd_user.first_name,
                fwd_user.username,
            )

        # -----------------------------
        # Reply to forwarded message
        # -----------------------------
        elif (
            m.reply_to_message
            and getattr(m.reply_to_message, "forward_origin", None)
            and getattr(m.reply_to_message.forward_origin, "sender_user", None)
        ):
            fwd_user = m.reply_to_message.forward_origin.sender_user

            chatdb.update_chat(m.chat.title, fwd_user.id)
            Users(fwd_user.id).update_user(
                f"{fwd_user.first_name} {fwd_user.last_name}"
                if fwd_user.last_name
                else fwd_user.first_name,
                fwd_user.username,
            )

        # -----------------------------
        # Normal message
        # -----------------------------
        else:
            user = m.from_user
            if user:
                chatdb.update_chat(m.chat.title, user.id)
                Users(user.id).update_user(
                    f"{user.first_name} {user.last_name}"
                    if user.last_name
                    else user.first_name,
                    user.username,
                )

    except AttributeError:
        pass  # Skip attribute errors safely

    return


async def migrate_chat(m: Message, new_chat: int) -> None:
    LOGGER.info(f"Migrating from {m.chat.id} to {new_chat}...")
    notedb = Notes()
    gdb = Greetings(m.chat.id)
    ruledb = Rules(m.chat.id)
    userdb = Users(m.chat.id)
    chatdb = Chats(m.chat.id)
    bldb = Blacklist(m.chat.id)
    approvedb = Approve(m.chat.id)
    reportdb = Reporting(m.chat.id)
    notes_settings = NotesSettings()
    pins_db = Pins(m.chat.id)
    fldb = Filters()
    disabl = Disabling(m.chat.id)
    disabl.migrate_chat(new_chat)
    gdb.migrate_chat(new_chat)
    chatdb.migrate_chat(new_chat)
    userdb.migrate_chat(new_chat)
    ruledb.migrate_chat(new_chat)
    bldb.migrate_chat(new_chat)
    notedb.migrate_chat(m.chat.id, new_chat)
    approvedb.migrate_chat(new_chat)
    reportdb.migrate_chat(new_chat)
    notes_settings.migrate_chat(m.chat.id, new_chat)
    pins_db.migrate_chat(new_chat)
    fldb.migrate_chat(m.chat.id, new_chat)
    LOGGER.info(f"Successfully migrated from {m.chat.id} to {new_chat}!")
