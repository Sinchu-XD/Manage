from re import compile as compile_re
from re import escape
from shlex import split
from typing import List, Union

from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError, UserNotParticipant
from pyrogram.filters import create
from pyrogram.types import CallbackQuery, ChatJoinRequest, Message

from Powers import OWNER_ID, PREFIX_HANDLER
from Powers.bot_class import Gojo
from Powers.database.afk_db import AFK
from Powers.database.approve_db import Approve
from Powers.database.autojoin_db import AUTOJOIN
from Powers.database.captcha_db import CAPTCHA
from Powers.database.disable_db import Disabling
from Powers.database.flood_db import Floods
from Powers.supports import get_support_staff
from Powers.utils.caching import ADMIN_CACHE, admin_cache_reload


def command(
    commands: Union[str, List[str]],
    case_sensitive: bool = False,
    owner_cmd: bool = False,
    dev_cmd: bool = False,
    sudo_cmd: bool = False,
):

    async def func(flt, c: Gojo, m: Message):

        if not m or not m.chat:
            return False

        if m.edit_date:
            return False

        if m.chat.type == ChatType.CHANNEL:
            return False

        if not m.from_user and not m.sender_chat:
            return False

        if m.forward_origin and (
            getattr(m.forward_origin, "sender_user", None)
            or getattr(m.forward_origin, "chat", None)
        ):
            return False

        if m.from_user:

            if m.from_user.is_bot:
                return False

            if owner_cmd and (m.from_user.id != OWNER_ID):
                return False

            DEV_LEVEL = get_support_staff("dev_level")
            if dev_cmd and (m.from_user.id not in DEV_LEVEL):
                return False

            SUDO_LEVEL = get_support_staff("sudo_level")
            if sudo_cmd and (m.from_user.id not in SUDO_LEVEL):
                return False

        text: str = m.text or m.caption
        if not text:
            return False

        regex = r"^[{prefix}](\w+)(@{bot_name})?(?: |$)(.*)".format(
            prefix="|".join(escape(x) for x in PREFIX_HANDLER),
            bot_name=c.me.username,
        )

        matches = compile_re(regex).search(text)

        if not matches:
            return False

        m.command = [matches.group(1)]

        if matches.group(1) not in flt.commands:
            return False

        if m.chat.type in {ChatType.SUPERGROUP, ChatType.GROUP} and m.from_user:

            try:
                user_status = (await m.chat.get_member(m.from_user.id)).status

            except UserNotParticipant:
                user_status = CMS.ADMINISTRATOR

            except ValueError:
                user_status = CMS.OWNER

            except RPCError:
                return False

            ddb = Disabling(m.chat.id)

            if (
                str(matches.group(1)) in ddb.get_disabled()
                and user_status not in (CMS.OWNER, CMS.ADMINISTRATOR)
                and ddb.get_action() == "del"
            ):
                try:
                    await m.delete()
                except RPCError:
                    return False

        if matches.group(3) == "":
            return True

        try:
            for arg in split(matches.group(3)):
                m.command.append(arg)
        except ValueError:
            pass

        return True

    commands = commands if isinstance(commands, list) else [commands]
    commands = {c if case_sensitive else c.lower() for c in commands}

    return create(
        func,
        "NormalCommandFilter",
        commands=commands,
        case_sensitive=case_sensitive,
    )


async def bot_admin_check_func(_, c: Gojo, m: Message or CallbackQuery):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return False

    if m.sender_chat:
        return True

    try:
        admin_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_group = {i[0] for i in await admin_cache_reload(m, "custom_filter_update")}
    except ValueError as ef:
        if "belongs to a user" in str(ef):
            return True

    if c.me.id in admin_group:
        return True

    await m.reply_text(
        "I am not an admin to recive updates in this group; Mind Promoting?",
    )

    return False


async def admin_check_func(_, __, m: Message or CallbackQuery):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return False

    if m.sender_chat and m.sender_chat.id == m.chat.id:
        return True

    if not m.from_user:
        return False

    try:
        admin_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_group = {i[0] for i in await admin_cache_reload(m, "custom_filter_update")}
    except ValueError as ef:
        if "belongs to a user" in str(ef):
            return True

    if m.from_user.id in admin_group:
        return True

    await m.reply_text(text="You cannot use an admin command!")

    return False


async def owner_check_func(_, __, m: Message or CallbackQuery):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return False

    if not m.from_user:
        return False

    user = await m.chat.get_member(m.from_user.id)

    if user.status == CMS.OWNER:
        return True

    if user.status == CMS.ADMINISTRATOR:
        msg = "You're an admin only, stay in your limits!"
    else:
        msg = "Do you think that you can execute owner commands?"

    await m.reply_text(msg)
    return False


async def restrict_check_func(_, __, m):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or not m.from_user:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return False

    user = await m.chat.get_member(m.from_user.id)

    if user.status in [CMS.ADMINISTRATOR, CMS.OWNER] and user.privileges and user.privileges.can_restrict_members:
        return True

    await m.reply_text(text="You don't have permissions to restrict members!")
    return False


async def promote_check_func(_, __, m):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or not m.from_user:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return False

    user = await m.chat.get_member(m.from_user.id)

    if user.status in [CMS.ADMINISTRATOR, CMS.OWNER] and user.privileges and user.privileges.can_promote_members:
        return True

    await m.reply_text(text="You don't have permission to promote members!")
    return False


async def changeinfo_check_func(_, __, m):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        await m.reply_text("This command is made to be used in groups not in pm!")
        return False

    if m.sender_chat:
        return True

    user = await m.chat.get_member(m.from_user.id)

    if user.status in [CMS.ADMINISTRATOR, CMS.OWNER] and user.privileges and user.privileges.can_change_info:
        return True

    await m.reply_text("You don't have: can_change_info permission!")
    return False


async def can_pin_message_func(_, __, m):

    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        await m.reply_text("This command is made to be used in groups not in pm!")
        return False

    if m.sender_chat:
        return True

    SUDO_LEVEL = get_support_staff("sudo_level")

    if m.from_user and m.from_user.id in SUDO_LEVEL:
        return True

    user = await m.chat.get_member(m.from_user.id)

    if user.status in [CMS.ADMINISTRATOR, CMS.OWNER] and user.privileges and user.privileges.can_pin_messages:
        return True

    await m.reply_text("You don't have: can_pin_messages permission!")
    return False


async def auto_join_check_filter(_, __, j: ChatJoinRequest):

    chat = j.chat.id
    aj = AUTOJOIN()
    join_type = aj.get_autojoin(chat)

    return bool(join_type)


async def afk_check_filter(_, __, m: Message):

    if not m.from_user or m.from_user.is_bot:
        return False

    if m.chat.type == ChatType.PRIVATE:
        return False

    afk = AFK()
    chat = m.chat.id

    if m.reply_to_message and m.reply_to_message.from_user:
        repl_user = m.reply_to_message.from_user.id
        return bool(afk.check_afk(chat, repl_user))

    return bool(afk.check_afk(chat, m.from_user.id))


async def flood_check_filter(_, __, m: Message):

    Flood = Floods()

    if not m.chat or not m.from_user:
        return False

    if m.chat.type == ChatType.PRIVATE:
        return False

    u_id = m.from_user.id
    c_id = m.chat.id

    if not Flood.is_chat(c_id):
        return False

    try:
        admin_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_group = {i[0] for i in await admin_cache_reload(m, "custom_filter_update")}

    app_users = Approve(m.chat.id).list_approved()
    SUDO_LEVEL = get_support_staff("sudo_level")

    if u_id in SUDO_LEVEL:
        return False

    if u_id in admin_group:
        return False

    if u_id in {i[0] for i in app_users}:
        return False

    return True


async def captcha_filt(_, __, m: Message):

    try:
        return CAPTCHA().is_captcha(m.chat.id)
    except Exception:
        return False


captcha_filter = create(captcha_filt)
flood_filter = create(flood_check_filter)
afk_filter = create(afk_check_filter)
auto_join_filter = create(auto_join_check_filter)
admin_filter = create(admin_check_func)
owner_filter = create(owner_check_func)
restrict_filter = create(restrict_check_func)
promote_filter = create(promote_check_func)
bot_admin_filter = create(bot_admin_check_func)
can_change_filter = create(changeinfo_check_func)
can_pin_filter = create(can_pin_message_func)
