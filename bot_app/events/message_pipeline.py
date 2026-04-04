from __future__ import annotations

from datetime import datetime
import re

import discord


async def record_chat_analyze_message(
    message,
    *,
    get_chat_analyze_onoff,
    chat_analyze_count: dict,
    chat_analyze_count_channel: dict,
    now_factory=datetime.now,
) -> None:
    chat_analyze_onoff = await get_chat_analyze_onoff(message.guild.id)
    if not chat_analyze_onoff:
        return

    now = now_factory()
    formatted_time = now.strftime("%Y-%m-%d %H:%M")

    if formatted_time not in chat_analyze_count:
        chat_analyze_count[formatted_time] = {}

    if formatted_time not in chat_analyze_count_channel:
        chat_analyze_count_channel[formatted_time] = {}

    if not message.author.bot:
        if message.guild.id not in chat_analyze_count[formatted_time]:
            chat_analyze_count[formatted_time][message.guild.id] = [message.author.id]
        else:
            chat_analyze_count[formatted_time][message.guild.id].append(message.author.id)

        if message.guild.id not in chat_analyze_count_channel[formatted_time]:
            chat_analyze_count_channel[formatted_time][message.guild.id] = {}
            chat_analyze_count_channel[formatted_time][message.guild.id][message.channel.id] = [
                message.author.id
            ]
        else:
            if message.channel.id not in chat_analyze_count_channel[formatted_time][message.guild.id]:
                chat_analyze_count_channel[formatted_time][message.guild.id][message.channel.id] = [
                    message.author.id
                ]
            else:
                chat_analyze_count_channel[formatted_time][message.guild.id][message.channel.id].append(
                    message.author.id
                )


async def handle_developer_text_commands(
    message,
    *,
    developer: int,
    add_account_relation,
    remove_account_relation,
    get_related_accounts,
    add_blacklist,
    check_blacklist,
    delete_blacklist,
    update_premium,
) -> bool:
    if message.author.id != developer:
        return False

    handled = False

    if message.content.startswith("!부계추가 "):
        pattern = r"^!부계추가\s+(\d+)\s+(\d+)$"
        match = re.match(pattern, message.content)
        if match:
            main_id = int(match.group(1))
            sub_id = int(match.group(2))
            add_account_relation(main_id, sub_id)
            await message.reply("처리되었습니다.", mention_author=False)
            handled = True
    elif message.content.startswith("!부계제거 "):
        pattern = r"^!부계제거\s+(\d+)\s+(\d+)$"
        match = re.match(pattern, message.content)
        if match:
            main_id = int(match.group(1))
            sub_id = int(match.group(2))
            remove_account_relation(main_id, sub_id)
            remove_account_relation(sub_id, main_id)
            await message.reply("처리되었습니다.", mention_author=False)
            handled = True
    elif message.content.startswith("!부계확인 "):
        pattern = r"^!부계확인\s+(\d+)$"
        match = re.match(pattern, message.content)
        if match:
            user_id = int(match.group(1))
            result = str(get_related_accounts(user_id))
            await message.author.send(f"부계 확인 결과: {result[1:-1]}")
            await message.reply("개인 DM으로 부계정 목록이 전송되었습니다.", mention_author=False)
            handled = True

    if message.content.startswith("!블리추가 "):
        pattern = r'!블리추가\s+(\d+)\s+"(.*?)"\s+"(.*?)"\s+([01])\s+(\d+)\s+(\d+)'
        match = re.match(pattern, message.content)
        if match:
            user_id = int(match.group(1))
            reason = match.group(2)
            image_link = match.group(3)
            image_private = int(match.group(4))
            report_user = int(match.group(5))
            reliability = int(match.group(6))
            add_blacklist(user_id, reason, image_link, image_private, report_user, reliability)
            await message.reply("처리되었습니다.", mention_author=False)
            handled = True
    elif message.content.startswith("!블리확인 "):
        temp = check_blacklist(int(message.content[6:]))
        print(temp)
        if temp[0] is False:
            await message.reply("블랙리스트에 존재하지 않는 유저입니다.", mention_author=False)
        else:
            await message.reply(
                (
                    "블랙리스트에 존재하는 유저입니다.\n\n"
                    f"- ID: {message.content[6:]}\n"
                    f"- 사유: {temp[1]}\n"
                    f"- 증거사진이나 메시지 링크: {temp[2]}\n"
                    f"- 증거사진 비공개 처리 여부: {temp[3]}\n"
                    f"- 신고 신뢰도: {temp[5]}단계"
                ),
                mention_author=False,
            )
        handled = True
    elif message.content.startswith("!블리제거 "):
        delete_blacklist(int(message.content[6:]))
        await message.reply("처리되었습니다.", mention_author=False)
        handled = True
    elif message.content.startswith("!프리미엄등록 "):
        update_premium(int(message.content[8:]), True)
        await message.reply("처리되었습니다.", mention_author=False)
        handled = True
    elif message.content.startswith("!프리미엄제거 "):
        update_premium(int(message.content[8:]), False)
        await message.reply("처리되었습니다.", mention_author=False)
        handled = True

    return handled


def should_ignore_direct_message(message) -> bool:
    return not bool(message.guild)


def is_message_delete_command(content: str) -> bool:
    return content.startswith("!메시지삭제") or content.startswith("!메세지삭제")


async def handle_message_delete_command(
    message,
    *,
    bot,
    using_server: int,
    message_log: int,
) -> bool:
    if not is_message_delete_command(message.content):
        return False

    if message.author.bot:
        return True

    try:
        original_message = await message.channel.fetch_message(message.reference.message_id)
    except (discord.NotFound, AttributeError):
        await message.reply("**[오류!]** 원본 메시지를 찾을 수 없습니다.", mention_author=False)
        return True

    if not message.author.guild_permissions.manage_messages:
        return False

    target_guild_id = original_message.guild.id
    target_user_id = original_message.author.id
    await original_message.delete()
    await message.reply("처리되었습니다.", mention_author=False)

    if target_guild_id != using_server:
        return True

    embed = discord.Embed(
        title="메시지 삭제",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="대상 채널", value=f"<#{message.channel.id}>", inline=False)
    embed.add_field(name="관리자", value=f"<@{message.author.id}>", inline=False)
    embed.add_field(name="개수", value="1개", inline=False)
    embed.add_field(name="대상 사용자", value=f"<@{target_user_id}>", inline=False)
    if len(message.content) >= 7:
        embed.add_field(name="사유", value=message.content[7:], inline=False)
    else:
        embed.add_field(name="사유", value="*(사유 입력되지 않음)*", inline=False)

    log_channel = bot.get_channel(message_log)
    await log_channel.send(embed=embed)
    return True


async def run_message_preprocessing(
    message,
    *,
    get_chat_analyze_onoff,
    chat_analyze_count: dict,
    chat_analyze_count_channel: dict,
    developer: int,
    add_account_relation,
    remove_account_relation,
    get_related_accounts,
    add_blacklist,
    check_blacklist,
    delete_blacklist,
    update_premium,
    bot,
    using_server: int,
    message_log: int,
) -> bool:
    await record_chat_analyze_message(
        message,
        get_chat_analyze_onoff=get_chat_analyze_onoff,
        chat_analyze_count=chat_analyze_count,
        chat_analyze_count_channel=chat_analyze_count_channel,
    )

    await handle_developer_text_commands(
        message,
        developer=developer,
        add_account_relation=add_account_relation,
        remove_account_relation=remove_account_relation,
        get_related_accounts=get_related_accounts,
        add_blacklist=add_blacklist,
        check_blacklist=check_blacklist,
        delete_blacklist=delete_blacklist,
        update_premium=update_premium,
    )

    if should_ignore_direct_message(message):
        return True

    return await handle_message_delete_command(
        message,
        bot=bot,
        using_server=using_server,
        message_log=message_log,
    )
