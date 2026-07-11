from threading import RLock
from time import perf_counter, time
from typing import List

from cachetools import TTLCache
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import RPCError, ChannelPrivate
from pyrogram.types import CallbackQuery
from pyrogram.types.messages_and_media.message import Message

THREAD_LOCK = RLock()

# admins stay cached for 30 mins
ADMIN_CACHE = TTLCache(maxsize=512, ttl=(60 * 30), timer=perf_counter)

# Block from refreshing admin list for 10 mins
TEMP_ADMIN_CACHE_BLOCK = TTLCache(
    maxsize=512, ttl=(60 * 10), timer=perf_counter
)


async def admin_cache_reload(m: Message or CallbackQuery, status=None) -> List[int]:

    start = time()

    with THREAD_LOCK:

        if isinstance(m, CallbackQuery):
            m = m.message

        if not m or not m.chat:
            return []

        if status is not None:
            TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = status

        try:
            if TEMP_ADMIN_CACHE_BLOCK[m.chat.id] in ("autoblock", "manualblock"):
                return []
        except KeyError:
            pass

        admin_list = []

        try:

            async for z in m._client.get_chat_members(
                    m.chat.id,
                    filter=ChatMembersFilter.ADMINISTRATORS
            ):

                if z.user.is_deleted:
                    continue

                username = f"@{z.user.username}" if z.user.username else z.user.first_name

                is_anon = False
                if z.privileges:
                    is_anon = z.privileges.is_anonymous

                admin_list.append(
                    (
                        z.user.id,
                        username,
                        is_anon
                    )
                )

        except ChannelPrivate:
            return []

        except RPCError:
            return []

        ADMIN_CACHE[m.chat.id] = admin_list
        TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = "autoblock"

        return admin_list
