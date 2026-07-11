from html import escape
from re import compile as compilere, sub

HTML_TAG_RE = compilere(r"<.*?>")

# Telegram markdown escape characters
MD_ESCAPE_RE = compilere(r"([_*\[\]()~`>#+\-=|{}.!])")


async def cleanhtml(raw_html: str) -> str:
    """Clean html data."""
    if not raw_html:
        return ""
    return sub(HTML_TAG_RE, "", raw_html)


async def escape_markdown(text: str) -> str:
    """Escape markdown data."""
    if not text:
        return ""
    return sub(MD_ESCAPE_RE, r"\\\1", text)


async def mention_html(name: str, user_id: int) -> str:
    """Mention user in html format."""
    name = escape(name or "User")
    return f'<a href="tg://user?id={user_id}">{name}</a>'


async def mention_markdown(name: str, user_id: int) -> str:
    """Mention user in markdown format."""
    name = await escape_markdown(name or "User")
    return f"[{name}](tg://user?id={user_id})"
