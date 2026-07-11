from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def ikb(rows=None, back=False, todo="start_back"):
    """
    rows = pass the rows
    back - if want to make back button
    todo - callback data of back button
    """

    if rows is None:
        rows = []

    lines = []

    try:
        for row in rows:
            line = []

            for button in row:

                if isinstance(button, str) and "." in button:
                    btn_text = button.split(".", 1)[1].capitalize()
                    button = btn(btn_text, button)

                elif isinstance(button, (list, tuple)):
                    button = btn(*button)

                else:
                    button = btn(str(button), str(button))

                line.append(button)

            lines.append(line)

    except Exception:
        line = []

        for button in rows:
            button = btn(*button)
            line.append(button)

        lines.append(line)

    if back:
        lines.append([btn("« Back", todo)])

    return InlineKeyboardMarkup(lines)


def btn(text, value, type="callback_data"):
    return InlineKeyboardButton(text, **{type: value})
