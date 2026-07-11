import asyncio
import os
from traceback import format_exc

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton as IKB,
    InlineKeyboardMarkup as IKM,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from Powers import RMBG, genius_lyrics, is_rmbg, LOGGER
from Powers.utils.custom_filters import command
from Powers.utils.http_helper import *
from Powers.utils.sticker_help import toimage
from Powers.utils.web_helpers import *
from Powers.utils.web_scrapper import INSTAGRAM


songs = {}


@Gojo.on_callback_query(filters.regex("^lyrics_"))
async def lyrics_for_song(c: Gojo, q: CallbackQuery):
    data = q.data.split("_")[1].split(":")
    song_name = data[0]

    try:
        artist = data[1]
    except IndexError:
        artist = None

    try:
        if artist:
            song = genius_lyrics.search_song(song_name, artist)
        else:
            song = genius_lyrics.search_song(song_name)
            artist = song.artist if song else None

        if not song or not song.lyrics:
            return await q.answer("No lyrics found", True)

        header = f"{song_name.capitalize()} by {artist}"
        reply = song.lyrics.split("\n", 1)[1]

        if len(reply) >= 4096:
            part = reply[:4080]

            if artist:
                songs.setdefault(song_name, {})[artist] = reply
                art = f"_{artist}"
            else:
                songs[song_name] = reply
                art = ""

            kb = IKM(
                [
                    [IKB("Next", callback_data=f"lyrics_next_{song_name}{art}")],
                    [IKB("Close", callback_data="f_close")],
                ]
            )
        else:
            part = reply
            kb = IKM([[IKB("Close", callback_data="f_close")]])

        text = f"{header}\n{part}"

        await q.message.reply_to_message.reply_text(text, reply_markup=kb)
        await q.message.delete()

    except Exception as e:
        await q.answer("Error fetching lyrics", True)
        LOGGER.error(e)


@Gojo.on_callback_query(filters.regex("^lyrics_next_") | filters.regex("^lyrics_prev_"))
async def lyrics_for_song_next(c: Gojo, q: CallbackQuery):
    data = q.data.split("_")

    action = data[1]
    song = data[2]

    try:
        artist = data[3]
        art = f"_{artist}"
        header = f"{song.capitalize()} by {artist}"
    except IndexError:
        artist = None
        art = ""
        header = song.capitalize()

    try:
        lyrics = songs[song][artist] if artist else songs[song]
    except KeyError:
        try:
            if artist:
                song_obj = genius_lyrics.search_song(song, artist)
            else:
                song_obj = genius_lyrics.search_song(song)

            lyrics = song_obj.lyrics
        except Exception:
            return await q.answer("Lyrics not found", True)

    if action == "next":
        part = lyrics[4080:8160]
    else:
        part = lyrics[:4080]

    text = f"{header}\n{part}"

    kb = IKM(
        [
            [IKB("Next", callback_data=f"lyrics_prev_{song}{art}")],
            [IKB("Close", callback_data="f_close")],
        ]
    )

    await q.edit_message_text(text, reply_markup=kb)


@Gojo.on_message(command(["removebackground", "removebg", "rmbg"]))
async def remove_background(c: Gojo, m: Message):

    if not is_rmbg:
        return await m.reply_text("Remove.bg API missing")

    reply = m.reply_to_message

    if not reply:
        return await m.reply_text("Reply to image/sticker")

    if not (
        reply.photo
        or (reply.document and reply.document.mime_type.split("/")[0] == "image")
        or reply.sticker
    ):
        return await m.reply_text("Reply to image/sticker")

    if reply.sticker and (reply.sticker.is_video or reply.sticker.is_animated):
        return await m.reply_text("Animated stickers not supported")

    msg = await m.reply_text("Processing...")

    URL = "https://api.remove.bg/v1.0/removebg"

    if reply.sticker:
        filee = await reply.download()
        file = toimage(filee)
    else:
        file = await reply.download()

    finfo = {"image_file": open(file, "rb")}
    data = {"size": "auto"}
    headers = {"X-Api-Key": RMBG}

    result = resp_post(URL, files=finfo, data=data, headers=headers)

    await msg.delete()

    if result.status_code != 200:
        os.remove(file)
        return await m.reply_text(f"Error: {result.text}")

    output = "./downloads/no-bg.png"

    with open(output, "wb") as f:
        f.write(result.content)

    await m.reply_photo(output)

    try:
        os.remove(file)
        os.remove(output)
    except:
        pass


@Gojo.on_message(command(["song", "yta"]))
async def song_down_up(c: Gojo, m: Message):

    try:
        query = m.text.split(None, 1)[1]
    except:
        return await m.reply_text("Usage: /song <name/link>")

    video_id = get_video_id(query)
    query = video_id or query

    msg = await m.reply_text("Downloading...")

    try:
        await youtube_downloader(c, m, query, "a")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"Error\n{e}")
        LOGGER.error(format_exc())


@Gojo.on_message(command(["vsong", "ytv"]))
async def video_down_up(c: Gojo, m: Message):

    try:
        query = m.text.split(None, 1)[1]
    except:
        return await m.reply_text("Usage: /vsong <name/link>")

    video_id = get_video_id(query)
    query = video_id or query

    msg = await m.reply_text("Downloading...")

    try:
        await youtube_downloader(c, m, query, "v")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"Error\n{e}")
        LOGGER.error(format_exc())


@Gojo.on_message(command(["ig", "instagram", "insta"]))
async def download_instareels(c: Gojo, m: Message):

    if len(m.command) < 2:
        return await m.reply_text("Give instagram link")

    reel = m.command[1]

    insta = INSTAGRAM(reel)

    if not insta.is_correct_url():
        return await m.reply_text("Invalid instagram link")

    msg = await m.reply_text("Fetching data...")

    content = insta.get_media()

    if content["message"] != "success":
        await msg.delete()
        return await m.reply_text(content["message"])

    try:
        medias = content["content"]["mediaUrls"]

        await msg.edit_text("Uploading...")

        media_group = []

        for media in medias:
            if media["type"] == "image":
                media_group.append(InputMediaPhoto(media["url"]))
            else:
                media_group.append(InputMediaVideo(media["url"]))

        await m.reply_media_group(media_group)

        await msg.delete()

    except:
        await msg.delete()
        await m.reply_text("Failed to fetch media")


__PLUGIN__ = "web support"

__HELP__ = """
• /rmbg : Remove image background
• /song : Download youtube audio
• /vsong : Download youtube video
• /ig : Download instagram reel


**Bot will not download any song or video having duration greater than 10 minutes (to reduce the load on bot's server)**
"""
