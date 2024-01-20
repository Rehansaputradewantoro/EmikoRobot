import html
import time
from datetime import datetime
from io import BytesIO

from telegram import ParseMode, Update
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import mention_html

import EmikoRobot.modules.sql.global_bans_sql as sql
from EmikoRobot.modules.sql.users_sql import get_user_com_chats
from EmikoRobot import (
    DEV_USERS,
    EVENT_LOGS,
    OWNER_ID,
    STRICT_GBAN,
    DRAGONS,
    SUPPORT_CHAT,
    SPAMWATCH_SUPPORT_CHAT,
    DEMONS,
    TIGERS,
    WOLVES,
    sw,
    dispatcher,
)
from EmikoRobot.modules.helper_funcs.chat_status import (
    is_user_admin,
    support_plus,
    user_admin,
)
from EmikoRobot.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)
from EmikoRobot.modules.helper_funcs.misc import send_to_list

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/membatalkan pembatasan anggota obrolan",
    "Pengguna_bukan_peserta",
    "Peer_id_tidak valid",
    "Obrolan grup dinonaktifkan",
    "Perlu menjadi pengundang pengguna untuk mengeluarkannya dari grup dasar",
    "Obrolan_admin_diperlukan",
    "Hanya pembuat grup dasar yang dapat mengeluarkan administrator grup",
    "Saluran_pribadi",
    "Tidak dalam obrolan",
    "Tidak dapat menghapus pemilik chat",
}

UNGBAN_ERRORS = {
    "Pengguna adalah administrator obrolan", 
    "Obrolan tidak ditemukan", 
    "Tidak cukup hak untuk membatasi/membatalkan pembatasan anggota obrolan", 
    "Pengguna_bukan_peserta", "
    Metode hanya tersedia untuk supergrup dan saluran obrolan", 
    "Tidak dalam obrolan", 
    "Saluran_pribadi", "
    Obrolan_admin_diperlukan", 
    "Peer_id_tidak valid", 
    "Pengguna tidak ditemukan",
}


@support_plus
def gban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "Tampaknya Anda tidak merujuk pada pengguna atau ID yang diberikan salah..",
        )
        return

    if int(user_id) in DEV_USERS:
        message.reply_text(
            "Pengguna tersebut adalah bagian dari Pembuat\nSaya tidak dapat bertindak melawan pengguna kami sendiri.",
        )
        return

    if int(user_id) in DRAGONS:
        message.reply_text(
            "Aku memata-matai, dengan mata kecilku... sebuah bencana! Kenapa kalian saling menyerang?",
        )
        return

    if int(user_id) in DEMONS:
        message.reply_text(
            "seseorang sedang mencoba untuk memblokir Bencana Iblis! *ambil popcorn*",
        )
        return

    if int(user_id) in TIGERS:
        message.reply_text("Itu Harimau! Mereka tidak bisa dilarang!")
       )
        return

    if int(user_id) in WOLVES:
        message.reply_text("Itu Serigala! Mereka tidak bisa dilarang!!")
        return

    if user_id == bot.id:
        message.reply_text("Kamu uhh...mau memukul diriku sendiri?")
        return

    if user_id in [777000, 1087968824]:
        message.reply_text("Bodoh! Anda tidak dapat menyerang teknologi asli Telegram!!")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return ""
        return

    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna! ")
        return

    if sql.is_user_gbanned(user_id):

        if not reason:
            message.reply_text(
                "Pengguna ini sudah di-banned; Saya akan mengubah alasannya, tetapi Anda belum memberikannya kepada saya...",
            )
            return

        old_reason = sql.update_gban_reason(
            user_id,
            user_chat.username or user_chat.first_name,
            reason,
        )
        if old_reason:
            message.reply_text(
                "Pengguna ini sudah di-banned karena alasan berikut:\n"
                "<code>{}</code>\n"
                "Saya telah pergi dan memperbaruinya dengan alasan baru Anda!".format(
                    html.escape(old_reason),
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "Pengguna ini sudah di-banned, namun alasannya belum ditetapkan; Saya telah pergi dan memperbaruinya!",
            )

        return

    message.reply_text("On it!")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = "<b>{} ({})</b>\n".format(html.escape(chat.title), chat.id)
    else:
        chat_origin = "<b>{}</b>\n".format(chat.id)

    log_message = (
        f"#GBANNED\n"
        f"<b>Berasal Dari:</b> <code>{chat_origin}</code>\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna yang dilarang:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>Pengguna yang dilarang:</b> <code>{user_chat.id}</code>\n"
        f"<b>Event Stamp:</b> <code>{current_time}</code>"
    )

    if reason:
        if chat.type == chat.SUPERGROUP and chat.username:
            log_message += f'\n<b>Reason:</b> <a href="https://telegram.me/{chat.username}/{message.message_id}">{reason}</a>'
        else:
            log_message += f"\n<b>Reason:</b> <code>{reason}</code>"

    if EVENT_LOGS:
        try:
            log = bot.send_message(EVENT_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                EVENT_LOGS,
                log_message
                + "\n\nPemformatan telah dinonaktifkan karena kesalahan yang tidak terduga.",
            )

    else:
        send_to_list(bot, DRAGONS + DEMONS, log_message, html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_user_com_chats(user_id)
    gbanned_chats = 0

    for chat in chats:
        chat_id = int(chat)

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.ban_chat_member(chat_id, user_id)
            gbanned_chats += 1

        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text(f"Tidak dapat membatalkan gban: {excp.message}")
                if EVENT_LOGS:
                    bot.send_message(
                        EVENT_LOGS,
                        f"Tidak dapat membatalkan gban {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    send_to_list(
                        bot,
                        DRAGONS + DEMONS,
                        f"Tidak dapat membatalkan gban: {excp.message}",
                    )
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    if EVENT_LOGS:
        log.edit_text(
            log_message + f"\n<b>Chats affected:</b> <code>{gbanned_chats}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(
            bot,
            DRAGONS + DEMONS,
            f"Gban complete! (User banned in <code>{gbanned_chats}</code> chats)",
            html=True,
        )

    end_time = time.time()
    gban_time = round((end_time - start_time), 2)

    if gban_time > 60:
        gban_time = round((gban_time / 60), 2)
        message.reply_text("Done! Gbanned.", parse_mode=ParseMode.HTML)
    else:
        message.reply_text("Done! Gbanned.", parse_mode=ParseMode.HTML)

    try:
        bot.send_message(
            user_id,
            "#EVENT"
            "Anda telah ditandai sebagai Berbahaya dan karenanya telah dilarang dari grup mana pun yang kami kelola di masa mendatang."
            f"\n<b>Alasan:</b> <code>{html.escape(user.reason)}</code>"
            f"</b>Obrolan banding</b> @{SUPPORT_CHAT}",
            parse_mode=ParseMode.HTML,
        )
    except:
        pass  # bot probably blocked by user


@support_plus
def ungban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "Tampaknya Anda tidak merujuk pada pengguna atau ID yang diberikan salah..",
        )
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Pengguna ini tidak di blokir! ")
        return

    message.reply_text(f"I'll give {user_chat.first_name} a second chance, globally.")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = f"<b>{html.escape(chat.title)} ({chat.id})</b>\n"
    else:
        chat_origin = f"<b>{chat.id}</b>\n"

    log_message = (
        f"#UNGBANNED\n"
        f"<b>Berasal dari:</b> <code>{chat_origin}</code>\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna yang tidak diblokir:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>Pengguna yang tidak diblokir:</b> <code>{user_chat.id}</code>\n"
        f"<b>Event Stamp:</b> <code>{current_time}</code>"
    )

    if EVENT_LOGS:
        try:
            log = bot.send_message(EVENT_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                EVENT_LOGS,
                log_message
                + "\n\nPemformatan telah dinonaktifkan karena kesalahan yang tidak terduga.",
            )
    else:
        send_to_list(bot, DRAGONS + DEMONS, log_message, html=True)

    chats = get_user_com_chats(user_id)
    ungbanned_chats = 0

    for chat in chats:
        chat_id = int(chat)

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(chat_id, user_id)
                ungbanned_chats += 1

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text(f"Tidak dapat membatalkan gban karena: {excp.message}")
                if EVENT_LOGS:
                    bot.send_message(
                        EVENT_LOGS,
                        f"Tidak dapat membatalkan gban karena: {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    bot.send_message(
                        OWNER_ID,
                        f"Tidak dapat membatalkan gban karena: {excp.message}",
                    )
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    if EVENT_LOGS:
        log.edit_text(
            log_message + f"\n<b>Chats affected:</b> {ungbanned_chats}",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(bot, DRAGONS + DEMONS, "un-gban complete!")

    end_time = time.time()
    ungban_time = round((end_time - start_time), 2)

    if ungban_time > 60:
        ungban_time = round((ungban_time / 60), 2)
        message.reply_text(f"Orang telah dibatalkan pemblokirannya. Took {ungban_time} min")
    else:
        message.reply_text(f"Orang telah dibatalkan pemblokoranya. Took {ungban_time} sec")


@support_plus
def gbanlist(update: Update, context: CallbackContext):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang diblokir! Anda lebih baik dari yang saya harapkan...",
        )
        return

    banfile = "Screw these guys.\n"
    for user in banned_users:
        banfile += f"[x] {user['name']} - {user['user_id']}\n"
        if user["reason"]:
            banfile += f"Reason: {user['reason']}\n"

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Berikut adalah daftar pengguna yang saat ini di-banned.",
        )


def check_and_ban(update, user_id, should_message=True):

    if user_id in TIGERS or user_id in WOLVES:
        sw_ban = None
    else:
        try:
            sw_ban = sw.get_ban(int(user_id))
        except:
            sw_ban = None

    if sw_ban:
        update.effective_chat.ban_member(user_id)
        if should_message:
            update.effective_message.reply_text(
                f"<b>Peringatan</b>: pengguna ini di blokir secara global.\n"
                f"<code>*melarang mereka disini*</code>.\n"
                f"<b>Obrolan Banding</b>: {SPAMWATCH_SUPPORT_CHAT}\n"
                f"<b>Identitas Pengguna</b>: <code>{sw_ban.id}</code>\n"
                f"<b>Alasan di blokir</b>: <code>{html.escape(sw_ban.reason)}</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    if sql.is_user_gbanned(user_id):
        update.effective_chat.ban_member(user_id)
        if should_message:
            text = (
                f"<b>Peringatan</b>: pengguna ini diblokir secara global.\n"
                f"<code>*melarang mereka disini*</code>.\n"
                f"<b>Obrolan Banding</b>: @{SUPPORT_CHAT}\n"
                f"<b>Identitas Pengguna</b>: <code>{user_id}</code>"
            )
            user = sql.get_gbanned_user(user_id)
            if user.reason:
                text += f"\n<b>Ban Kasih Alasan:</b> <code>{html.escape(user.reason)}</code>"
            update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def enforce_gban(update: Update, context: CallbackContext):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    bot = context.bot
    try:
        restrict_permission = update.effective_chat.get_member(
            bot.id,
        ).can_restrict_members
    except Unauthorized:
        return
    if sql.does_chat_gban(update.effective_chat.id) and restrict_permission:
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)
            return

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@user_admin
def gbanstat(update: Update, context: CallbackContext):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Antispam sekarang di aktifkan ✅ "
                "Saya sekarang melindungi kelompok Anda dari potensi ancaman jarak jauh!",
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Antispan sekarang dinonaktifkan ❌ " "Spamwatch sekarang dinonaktifkan ❌",
            )
    else:
        update.effective_message.reply_text(
            "Beri saya beberapa argumen untuk memilih pengaturan! hidup/mati, yes/no!\n\n"
            "Pengaturan Anda saat ini adalah: {}\n"
            "Jika Benar, semua gban yang terjadi juga akan terjadi di grup Anda. "
            "Ketika False, mereka tidak akan melakukannya, meninggalkan Anda pada kemungkinan belas kasihan"
            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)),
        )


def __stats__():
    return f"× {sql.num_gbanned_users()} gbanned users."


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)
    text = "Malicious: <b>{}</b>"
    if user_id in [777000, 1087968824]:
        return ""
    if user_id == dispatcher.bot.id:
        return ""
    if int(user_id) in DRAGONS + TIGERS + WOLVES:
        return ""
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += f"\n<b>Reason:</b> <code>{html.escape(user.reason)}</code>"
        text += f"\n<b>Appeal Chat:</b> @{SUPPORT_CHAT}"
    else:
        text = text.format("???")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"This chat is enforcing *gbans*: `{sql.does_chat_gban(chat_id)}`."


__help__ = f"""
*Admins only:*
❂ /antispam <on/off/yes/no>: Akan mengaktifkan teknologi antispam kami atau mengembalikan pengaturan Anda saat ini.
Anti-Spam, digunakan oleh pengembang bot untuk melarang pelaku spam di semua grup. Ini membantu melindungi \
Anda dan grup Anda dengan menghapus pembanjir spam secepat mungkin.
Catatan: Pengguna dapat mengajukan banding ke gbans atau melaporkan pelaku spam di @{SUPPORT_CHAT}
❂ /flood: Dapatkan pengaturan antispam saat ini
❂ /setflood <number/off/no>: Tetapkan jumlah pesan yang akan digunakan untuk mengambil tindakan terhadap pengguna. Setel ke '0', 'mati', atau 'tidak' untuk menonaktifkan.
❂ /setfloodmode <action type>: Pilih tindakan mana yang akan diambil terhadap pengguna yang mengalami banjir. Opsi: ban/tendangan/bisu/tban/tmute.
"""

GBAN_HANDLER = CommandHandler("gban", gban, run_async=True)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, run_async=True)
GBAN_LIST = CommandHandler("gbanlist", gbanlist, run_async=True)
GBAN_STATUS = CommandHandler(
    "antispam", gbanstat, filters=Filters.chat_type.groups, run_async=True
)
GBAN_ENFORCER = MessageHandler(
    Filters.all & Filters.chat_type.groups, enforce_gban, run_async=True
)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

__mod_name__ = "Anti-Spam"
__handlers__ = [GBAN_HANDLER, UNGBAN_HANDLER, GBAN_LIST, GBAN_STATUS]

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
    __handlers__.append((GBAN_ENFORCER, GBAN_ENFORCE_GROUP))
