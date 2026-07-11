async def remove_markdown_and_html(text: str) -> str:
    if not text:
        return ""
    return clean_markdown(clean_html(text))


def clean_html(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("<code>", "")
        .replace("</code>", "")
        .replace("<b>", "")
        .replace("</b>", "")
        .replace("<i>", "")
        .replace("</i>", "")
        .replace("<u>", "")
        .replace("</u>", "")
    )


def clean_markdown(text: str) -> str:
    if not text:
        return ""
    return text.replace("`", "").replace("**", "").replace("__", "")
