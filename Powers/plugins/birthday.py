from datetime import date, datetime
from traceback import format_exc
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import CallbackQuery
from pyrogram.types import InlineKeyboardButton as IKB
from pyrogram.types import InlineKeyboardMarkup as IKM
from pyrogram.types import Message
from Powers import BDB_URI, LOGGER
from Powers.bot_class import Gojo
from Powers.database.chats_db import Chats
if BDB_URI:
    from Powers.plugins import bday_cinfo, bday_info
from Powers.utils.custom_filters import command

def give_date(date, form="%d/%m/%Y"):
    return datetime.strptime(date, form).date()

@Gojo.on_message(command("remember"))
async def remember_me(c: Gojo, m: Message):

    if not BDB_URI:
        await m.reply_text("BDB_URI is not configured")
        return

    args = m.text.split()

    if len(args) < 2:
        await m.reply_text(
            "**Usage:**\n"
            "/remember [username/user_id/reply] [DOB]\n\n"
            "Example:\n"
            "/remember 10/05/2002\n"
            "/remember @username 10/05/2002\n"
            "/remember 123456789 10/05/2002"
        )
        return

    # -------- USER DETECT -------- #

    if m.reply_to_message:
        user_id = m.reply_to_message.from_user.id
        DOB = args[1]

    elif len(args) == 3:
        try:
            user = await c.get_users(args[1])
            user_id = user.id
        except:
            await m.reply_text("❌ Invalid username or user id")
            return

        DOB = args[2]

    else:
        user_id = m.from_user.id
        DOB = args[1]

    # -------- DOB CHECK -------- #

    DOB = DOB.split("/")

    if len(DOB) not in [2,3]:
        await m.reply_text("DOB format should be **dd/mm/yyyy** or **dd/mm**")
        return

    try:
        day = int(DOB[0])
        month = int(DOB[1])

        if not 1 <= day <= 31 or not 1 <= month <= 12:
            await m.reply_text("❌ Invalid date")
            return

        if len(DOB) == 3:
            year = int(DOB[2])
            is_year = 1
        else:
            year = 1900
            is_year = 0

    except ValueError:
        await m.reply_text("DOB must contain numbers only")
        return

    DOB = f"{day}/{month}/{year}"

    data = {
        "user_id": user_id,
        "dob": DOB,
        "is_year": is_year
    }

    # -------- DUPLICATE CHECK -------- #

    try:
        if bday_info.find_one({"user_id": user_id}):
            await m.reply_text("⚠️ This user's birthday is already saved in database")
            return
    except Exception as e:
        LOGGER.error(e)
        await m.reply_text(f"Database error\n{e}")
        return

    # -------- INSERT -------- #

    try:
        bday_info.insert_one(data)
        user = await c.get_users(user_id)
        name = user.mention

        await m.reply_text(f"🎉 Birthday saved successfully for {name}")
    except Exception as e:
        LOGGER.error(e)
        await m.reply_text(f"Database error\n{e}")

@Gojo.on_message(command(["removebday","rmbday"]))
async def who_are_you_again(c: Gojo, m: Message):
    if not BDB_URI:
        await m.reply_text("BDB_URI is not configured")
        return
    user = m.from_user.id
    try:
        if bday_info.find_one({"user_id": user}):
            bday_info.delete_one({"user_id": user})
            await m.reply_text("Removed your birthday")
        else:
            await m.reply_text("User is not in my database")
        return
    except Exception as e:
        await m.reply_text(f"Got an error\n{e}")
        return

@Gojo.on_message(command(["nextbdays","nbdays","birthdays","bdays"]))
async def who_is_next(c: Gojo, m: Message):
    if not BDB_URI:
        await m.reply_text("BDB_URI is not configured")
        return
    blist = list(bday_info.find())
    if m.chat.type == ChatType.PRIVATE:
        await m.reply_text("Use it in group")
        return
    curr = datetime.now().date()
    xx = await m.reply_text("📆")
    users = []
    if blist:
        for i in blist:
            if Chats(m.chat.id).user_is_in_chat(i["user_id"]):
                dob = give_date(i["dob"])
                if dob.month >= curr.month:
                    users.append(i)
            if len(users) == 10:
                break
    if not users:
        await xx.delete()
        await m.reply_text("There are no upcoming birthdays of any user in this chat:/\nEither all the birthdays are passed or no user from this chat have registered their birthday")
        return
    txt = "🎊 Upcomming Birthdays Are 🎊\n"
    for i in users:
        try:
            user = await c.get_users(i["user_id"])
            if user.is_deleted:
                bday_info.delete_one({"user_id": i["user_id"]})
                continue
            name = user.full_name
        except:
            name = i["user_id"]
        DOB = give_date(i["dob"])
        dete = date(curr.year, DOB.month, DOB.day)
        leff = (dete - curr).days
        txt += f"{name} : {leff} days left\n"
    txt += "\n\nYou can use /info [user id] to get info about the user"
    await xx.delete()
    await m.reply_text(txt)
    return

@Gojo.on_message(command(["getbday","gbday","mybirthday","mybday"]))
async def cant_recall_it(c: Gojo, m: Message):
    if not BDB_URI:
        await m.reply_text("BDB_URI is not configured")
        return
    user = m.from_user.id
    men = m.from_user.mention
    if m.reply_to_message:
        user = m.reply_to_message.from_user.id
        men = m.reply_to_message.from_user.mention
    try:
        result = bday_info.find_one({"user_id": user})
        if not result:
            if not m.reply_to_message:
                await m.reply_text("You are not registered in my database\nUse `/remember` to register your birth day so I can wish you")
            await m.reply_text("User is not in my database")
            return
    except Exception as e:
        await m.reply_text(f"Got an error\n{e}")
        return
    curr = datetime.now().date()
    u_dob = give_date(result["dob"])
    day = int(result["dob"].split('/')[0])
    suffix = {1:'st',2:'nd',3:'rd'}.get(day%10,'th')
    bday_on = f"{day}{suffix} {u_dob.strftime('%B')}"
    if (u_dob.day,u_dob.month)<(curr.day,curr.month):
        next_b = date(curr.year+1,u_dob.month,u_dob.day)
        days_left = (next_b-curr).days
        txt = f"{men} 's birthday is passed 🫤\nDays left until next one {abs(days_left)}"
        txt += f"\nBirthday on: {bday_on}"
        txt += f"\n\nDate of birth: {result['dob']}"
    elif (u_dob.day,u_dob.month)==(curr.day,curr.month):
        txt = f"Today is {men}'s birthday."
    else:
        u_dobm = date(curr.year,u_dob.month,u_dob.day)
        days_left = (u_dobm-curr).days
        txt = f"User's birthday is coming🥳\nDays left: {abs(days_left)}"
        txt += f"\nBirthday on: {bday_on}"
        txt += f"\n\nDate of birth: {result['dob']}"
    txt += "\n\n**NOTE**:\nDOB may be wrong if user haven't entered his/her birth year"
    await m.reply_text(txt)
    return

@Gojo.on_message(command(["settingbday","sbday"]))
async def chat_birthday_settings(c: Gojo, m: Message):
    if not BDB_URI:
        await m.reply_text("BDB_URI is not configured")
        return
    if m.chat.type == ChatType.PRIVATE:
        await m.reply_text("Use in groups")
        return
    chats = m.chat.id
    c_in = bday_cinfo.find_one({"chat_id": chats})
    kb = IKM([[IKB(f"{'No' if c_in else 'Yes'}",f"switchh_{'no' if c_in else 'yes'}"),IKB("Close","f_close")]])
    await m.reply_text("Do you want to wish members for their birthday in the group?",reply_markup=kb)
    return

@Gojo.on_callback_query(filters.regex(r"^switchh_(yes|no)$"))
async def switch_on_off(c: Gojo, q: CallbackQuery):
    user = (await q.message.chat.get_member(q.from_user.id)).status
    if user not in [ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.OWNER]:
        await q.answer("...")
        return
    data = q.data.split("_")[1]
    chats = q.message.chat.id
    query = {"chat_id":chats}
    if data=="yes":
        bday_cinfo.delete_one(query)
    elif data=="no":
        bday_cinfo.insert_one(query)
    await q.edit_message_text(f"Done! I will {'wish' if data=='yes' else 'not wish'}",reply_markup=IKM([[IKB("Close","f_close")]]))
    return

__PLUGIN__="birthday"

__HELP__="""
• /remember [reply to user] [DOB] : To registers user date of birth in my database. If not replied to user then the DOB givien will be treated as yours
• /nextbdays (/nbdays,/brithdays,/bdays) : Return upcoming birthdays of 10 users
• /removebday (/rmbday) : To remove birthday from database (One can only remove their data from database not of others)
• /settingbday (/sbday) : To configure the settings for wishing and all for the chat
• /getbday (/gbday,/mybirthday,/mybday) [reply to user] : If replied to user get the replied user's birthday else returns your birthday
DOB should be in format of dd/mm/yyyy
Year is optional it is not necessary to pass it
"""
