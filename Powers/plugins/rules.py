from pyrogram.types import LinkPreviewOptions
from pyrogram import filters
from pyrogram.types import CallbackQuery, Message

from Powers.bot_class import Gojo
from Powers.database.rules_db import Rules
from Powers.utils.custom_filters import admin_filter, command
from Powers.utils.kbhelpers import ikb
from Powers.utils.string import build_keyboard, parse_button


@Gojo.on_message(command("rules") & filters.group)
async def get_rules(c: Gojo, m: Message):
    db = Rules(m.chat.id)
    msg_id = m.reply_to_message.id if m.reply_to_message else m.id
    me = await c.get_me()
    rules = db.get_rules()
    if not m.from_user:
        return

    if not rules:
        await m.reply_text(
            text="The Admins for this group have not setup rules! That doesn't mean you can break the DECORUM of this group !",
    
        )
        return

    if db.get_privrules():
        pm_kb = ikb(
            [
                [
                    (
                        "Rules",
                        f"https://t.me/{me.username}?start=rules_{m.chat.id}",
                        "url",
                    ),
                ],
            ],
        )
        await m.reply_text(
            text="Click on the below button to see this group rules!",
    
            reply_markup=pm_kb,
            reply_to_message_id=msg_id,
        )
        return

    formated = rules
    teks, button = await parse_button(formated)
    button = await build_keyboard(button)
    button = ikb(button) if button else None
    chat_title = m.chat.title or "This Chat"
    textt = teks
    await m.reply_text(
        text=f"""The rules for <b>{chat_title} are:</b>
{textt}""",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_to_message_id=msg_id,
        reply_markup=button
    )
    return


@Gojo.on_message(command("setrules") & admin_filter)
async def set_rules(_, m: Message):
    db = Rules(m.chat.id)
    if not m.from_user:
        return

    if m.reply_to_message and m.reply_to_message.text:
        rules = m.reply_to_message.text
    elif (not m.reply_to_message) and len(m.text.split()) >= 2:
        rules = m.text.split(None, 1)[1]
    else:
        return await m.reply_text("Provide some text to set as rules !!")

    if len(rules) > 4090:
        rules = rules[:4090]
        await m.reply_text("Rules are truncated to 4090 characters!")

    db.set_rules(rules)
    await m.reply_text(text="Successfully set rules for this group.")
    return


@Gojo.on_message(
    command(["pmrules", "privaterules"]) & admin_filter,
)
async def priv_rules(_, m: Message):
    db = Rules(m.chat.id)
    if not m.from_user:
        return

    if len(m.text.split()) == 2:
        option = (m.text.split())[1]
        if option in ("on", "yes"):
            db.set_privrules(True)
            msg = f"Private Rules have been turned <b>on</b> for chat <b>{m.chat.title}</b>"
        elif option in ("off", "no"):
            db.set_privrules(False)
            msg = f"Private Rules have been turned <b>off</b> for chat <b>{m.chat.title}</b>"
        else:
            msg = "Option not valid, choose from <code>on</code>, <code>yes</code>, <code>off</code>, <code>no</code>"
        await m.reply_text(msg)
    elif len(m.text.split()) == 1:
        curr_pref = db.get_privrules()
        msg = (
            f"Current Preference for Private rules in this chat is: <b>{curr_pref}</b>"
        )
        await m.reply_text(msg)
    else:
        await m.reply_text(text="Please check help on how to use this this command.")

    return


@Gojo.on_message(command("clearrules") & admin_filter)
async def clear_rules(_, m: Message):
    db = Rules(m.chat.id)
    if not m.from_user:
        return

    rules = db.get_rules()
    if not rules:
        await m.reply_text(
            text="The Admins for this group have not setup rules! That doesn't mean you can break the DECORUM of this group !"
        )
        return

    await m.reply_text(
        text="Are you sure you want to clear rules?",
        reply_markup=ikb(
            [[("⚠️ Confirm", "clear_rules"), ("❌ Cancel", "close_admin")]],
        ),
    )
    return


@Gojo.on_callback_query(filters.regex("^clear_rules$"))
async def clearrules_callback(_, q: CallbackQuery):
    Rules(q.message.chat.id).clear_rules()
    await q.message.edit_text(text="Successfully cleared rules for this group!")
    await q.answer("Rules for the chat have been cleared!", show_alert=True)
    return


__PLUGIN__ = "rules"

__alt_name__ = ["rule"]

__HELP__ = """
**Rules**

Set rules for you chat so that members know what to do and what not to do in your group!

• /rules: get the rules for current chat.

**Admin only:**
• /setrules `<rules>`: Set the rules for this chat, also works as a reply to a message.
• /clearrules: Clear the rules for this chat.
• /privrules `<on/yes/no/off>`: Turns on/off the option to send the rules to PM of user or group.

**Note Format**
    Check /markdownhelp for help related to formatting!
"""
