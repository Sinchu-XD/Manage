from traceback import format_exc

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.types import CallbackQuery, ChatJoinRequest
from pyrogram.types import InlineKeyboardButton as ikb
from pyrogram.types import InlineKeyboardMarkup as ikm
from pyrogram.types import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.database.autojoin_db import AUTOJOIN
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import admin_filter, auto_join_filter, command


@Gojo.on_message(command(["joinreq"]) & admin_filter)
async def accept_join_requests(c: Gojo, m: Message):

    if m.chat.id == m.from_user.id:
        await m.reply_text("Use it in groups")
        return

    split = m.command
    a_j = AUTOJOIN()

    try:
        status = (await m.chat.get_member(c.me.id)).status
        if status != CMS.ADMINISTRATOR:
            await m.reply_text("I should be admin to accept and reject join requests")
            return
    except Exception as ef:
        await m.reply_text(
            f"Some error occured, report it using `/bug`\n<b>Error:</b> <code>{ef}</code>"
        )
        LOGGER.error(ef)
        LOGGER.error(format_exc())
        return

    if len(split) == 1:
        txt = "**USAGE**\n/joinreq [on | off]"
    else:
        yes_no = split[1].lower()

        if yes_no == "on":

            a_j.add_autojoin(m.chat.id)

            txt = (
                "Now I will approve all join requests of this chat.\n"
                "If you want manual approval use:\n"
                "/joinreqmode [manual | auto]"
            )

        elif yes_no == "off":

            a_j.remove_autojoin(m.chat.id)

            txt = (
                "Now I will neither auto approve join request nor notify admins."
            )

        else:
            txt = "**USAGE**\n/joinreq [on | off]"

    await m.reply_text(txt)


@Gojo.on_message(command("joinreqmode") & admin_filter)
async def join_request_mode(c: Gojo, m: Message):

    if m.chat.id == m.from_user.id:
        await m.reply_text("Use it in groups")
        return

    usage = (
        "**USAGE**\n"
        "/joinreqmode [auto | manual]\n"
        "auto: auto approve joins\n"
        "manual: notify admins"
    )

    split = m.command
    a_j = AUTOJOIN()

    if len(split) == 1:
        await m.reply_text(usage)
        return

    mode = split[1].lower()

    if mode not in ["auto", "manual"]:
        await m.reply_text(usage)
        return

    a_j.update_join_type(m.chat.id, mode)

    await m.reply_text("Changed join request mode.")


@Gojo.on_chat_join_request(auto_join_filter)
async def join_request_handler(c: Gojo, j: ChatJoinRequest):

    user = j.from_user.id
    userr = j.from_user
    chat = j.chat.id

    aj = AUTOJOIN()
    join_type = aj.get_autojoin(chat)

    SUPPORT_STAFF = get_support_staff()

    if not join_type:
        return

    if join_type == "auto" or user in SUPPORT_STAFF:

        try:
            await c.approve_chat_join_request(chat, user)

            await c.send_message(
                chat,
                f"Accepted join request of {userr.mention}",
            )

        except Exception as ef:

            await c.send_message(
                chat,
                f"Error approving join request\n<code>{ef}</code>",
            )

            LOGGER.error(ef)
            LOGGER.error(format_exc())

        return

    if join_type == "manual":

        txt = "New join request received\n\n"
        txt += f"Name: {userr.full_name}\n"
        txt += f"Mention: {userr.mention}\n"
        txt += f"User ID: {user}\n"

        vs = getattr(userr, "verification_status", None)
        is_scam = vs.is_scam if vs else False

        txt += f"Scam: {'True' if is_scam else 'False'}\n"

        if userr.username:
            txt += f"Username: @{userr.username}\n"

        kb = [
            [
                ikb("Accept", f"accept_joinreq_uest_{user}"),
                ikb("Decline", f"decline_joinreq_uest_{user}")
            ]
        ]

        await c.send_message(chat, txt, reply_markup=ikm(kb))


@Gojo.on_callback_query(
    filters.regex("^accept_joinreq_uest_") | filters.regex("^decline_joinreq_uest_")
)
async def accept_decline_request(c: Gojo, q: CallbackQuery):

    user_id = q.from_user.id
    chat = q.message.chat.id

    try:
        user_status = (await q.message.chat.get_member(user_id)).status

        if user_status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
            await q.answer(
                "You're not even an admin!",
                show_alert=True,
            )
            return

    except Exception:
        await q.answer("Unknown error occurred.")
        return

    split = q.data.split("_")
    user = int(split[-1])
    action = split[0]

    try:
        userr = await c.get_users(user)
    except Exception:
        userr = None

    if action == "accept":

        try:
            await c.approve_chat_join_request(chat, user)

            text = f"Accepted join request of {userr.mention if userr else user}"

            await q.answer(text, True)
            await q.edit_message_text(text)

        except Exception as ef:

            await c.send_message(
                chat,
                f"Error approving join request\n<code>{ef}</code>",
            )

            LOGGER.error(ef)
            LOGGER.error(format_exc())

    elif action == "decline":

        try:
            await c.decline_chat_join_request(chat, user)

            text = f"Declined join request of {userr.mention if userr else user}"

            await q.answer("Declined", True)
            await q.edit_message_text(text)

        except Exception as ef:

            await c.send_message(
                chat,
                f"Error declining join request\n<code>{ef}</code>",
            )

            LOGGER.error(ef)
            LOGGER.error(format_exc())


__PLUGIN__ = "auto join"

__alt_name__ = ["join_request"]

__HELP__ = """
Auto Join Request

Admin commands:
/joinreq [on | off] - Enable or disable auto join approve
/joinreqmode [auto | manual] - Auto approve or manual approve
"""
