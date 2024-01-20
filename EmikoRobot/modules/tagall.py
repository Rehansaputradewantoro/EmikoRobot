import asyncio

from telethon import events
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin
from telethon.tl.types import ChannelParticipantCreator

from EmikoRobot import telethn as client

spam_chats = []


@client.on(events.NewMessage(pattern="^/tagall|@all|/all ?(.*)"))
async def mentionall(event):
    chat_id = event.chat_id
    if event.is_private:
        return await event.respond("__This command can be use in groups and channels!__")

    is_admin = False
    try:
        partici_ = await client(GetParticipantRequest(
            event.chat_id,
            event.sender_id
        ))
    except UserNotParticipantError:
        is_admin = False
    else:
        if (
                isinstance(
                    partici_.participant,
                    (
                            ChannelParticipantAdmin,
                            ChannelParticipantCreator
                    )
                )
        ):
            is_admin = True
    if not is_admin:
        return await event.reply("__Lu Bukan Admin Anjeng!__")

    if event.pattern_match.group(1) and event.is_reply:
        return await event.reply("__Mana Kata-Kata Nya Goblok! !__")
    elif event.pattern_match.group(1):
        mode = "text_on_cmd"
        msg = event.pattern_match.group(1)
    elif event.is_reply:
        mode = "text_on_reply"
        msg = await event.get_reply_message()
        if msg == None:
            return await event.respond(
                "__I can't mention members for older messages! (messages which are sent before I'm added to group)__")
    else:
        return await event.reply("__Reply Chat nya Kalo Mau Tag All Goblok!__")

    spam_chats.append(chat_id)
    usrnum = 0
    usrtxt = ''
    async for usr in client.iter_participants(chat_id):
        if not chat_id in spam_chats:
            break
        usrnum += 1
        usrtxt += f"[{usr.first_name}](tg://user?id={usr.id}), "
        if usrnum == 5:
            if mode == "text_on_cmd":
                txt = f"{msg}\n{usrtxt}"
                await client.send_message(chat_id, txt)
            elif mode == "text_on_reply":
                await msg.reply(usrtxt)
            await asyncio.sleep(2)
            usrnum = 0
            usrtxt = ''
    try:
        spam_chats.remove(chat_id)
    except:
        pass


@client.on(events.NewMessage(pattern="^/cancel$"))
async def cancel_spam(event):
    is_admin = False
    try:
        partici_ = await client(GetParticipantRequest(
            event.chat_id,
            event.sender_id
        ))
    except UserNotParticipantError:
        is_admin = False
    else:
        if (
                isinstance(
                    partici_.participant,
                    (
                            ChannelParticipantAdmin,
                            ChannelParticipantCreator
                    )
                )
        ):
            is_admin = True
    if not is_admin:
        return await event.reply("__Anjeng Lu Bukan Admin Goblok!__")
    if not event.chat_id in spam_chats:
        return await event.reply("__Otw Manggil Sekumpulan Anak Babi! __")
    else:
        try:
            spam_chats.remove(event.chat_id)
        except:
            pass
        return await event.respond("__Ya Gua Stop Anjeng! __")


__mod_name__ = "Tag all"
__help__ = """
──「 Mention all func 」──

Han Can Be a Mention Bot for your group.

Only admins can tag all.  here is a list of commands

❂ /tagall or @all (reply to message or add another message) To mention all members in your group, without exception.
❂ /cancel for canceling the mention-all.
"""
