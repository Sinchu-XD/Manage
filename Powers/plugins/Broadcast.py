from asyncio import gather, sleep
from time import time
from traceback import format_exc

from pyrogram import enums
from pyrogram.errors import (
    ChannelInvalid,
    ChannelPrivate,
    ChatAdminRequired,
    ChatWriteForbidden,
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    RPCError,
    UserIsBlocked,
    UserNotParticipant,
)
from pyrogram.types import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.database import MongoDB
from Powers.database.chats_db import Chats
from Powers.database.users_db import Users
from Powers.utils.custom_filters import command

BATCH_SIZE = 10
CHECKPOINT_EVERY = 50
UPDATE_INTERVAL = 120


class _State:
    COL = "broadcast_state"

    @staticmethod
    def save(btype, from_chat_id, message_id, targets_users, targets_chats):
        db = MongoDB(_State.COL)
        db.delete_one({"_id": "current"})
        db.insert_one({
            "_id": "current", "btype": btype,
            "from_chat_id": from_chat_id, "message_id": message_id,
            "targets_users": targets_users, "targets_chats": targets_chats,
            "idx_users": 0, "idx_chats": 0,
            "done_users": 0, "done_chats": 0,
            "failed_users": 0, "failed_chats": 0,
            "reasons_users": {}, "reasons_chats": {},
        })

    @staticmethod
    def checkpoint(idx_users, idx_chats, done_u, done_c,
                   failed_u, failed_c, reasons_u, reasons_c):
        db = MongoDB(_State.COL)
        db.update({"_id": "current"}, {
            "idx_users": idx_users, "idx_chats": idx_chats,
            "done_users": done_u, "done_chats": done_c,
            "failed_users": failed_u, "failed_chats": failed_c,
            "reasons_users": reasons_u, "reasons_chats": reasons_c,
        })

    @staticmethod
    def get():
        db = MongoDB(_State.COL)
        result = db.find_one({"_id": "current"})
        return result if result else {}

    @staticmethod
    def clear():
        MongoDB(_State.COL).delete_one({"_id": "current"})


async def _copy(c, target_id, from_chat_id, message_id):
    try:
        await c.copy_message(
            chat_id=target_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
        )
        return True, "ok"
    except FloodWait as fw:
        await sleep(fw.value + 2)
        try:
            await c.copy_message(
                chat_id=target_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            return True, "ok"
        except Exception:
            return False, "flood_retry_failed"
    except UserIsBlocked:                    return False, "blocked"
    except InputUserDeactivated:             return False, "deactivated"
    except PeerIdInvalid:                    return False, "invalid_id"
    except (ChannelInvalid, ChannelPrivate): return False, "channel_unavailable"
    except ChatWriteForbidden:               return False, "write_forbidden"
    except ChatAdminRequired:                return False, "admin_required"
    except UserNotParticipant:               return False, "not_participant"
    except RPCError:                         return False, "rpc_error"
    except Exception:
        LOGGER.error(format_exc())
        return False, "unknown"


def _reason_label(r):
    return {
        "blocked":             "Bot blocked by user",
        "deactivated":         "Account deleted/deactivated",
        "invalid_id":          "Invalid peer ID",
        "channel_unavailable": "Channel invalid/private",
        "write_forbidden":     "Write forbidden (kicked)",
        "admin_required":      "Admin rights required",
        "not_participant":     "Bot not in chat",
        "rpc_error":           "Telegram RPC error",
        "flood_retry_failed":  "Flood wait retry failed",
        "unknown":             "Unknown error",
    }.get(r, r)


def _progress_text(label, total, done, failed, reasons, elapsed):
    mins, secs = divmod(elapsed, 60)
    processed = done + failed
    pct = round((processed / total) * 100) if total else 0
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    lines = [
        f"<b>📡 {label} — In Progress</b>", "",
        f"<code>[{bar}] {pct}%</code>",
        f"• <b>Total:</b>     <code>{total}</code>",
        f"• <b>Sent:</b>      <code>{done}</code>",
        f"• <b>Failed:</b>    <code>{failed}</code>",
        f"• <b>Remaining:</b> <code>{total - processed}</code>",
        f"• <b>Time:</b>      <code>{mins}m {secs}s</code>",
    ]
    if reasons:
        lines.append("\n<b>❌ Failure Reasons:</b>")
        for r, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
            lines.append(f"  • {_reason_label(r)}: <code>{cnt}</code>")
    return "\n".join(lines)


def _final_text(label, total, done, failed, reasons, elapsed):
    mins, secs = divmod(elapsed, 60)
    rate = round((done / total) * 100) if total else 0
    lines = [
        f"<b>✅ {label} — Complete!</b>", "",
        f"• <b>Total targets:</b>    <code>{total}</code>",
        f"• <b>Successfully sent:</b> <code>{done}</code>",
        f"• <b>Failed:</b>           <code>{failed}</code>",
        f"• <b>Success rate:</b>     <code>{rate}%</code>",
        f"• <b>Time taken:</b>       <code>{mins}m {secs}s</code>",
    ]
    if reasons:
        lines.append("\n<b>❌ Failure Breakdown:</b>")
        for r, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
            lines.append(f"  • {_reason_label(r)}: <code>{cnt}</code>")
    return "\n".join(lines)


async def _run_targets(c, status_msg, label, targets, from_chat_id, message_id,
                       is_chat, start_idx=0, init_done=0, init_failed=0,
                       init_reasons=None, get_checkpoint_kwargs=None):
    done = init_done
    failed = init_failed
    reasons = dict(init_reasons or {})
    total = len(targets)
    start_time = time()
    last_update = time()
    processed = start_idx

    for batch_start in range(start_idx, total, BATCH_SIZE):
        batch = targets[batch_start: batch_start + BATCH_SIZE]
        results = await gather(*[_copy(c, t, from_chat_id, message_id) for t in batch])

        for i, (ok, reason) in enumerate(results):
            tid = batch[i]
            if ok:
                done += 1
            else:
                failed += 1
                reasons[reason] = reasons.get(reason, 0) + 1
                if is_chat:
                    Chats.remove_invalid_chat(tid)
                else:
                    Users.remove_invalid_user(tid)
            processed += 1

        if processed % CHECKPOINT_EVERY < BATCH_SIZE and get_checkpoint_kwargs:
            try:
                _State.checkpoint(**get_checkpoint_kwargs(processed, done, failed, reasons))
            except Exception:
                pass

        if time() - last_update >= UPDATE_INTERVAL:
            last_update = time()
            try:
                await status_msg.edit_text(
                    _progress_text(label, total, done, failed, reasons,
                                   int(time() - start_time)),
                    parse_mode=enums.ParseMode.HTML,
                )
            except Exception:
                pass

        await sleep(0.05)

    return done, failed, reasons, processed


@Gojo.on_message(command(["broadcast", "chatbroadcast"], owner_cmd=True))
async def broadcast_to_chats(c: Gojo, m: Message):
    if not m.reply_to_message:
        await m.reply_text(
            "<b>Usage:</b> Reply to a message with /broadcast to send it to all chats."
        )
        return

    src = m.reply_to_message
    chat_ids = Chats.list_chats_by_id()
    total = len(chat_ids)
    _State.save("chats", src.chat.id, src.id, [], chat_ids)

    status = await m.reply_text(
        f"<b>📡 Broadcast Starting</b>\n\n"
        f"• <b>Target chats:</b> <code>{total}</code>\n"
        f"<i>Sending… har 2 minute mein live update milega.</i>",
        parse_mode=enums.ParseMode.HTML,
    )
    start_time = time()

    def ckpt(idx, done, failed, reasons):
        return dict(idx_users=0, idx_chats=idx, done_u=0, done_c=done,
                    failed_u=0, failed_c=failed, reasons_u={}, reasons_c=reasons)

    done, failed, reasons, _ = await _run_targets(
        c, status, "Broadcast", chat_ids, src.chat.id, src.id,
        is_chat=True, get_checkpoint_kwargs=ckpt,
    )
    _State.clear()
    await status.edit_text(
        _final_text("Broadcast", total, done, failed, reasons, int(time() - start_time)),
        parse_mode=enums.ParseMode.HTML,
    )


@Gojo.on_message(command("fwd", owner_cmd=True))
async def forward_message(c: Gojo, m: Message):
    if not m.reply_to_message:
        await m.reply_text(
            "<b>Usage:</b> Reply to a message with:\n"
            "• <code>/fwd -u</code>  — forward to all users\n"
            "• <code>/fwd -c</code>  — forward to all chats\n"
            "• <code>/fwd all</code> — forward to all users + chats",
        )
        return

    args = m.command[1:]
    if not args:
        await m.reply_text(
            "Flag specify karo:\n"
            "<code>/fwd -u</code>  |  <code>/fwd -c</code>  |  <code>/fwd all</code>"
        )
        return

    flag = args[0].lower()
    send_users = flag in ("-u", "all")
    send_chats = flag in ("-c", "all")

    if not send_users and not send_chats:
        await m.reply_text(
            "Unknown flag. Use <code>-u</code>, <code>-c</code>, or <code>all</code>."
        )
        return

    src = m.reply_to_message
    user_ids = Users.list_user_ids() if send_users else []
    chat_ids = Chats.list_chats_by_id() if send_chats else []

    _State.save(
        "all" if (send_users and send_chats) else ("users" if send_users else "chats"),
        src.chat.id, src.id, user_ids, chat_ids,
    )

    preview = ["<b>📡 Forward Starting</b>\n"]
    if send_users:
        preview.append(f"• <b>Target users:</b> <code>{len(user_ids)}</code>")
    if send_chats:
        preview.append(f"• <b>Target chats:</b> <code>{len(chat_ids)}</code>")
    preview.append("<i>Sending… har 2 minute mein live update milega.</i>")

    status = await m.reply_text("\n".join(preview), parse_mode=enums.ParseMode.HTML)
    start_time = time()
    u_done = u_failed = 0
    c_done = c_failed = 0
    u_reasons: dict = {}
    c_reasons: dict = {}

    if send_users:
        def ckpt_u(idx, done, failed, reasons):
            return dict(idx_users=idx, idx_chats=0, done_u=done, done_c=0,
                        failed_u=failed, failed_c=0, reasons_u=reasons, reasons_c={})
        u_done, u_failed, u_reasons, _ = await _run_targets(
            c, status, "Users", user_ids, src.chat.id, src.id,
            is_chat=False, get_checkpoint_kwargs=ckpt_u,
        )

    if send_chats:
        def ckpt_c(idx, done, failed, reasons):
            return dict(idx_users=len(user_ids), idx_chats=idx,
                        done_u=u_done, done_c=done,
                        failed_u=u_failed, failed_c=failed,
                        reasons_u=u_reasons, reasons_c=reasons)
        c_done, c_failed, c_reasons, _ = await _run_targets(
            c, status, "Chats", chat_ids, src.chat.id, src.id,
            is_chat=True, get_checkpoint_kwargs=ckpt_c,
        )

    _State.clear()
    elapsed = int(time() - start_time)
    parts = []
    if send_users:
        parts.append(_final_text("Users Forward", len(user_ids), u_done, u_failed, u_reasons, elapsed))
    if send_chats:
        if parts:
            parts.append("")
        parts.append(_final_text("Chats Forward", len(chat_ids), c_done, c_failed, c_reasons, elapsed))
    await status.edit_text("\n".join(parts), parse_mode=enums.ParseMode.HTML)


@Gojo.on_message(command("resumebroadcast", owner_cmd=True))
async def resume_broadcast(c: Gojo, m: Message):
    state = _State.get()
    if not state:
        await m.reply_text("⚠️ Koi pending broadcast nahi mila.")
        return

    from_chat_id = state.get("from_chat_id")
    message_id   = state.get("message_id")
    t_users      = state.get("targets_users", [])
    t_chats      = state.get("targets_chats", [])
    idx_u        = state.get("idx_users", 0)
    idx_c        = state.get("idx_chats", 0)
    done_u       = state.get("done_users", 0)
    done_c       = state.get("done_chats", 0)
    failed_u     = state.get("failed_users", 0)
    failed_c     = state.get("failed_chats", 0)
    reasons_u    = state.get("reasons_users", {})
    reasons_c    = state.get("reasons_chats", {})

    status = await m.reply_text(
        f"<b>🔄 Broadcast Resume Ho Raha Hai</b>\n\n"
        f"• <b>Users remaining:</b> <code>{len(t_users) - idx_u}</code>\n"
        f"• <b>Chats remaining:</b> <code>{len(t_chats) - idx_c}</code>\n"
        f"• <b>Already sent (users):</b> <code>{done_u}</code>\n"
        f"• <b>Already sent (chats):</b> <code>{done_c}</code>\n\n"
        f"<i>Resuming… har 2 minute mein update milega.</i>",
        parse_mode=enums.ParseMode.HTML,
    )
    start_time = time()

    if t_users and idx_u < len(t_users):
        def ckpt_u(idx, done, failed, reasons):
            return dict(idx_users=idx_u + idx, idx_chats=idx_c,
                        done_u=done_u + done, done_c=done_c,
                        failed_u=failed_u + failed, failed_c=failed_c,
                        reasons_u=reasons, reasons_c=reasons_c)
        done_u, failed_u, reasons_u, _ = await _run_targets(
            c, status, "Users", t_users, from_chat_id, message_id,
            is_chat=False, start_idx=idx_u, init_done=done_u,
            init_failed=failed_u, init_reasons=reasons_u,
            get_checkpoint_kwargs=ckpt_u,
        )

    if t_chats and idx_c < len(t_chats):
        def ckpt_c(idx, done, failed, reasons):
            return dict(idx_users=len(t_users), idx_chats=idx_c + idx,
                        done_u=done_u, done_c=done_c + done,
                        failed_u=failed_u, failed_c=failed_c + failed,
                        reasons_u=reasons_u, reasons_c=reasons)
        done_c, failed_c, reasons_c, _ = await _run_targets(
            c, status, "Chats", t_chats, from_chat_id, message_id,
            is_chat=True, start_idx=idx_c, init_done=done_c,
            init_failed=failed_c, init_reasons=reasons_c,
            get_checkpoint_kwargs=ckpt_c,
        )

    _State.clear()
    elapsed = int(time() - start_time)
    parts = []
    if t_users:
        parts.append(_final_text("Users", len(t_users), done_u, failed_u, reasons_u, elapsed))
    if t_chats:
        if parts:
            parts.append("")
        parts.append(_final_text("Chats", len(t_chats), done_c, failed_c, reasons_c, elapsed))
    await status.edit_text("\n".join(parts), parse_mode=enums.ParseMode.HTML)


@Gojo.on_message(command("broadcaststatus", owner_cmd=True))
async def broadcast_status(c: Gojo, m: Message):
    state = _State.get()
    if not state:
        await m.reply_text("✅ Koi pending broadcast nahi hai.")
        return
    t_users = state.get("targets_users", [])
    t_chats = state.get("targets_chats", [])
    idx_u   = state.get("idx_users", 0)
    idx_c   = state.get("idx_chats", 0)
    done_u  = state.get("done_users", 0)
    done_c  = state.get("done_chats", 0)
    await m.reply_text(
        f"<b>⏸ Pending Broadcast Mila!</b>\n\n"
        f"• <b>Users:</b> sent <code>{done_u}</code>/<code>{len(t_users)}</code>"
        f" (remaining: <code>{len(t_users) - idx_u}</code>)\n"
        f"• <b>Chats:</b> sent <code>{done_c}</code>/<code>{len(t_chats)}</code>"
        f" (remaining: <code>{len(t_chats) - idx_c}</code>)\n\n"
        f"/resumebroadcast — resume karo\n"
        f"/cancelbroadcast — cancel karo",
        parse_mode=enums.ParseMode.HTML,
    )


@Gojo.on_message(command("cancelbroadcast", owner_cmd=True))
async def cancel_broadcast(c: Gojo, m: Message):
    if not _State.get():
        await m.reply_text("⚠️ Koi pending broadcast nahi hai.")
        return
    _State.clear()
    await m.reply_text("🗑 Pending broadcast cancel kar diya.")


__PLUGIN__ = "broadcast"
__HELP__ = """
**Broadcast / Forward** (Owner only)

• `/broadcast` — Reply to any message → all chats ko bhejo.
• `/chatbroadcast` — /broadcast ka alias.
• `/fwd -u` — Sabhi users ko bhejo.
• `/fwd -c` — Sabhi chats ko bhejo.
• `/fwd all` — Users + chats dono ko bhejo.

• `/broadcaststatus` — Pending broadcast check karo.
• `/resumebroadcast` — Bot band hone ke baad wahi se resume karo.
• `/cancelbroadcast` — Pending broadcast cancel karo.

Features:
- Pehle total target count dikhata hai
- 10 concurrent sends (5-10x fast)
- Har 2 minute mein live progress bar
- Har 50 sends pe DB checkpoint (resume possible)
- Final report with reason-wise failure breakdown
- Failed targets auto-remove from database
"""
