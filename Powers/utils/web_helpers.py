import math
import os
import time
from traceback import format_exc
import asyncio
from pyrogram.types import InlineKeyboardButton as IKB
from pyrogram.types import InlineKeyboardMarkup as IKM
from pyrogram.types import Message
from pytube import YouTube, extract
from youtubesearchpython.__future__ import VideosSearch
from yt_dlp import YoutubeDL

from Powers import youtube_dir
from Powers.bot_class import LOGGER, Gojo
from Powers.utils.sticker_help import resize_file_to_sticker_size
from Powers.utils.web_scrapper import SCRAP_DATA

backUP = "https://artfiles.alphacoders.com/160/160160.jpeg"


def readable_time(seconds: int) -> str:

    count = 0
    out_time = ""
    time_list = []
    time_suffix_list = ["secs", "mins", "hrs", "days"]

    while count < 4:

        count += 1

        remainder, result = (
            divmod(seconds, 60)
            if count < 3
            else divmod(seconds, 24)
        )

        if seconds == 0 and remainder == 0:
            break

        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]

    if len(time_list) == 4:
        out_time += f"{time_list.pop()}, "

    time_list.reverse()

    out_time += " ".join(time_list)

    return out_time or "0 secs"


def humanbytes(size: int):

    if not size:
        return ""

    power = 2 ** 10
    number = 0
    dict_power_n = {0: " ", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}

    while size >= power and number < 4:
        size /= power
        number += 1

    return f"{round(size, 2)} {dict_power_n[number]}B"


async def progress(current: int, total: int, message: Message, start: float, process: str):

    now = time.time()

    diff = now - start

    if diff == 0:
        return

    if round(diff % 10.00) == 0 or current == total:

        percentage = current * 100 / total

        speed = current / diff

        if speed == 0:
            return

        elapsed_time = round(diff) * 1000

        complete_time = round((total - current) / speed) * 1000

        estimated_total_time = elapsed_time + complete_time

        progress_str = "**[{0}{1}] : {2}%\n**".format(
            "".join(["●" for _ in range(math.floor(percentage / 10))]),
            "".join(["○" for _ in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2),
        )

        msg = (
                progress_str
                + "__{0}__ **𝗈𝖿** __{1}__\n**𝖲𝗉𝖾𝖾𝖽:** __{2}/s__\n**𝖤𝖳𝖠:** __{3}__".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            readable_time(estimated_total_time / 1000),
        )
        )

        await message.edit_text(f"**{process} ...**\n\n{msg}")


async def get_file_size(file: Message):

    size = None

    if file.photo:
        size = file.photo.file_size

    elif file.document:
        size = file.document.file_size

    elif file.video:
        size = file.video.file_size

    elif file.audio:
        size = file.audio.file_size

    elif file.sticker:
        size = file.sticker.file_size

    elif file.animation:
        size = file.animation.file_size

    elif file.voice:
        size = file.voice.file_size

    elif file.video_note:
        size = file.video_note.file_size

    if not size:
        return "0 kb"

    size = size / 1024

    if size <= 1024:
        return f"{round(size)} kb"

    size = size / 1024

    if size <= 1024:
        return f"{round(size)} mb"

    size = size / 1024

    return f"{round(size)} gb"


def get_video_id(url):

    try:

        _id = extract.video_id(url)

        return _id or None

    except Exception:
        return None


def get_duration_in_sec(dur: str):

    duration = dur.split(":")

    return (
        (int(duration[0]) * 60) + int(duration[1])
        if len(duration) == 2
        else int(duration[0])
    )


async def song_search(query, max_results=1):
    yt_dict = {}

    try:
        data = await VideosSearch(query, limit=max_results).next()
        results = data.get("result", [])

    except Exception as e:
        LOGGER.error(e)
        return {0: str(e)}

    nums = 1

    for i in results:
        duration = i.get("duration")

        # LIVE skip
        if not duration or duration == "LIVE":
            continue

        # duration convert
        durr = duration.split(":")
        total = 0

        try:
            if len(durr) == 3:
                total = int(durr[0]) * 3600 + int(durr[1]) * 60 + int(durr[2])
            elif len(durr) == 2:
                total = int(durr[0]) * 60 + int(durr[1])
        except:
            continue

        # max 10 min filter
        if total <= 600:
            thumbnails = i.get("thumbnails") or []
            thumbnail = thumbnails[0].get("url") if thumbnails else None
            yt_dict[nums] = {
                "link": i.get("url"),
                "title": i.get("title"),
                "views": i.get("views", "0 Views"),
                "channel": "",
                "duration": duration,
                "DURATION": duration,
                "published": "",
                "uploader": (i.get("channel") or {}).get("name", "Unknown"),
                "thumbnail": thumbnail,
            }
            nums += 1

    if not yt_dict:
        return {0: "No suitable results found"}

    return yt_dict

def build_command(url: str, is_audio: bool):
    base = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--cookies", "cookies.txt",
        "--extractor-args", "youtube:player_client=web;player_js_variant=main",
        "-o", "%(title).80s [%(id)s].%(ext)s",
    ]

    if is_audio:
        base += [
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",
        ]
    else:
        base += [
            "-f", "bv*+ba/b",
            "--merge-output-format", "mp4",
        ]

    base.append(url)
    return base

async def youtube_downloader(c, m, query: str, type_: str):
    is_audio = type_ == "a"

    data = await song_search(query, 1)

    if not isinstance(data, dict):
        return await m.reply_text("Search error")

    if err := data.get(0):
        return await m.reply_text(err)

    if not data.get(1):
        return await m.reply_text("No results found")

    info = data[1]
    url = info["link"]

    msg = await m.reply_text("⬇️ Downloading...")

    cmd = build_command(url, is_audio)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        return await msg.edit(stderr.decode()[:4000])

    # ---- find downloaded file ---- #
    files = sorted(
        [f for f in os.listdir(".") if f.endswith(".mp3" if is_audio else ".mp4")],
        key=os.path.getctime,
        reverse=True
    )

    if not files:
        return await msg.edit("Download failed")

    file_path = files[0]

    caption = f"""
⤷ Name: `{info['title']}`
⤷ Duration: `{info['duration']}`
⤷ Views: `{info['views']}`

Downloaded by: @{c.me.username}
"""

    if is_audio:
        await m.reply_audio(file_path, caption=caption)
    else:
        await m.reply_video(file_path, caption=caption)

    await msg.delete()
    os.remove(file_path)
