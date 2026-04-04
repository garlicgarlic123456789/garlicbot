from __future__ import annotations

from datetime import timedelta
import re
from typing import Any, Mapping

import discord


def should_skip_log_channel(channel_id: int, no_log_channel: set[int] | list[int]) -> bool:
    return channel_id in no_log_channel


def truncate_log_content(content: str | None, *, fallback: str, limit: int = 1000) -> str:
    value = content or fallback
    if len(value) > limit:
        return value[:limit] + "\n\n(이후 생략)"
    return value


def build_reaction_embed(payload, *, title: str, color: discord.Colour) -> discord.Embed:
    message_link = (
        f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"
    )

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="사용자", value=f"<@{payload.user_id}>", inline=True)

    if payload.emoji.is_custom_emoji():
        if payload.emoji.animated:
            emoji_value = f"<a:{payload.emoji.name}:{payload.emoji.id}>"
        else:
            emoji_value = f"<:{payload.emoji.name}:{payload.emoji.id}>"
    else:
        emoji_value = f"{payload.emoji.name}"

    embed.add_field(name="반응", value=emoji_value, inline=True)
    embed.add_field(name="메시지 링크", value=message_link, inline=False)
    return embed


async def _apply_edit_automod(after, context: Mapping[str, Any]) -> None:
    if after.guild.id != context["using_server"]:
        return

    handle_spamming = context["handle_spamming"]
    if handle_spamming is None:
        return

    pattern1 = (
        r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)"
        r"(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))"
        r"(?:[\/:0-9A-Za-z%\-]*)?"
    )

    if isinstance(after.channel, discord.Thread):
        if after.channel.parent.id == 1394966782426484796:
            return
    else:
        if re.search(pattern1, after.content):
            await handle_spamming(after, "디스코드 서버 초대 링크 (메시지 수정)", 15 * 60 * 60, True, None)
            return
        if "discord://-/invite/" in after.content:
            await handle_spamming(after, "디스코드 서버 초대 링크 (메시지 수정)", 15 * 60 * 60, True, None)
            return

    message_content = re.sub(r"[^가-힣a-zA-Z]", "", after.content)

    if after.channel.id != 1344617642312597585:
        for keyword in context["automod_keyword"]:
            if keyword in message_content:
                await handle_spamming(
                    after,
                    f"{context['automod_reason']} (메시지 수정)",
                    20 * 60,
                    True,
                    keyword,
                    True,
                )
                return

    for keyword in context["automod_keyword2"]:
        if keyword in message_content:
            await handle_spamming(after, f"{context['automod_reason2']} (메시지 수정)", 5 * 60 * 60, True, keyword)
            return

    for keyword in context["automod_keyword3"]:
        if keyword in after.content.replace("\\", ""):
            await handle_spamming(after, f"{context['automod_reason3']} (메시지 수정)", 24 * 60 * 60, False, keyword)
            return

    for keyword in context["automod_keyword4"]:
        if keyword in after.content and after.content.startswith("!번역 "):
            await handle_spamming(after, f"{context['automod_reason4']} (메시지 수정)", 15 * 60 * 60, True, keyword)
            return

    if after.channel.id != 1344617642312597585:
        for keyword in context["automod_keyword5"]:
            if keyword in message_content:
                await handle_spamming(
                    after,
                    f"{context['automod_reason5']} (메시지 수정)",
                    10 * 60,
                    True,
                    keyword,
                    True,
                )
                return

    for keyword in context["automod_keyword7"]:
        if keyword in after.content:
            await handle_spamming(after, f"{context['automod_reason7']} (메시지 수정)", 48 * 60 * 60, True, keyword)
            return

    if after.channel.id != 1322203223028793396:
        for keyword in context["automod_keyword8"]:
            if keyword in message_content:
                await handle_spamming(after, f"{context['automod_reason8']} (메시지 수정)", 10 * 60, True, keyword)
                return

    for keyword in context["automod_keyword9"]:
        if keyword in message_content:
            await handle_spamming(after, f"{context['automod_reason9']} (메시지 수정)", 20 * 60, True, keyword)
            return

    for keyword in context["automod_keyword10"]:
        if keyword in message_content:
            await handle_spamming(after, f"{context['automod_reason10']} (메시지 수정)", 3 * 60 * 60, True, keyword)
            return

    for keyword in context["automod_keyword11"]:
        if keyword in after.content:
            await handle_spamming(after, f"{context['automod_reason11']} (메시지 수정)", 24 * 60 * 60, True, keyword)
            return

    for keyword in context["raid_keyword1"]:
        if keyword in after.content:
            await handle_spamming(after, "테러로 의심되는 활동 (메시지 수정)", 72 * 60 * 60, True, keyword)
            await after.guild.edit(
                invites_disabled=True,
                invites_disabled_until=discord.utils.utcnow() + timedelta(days=1),
                reason="레이드 감지",
            )
            await after.guild.edit(
                dms_disabled_until=discord.utils.utcnow() + timedelta(days=1),
                reason="레이드 감지",
            )
            return


def register_log_events(bot, context: Mapping[str, Any]) -> None:
    no_log_channel = context["no_log_channel"]
    get_log_channel = context["get_log_channel"]

    @bot.event
    async def on_raw_message_delete(payload):
        if not payload.guild_id:
            return

        cached_message = payload.cached_message
        channel = bot.get_channel(payload.channel_id)
        if should_skip_log_channel(channel.id, no_log_channel):
            return

        log_id = get_log_channel(payload.guild_id)["editdelete"]
        if log_id is None:
            return

        log_channel = bot.get_channel(log_id)
        if log_channel is None:
            return

        if cached_message is None:
            content = "*(알 수 없음)*"
            author = "*(알 수 없음)*"
            reply_to = "*(알 수 없음)*"
        else:
            content = truncate_log_content(cached_message.content, fallback="*(메시지 내용 없음)*")
            author = cached_message.author.mention
            if cached_message.type == discord.MessageType.reply:
                reply_to = f"{cached_message.reference.jump_url} ({cached_message.reference.message_id})"
            else:
                reply_to = "*(답장 아님)*"

        embed = discord.Embed(
            title="메시지 삭제 로그",
            description=f"{channel.mention}에서 {author}님의 메시지가 삭제되었습니다.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="메시지 내용", value=content, inline=False)
        embed.add_field(name="메시지 ID", value=f"{payload.message_id}", inline=False)
        embed.add_field(name="답장 대상 메시지", value=reply_to, inline=False)
        await log_channel.send(embed=embed)

    @bot.event
    async def on_message_delete(message):
        if not message.guild:
            return

        log_info = get_log_channel(message.guild.id)
        image_log_enabled = log_info["image"] is not None

        if should_skip_log_channel(message.channel.id, no_log_channel):
            return

        if not image_log_enabled:
            return

        attachments = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                attachments.append(attachment.url)

        log_channel = bot.get_channel(log_info["image"])
        if not log_channel:
            return

        for attachment in attachments:
            embed = discord.Embed(
                title="메시지 삭제 로그",
                description=f"<#{message.channel.id}>에서 <@{message.author.id}>님의 메시지가 삭제되었습니다.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_image(url=attachment)
            await log_channel.send(embed=embed)

    @bot.event
    async def on_raw_message_edit(payload):
        if not payload.guild_id:
            return

        cached_message = payload.cached_message
        channel = bot.get_channel(payload.channel_id)
        if should_skip_log_channel(channel.id, no_log_channel):
            return

        log_id = get_log_channel(payload.guild_id)["editdelete"]
        if log_id is None:
            return

        log_channel = bot.get_channel(log_id)
        if not log_channel:
            return

        if payload.message.author.bot:
            return

        if cached_message is None:
            before_content = "*(알 수 없음)*"
            after_content = truncate_log_content(payload.message.content, fallback="*(수정 후 메시지 내용 없음)*")
            channel_mention = channel.mention
        else:
            before_content = truncate_log_content(cached_message.content, fallback="*(수정 전 메시지 내용 없음)*")
            after_content = truncate_log_content(payload.message.content, fallback="*(수정 후 메시지 내용 없음)*")
            if before_content == after_content:
                return
            channel_mention = f"<#{payload.channel_id}>"

        message_link = f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"
        embed = discord.Embed(
            title="메시지 수정 로그",
            description=f"{channel_mention}에서 <@{payload.message.author.id}>님의 [메시지]({message_link})가 수정되었습니다.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="수정 전 메시지 내용", value=before_content, inline=False)
        embed.add_field(name="수정 후 메시지 내용", value=after_content, inline=False)
        embed.add_field(name="메시지 ID", value=f"{payload.message_id}", inline=False)
        await log_channel.send(embed=embed)

        await _apply_edit_automod(payload.message, context)

    @bot.event
    async def on_raw_reaction_add(payload):
        if should_skip_log_channel(payload.channel_id, no_log_channel):
            return

        log_id = get_log_channel(payload.guild_id)["reaction"]
        if log_id is None:
            return

        channel = bot.get_channel(log_id)
        if not channel:
            return

        await channel.send(
            embed=build_reaction_embed(
                payload,
                title="반응 추가됨",
                color=discord.Color.blue(),
            )
        )

    @bot.event
    async def on_raw_reaction_remove(payload):
        if should_skip_log_channel(payload.channel_id, no_log_channel):
            return

        log_id = get_log_channel(payload.guild_id)["reaction"]
        if log_id is None:
            return

        channel = bot.get_channel(log_id)
        if not channel:
            return

        await channel.send(
            embed=build_reaction_embed(
                payload,
                title="반응 제거됨",
                color=discord.Color.red(),
            )
        )
