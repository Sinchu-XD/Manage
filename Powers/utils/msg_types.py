from enum import IntEnum, unique
from pyrogram.types import Message


@unique
class Types(IntEnum):
    TEXT = 1
    DOCUMENT = 2
    PHOTO = 3
    VIDEO = 4
    STICKER = 5
    AUDIO = 6
    VOICE = 7
    VIDEO_NOTE = 8
    ANIMATION = 9
    ANIMATED_STICKER = 10
    CONTACT = 11


def _raw_text(m: Message):
    if m.text:
        return m.text
    if m.caption:
        return m.caption
    return ""


def _reply_text(m: Message):
    if m.reply_to_message.text:
        return m.reply_to_message.text
    if m.reply_to_message.caption:
        return m.reply_to_message.caption
    return ""


async def get_note_type(m: Message):

    raw_text = _raw_text(m)

    if len(raw_text.split()) <= 1:
        return None, None, None, None

    args = raw_text.split(None, 2)

    note_name = args[1]
    data_type = None
    content = None
    text = None

    if len(args) >= 3:
        text = args[2]
        data_type = Types.TEXT

    elif m.reply_to_message:

        text = _reply_text(m)

        r = m.reply_to_message

        if r.text:
            data_type = Types.TEXT

        elif r.sticker:
            content = r.sticker.file_id
            data_type = Types.STICKER

        elif r.document:
            if r.document.mime_type in ["application/x-bad-tgsticker", "application/x-tgsticker"]:
                data_type = Types.ANIMATED_STICKER
            else:
                data_type = Types.DOCUMENT
            content = r.document.file_id

        elif r.photo:
            content = r.photo.file_id
            data_type = Types.PHOTO

        elif r.audio:
            content = r.audio.file_id
            data_type = Types.AUDIO

        elif r.voice:
            content = r.voice.file_id
            data_type = Types.VOICE

        elif r.video:
            content = r.video.file_id
            data_type = Types.VIDEO

        elif r.video_note:
            content = r.video_note.file_id
            data_type = Types.VIDEO_NOTE

        elif r.animation:
            content = r.animation.file_id
            data_type = Types.ANIMATION

    else:
        return None, None, None, None

    return note_name, text, data_type, content


async def get_filter_type(m: Message):

    raw_text = _raw_text(m)

    if len(raw_text.split()) <= 1:
        return None, None, None

    args = raw_text.split(None, 2)

    data_type = None
    content = None
    text = None

    if not m.reply_to_message and m.text and len(raw_text.split()) >= 3:

        text = raw_text.split(None, 2)[2]
        data_type = Types.TEXT

    elif m.reply_to_message:

        text = _reply_text(m)

        r = m.reply_to_message

        if r.text:
            data_type = Types.TEXT

        elif r.sticker:
            content = r.sticker.file_id
            data_type = Types.STICKER

        elif r.document:
            if r.document.mime_type in ["application/x-bad-tgsticker", "application/x-tgsticker"]:
                data_type = Types.ANIMATED_STICKER
            else:
                data_type = Types.DOCUMENT
            content = r.document.file_id

        elif r.photo:
            content = r.photo.file_id
            data_type = Types.PHOTO

        elif r.audio:
            content = r.audio.file_id
            data_type = Types.AUDIO

        elif r.voice:
            content = r.voice.file_id
            data_type = Types.VOICE

        elif r.video:
            content = r.video.file_id
            data_type = Types.VIDEO

        elif r.video_note:
            content = r.video_note.file_id
            data_type = Types.VIDEO_NOTE

        elif r.animation:
            content = r.animation.file_id
            data_type = Types.ANIMATION

    return text, data_type, content


async def get_wlcm_type(m: Message):

    raw_text = _raw_text(m)

    data_type = None
    content = None
    text = None

    if not m.reply_to_message and m.text and len(raw_text.strip().split()) >= 2:

        text = raw_text.split(None, 1)[1]
        data_type = Types.TEXT

    elif m.reply_to_message:

        text = _reply_text(m)
        r = m.reply_to_message

        if r.text:
            data_type = Types.TEXT

        elif r.document:
            data_type = Types.DOCUMENT
            content = r.document.file_id

        elif r.photo:
            content = r.photo.file_id
            data_type = Types.PHOTO

        elif r.audio:
            content = r.audio.file_id
            data_type = Types.AUDIO

        elif r.voice:
            content = r.voice.file_id
            data_type = Types.VOICE

        elif r.video:
            content = r.video.file_id
            data_type = Types.VIDEO

        elif r.video_note:
            content = r.video_note.file_id
            data_type = Types.VIDEO_NOTE

        elif r.animation:
            content = r.animation.file_id
            data_type = Types.ANIMATION

    return text, data_type, content


async def get_afk_type(m: Message):

    raw_text = _raw_text(m)

    data_type = None
    content = None
    text = None

    if not m.reply_to_message and m.text and len(raw_text.strip().split()) >= 2:

        text = raw_text.split(None, 1)[1]
        data_type = Types.TEXT

    elif m.reply_to_message:

        text = _reply_text(m)
        r = m.reply_to_message

        if r.text:
            data_type = Types.TEXT

        elif r.document:
            data_type = Types.DOCUMENT
            content = r.document.file_id

        elif r.photo:
            content = r.photo.file_id
            data_type = Types.PHOTO

        elif r.audio:
            content = r.audio.file_id
            data_type = Types.AUDIO

        elif r.voice:
            content = r.voice.file_id
            data_type = Types.VOICE

        elif r.video:
            content = r.video.file_id
            data_type = Types.VIDEO

        elif r.video_note:
            content = r.video_note.file_id
            data_type = Types.VIDEO_NOTE

        elif r.animation:
            content = r.animation.file_id
            data_type = Types.ANIMATION

    return text, data_type, content
