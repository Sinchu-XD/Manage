from traceback import format_exc
from typing import Tuple

from pyrogram.enums import MessageEntityType as entity
from pyrogram.types.messages_and_media.message import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.database.users_db import Users


async def extract_user(c: Gojo, m: Message) -> Tuple[int, str, str]:

    user_id = None
    user_first_name = None
    user_name = None

    # Reply user
    if m.reply_to_message and m.reply_to_message.from_user:

        user = m.reply_to_message.from_user
        user_id = user.id
        user_first_name = user.first_name
        user_name = user.username

    # Command argument
    elif getattr(m, "command", None) and len(m.command) > 1:

        entities = m.entities or []

        if len(entities) > 1:

            required_entity = entities[1]

            if required_entity.type == entity.TEXT_MENTION:

                user = required_entity.user
                user_id = user.id
                user_first_name = user.first_name
                user_name = user.username

            elif required_entity.type in (entity.MENTION, entity.PHONE_NUMBER):

                user_found = m.text[
                    required_entity.offset :
                    required_entity.offset + required_entity.length
                ]

                try:
                    user_found = int(user_found)
                except Exception:
                    user_found = str(user_found)

                try:
                    user = Users.get_user_info(user_found)
                    if user:
                        user_id = user["_id"]
                        user_first_name = user["name"]
                        user_name = user["username"]
                    else:
                        raise KeyError

                except KeyError:

                    try:
                        user = await c.get_users(user_found)
                    except Exception:

                        try:
                            peer = await c.resolve_peer(user_found)
                            user = await c.get_users(peer.user_id)
                        except Exception as ef:
                            await m.reply_text(f"User not found ! Error: {ef}")
                            return None, None, None

                    user_id = user.id
                    user_first_name = user.first_name
                    user_name = user.username

                except Exception as ef:
                    LOGGER.error(ef)
                    LOGGER.error(format_exc())

                    user_id = user_found
                    user_first_name = str(user_found)
                    user_name = ""

        else:

            user_found = m.text.split()[1]

            try:
                user_id = int(user_found)
            except Exception:
                user_id = user_found if user_found.startswith("@") else None

            if user_id is not None:

                try:
                    user = Users.get_user_info(user_id)
                    if user:
                        user_first_name = user["name"]
                        user_name = user["username"]
                    else:
                        raise KeyError

                except Exception:

                    try:
                        user = await c.get_users(user_id)
                    except Exception:

                        try:
                            peer = await c.resolve_peer(user_id)
                            user = await c.get_users(peer.user_id)
                        except Exception as ef:
                            await m.reply_text(f"User not found ! Error: {ef}")
                            return None, None, None

                    user_id = user.id
                    user_first_name = user.first_name
                    user_name = user.username

    else:

        if not m.from_user:
            return None, None, None

        user = m.from_user
        user_id = user.id
        user_first_name = user.first_name
        user_name = user.username

    return user_id, user_first_name, user_name
