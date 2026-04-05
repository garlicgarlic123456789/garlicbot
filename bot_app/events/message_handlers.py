from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Mapping

import discord

from bot_app.services import (
    add_warning_action,
    finalize_warn_limit_ban,
    parse_timeout_duration,
    record_timeout_action,
    record_untimeout_action,
    remove_warning_action,
)


async def handle_moderation_text_commands(
    message,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> tuple[bool, int]:
    if not message.author.bot:
        timeout_pattern = re.match(r"마늘아 타임아웃 <@!?(\d+)> (-?\d+)(초|분|시간|일|주)(?: (.+))?", message.content)
        remove_timeout_pattern = re.match(r"마늘아 타임아웃해제 <@!?(\d+)>(?: (.+))?", message.content)
        경고_pattern = re.match(r"마늘아 경고 <@!?(\d+)> (\d+) (.+)", message.content)
        경고차감_pattern = re.match(r"마늘아 경고차감 <@!?(\d+)> (\d+) (.+)", message.content)

        if 경고_pattern:
            user_id, 개수, 사유 = 경고_pattern.groups()
            개수 = int(개수)
            guild = message.guild
            사용자 = guild.get_member(int(user_id))

            if not message.author.guild_permissions.ban_members:
                embed = discord.Embed(title="오류", description="권한이 부족합니다. 다음 권한이 필요합니다: `멤버 차단하기`", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if 사용자.id == message.guild.owner_id:
                embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if 사용자.id == 1316579106749681664:
                if message.author.id in context["friendly_list"]:
                    embed = discord.Embed(title="오류", description="잘못했어요.. 한 번만..", color=discord.Color.red())
                    await message.reply(embed=embed, mention_author=False)
                    return True, error_count
                embed = discord.Embed(title="오류", description="마늘이에게 경고를 부여할 수 없습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if 개수 <= 0:
                embed = discord.Embed(title="오류", description="개수의 값은 1 이상이여야 합니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if 개수 > 1000:
                embed = discord.Embed(title="오류", description="개수의 값은 1000 이하여야 합니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if not 사용자:
                embed = discord.Embed(title="오류", description="사용자의 값이 올바르지 않습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if message.author.top_role <= 사용자.top_role:
                embed = discord.Embed(title="오류", description="경고 적용 대상의 최상위 역할이 사용자의 최상위 역할보다 높거나 같습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            result = await add_warning_action(
                server_id=message.guild.id,
                user_id=int(user_id),
                admin_id=message.author.id,
                amount=개수,
                reason=사유,
            )

            embed = discord.Embed(title="경고", color=discord.Color.red(), timestamp=discord.utils.utcnow())
            embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
            embed.add_field(name="관리자", value=f"{message.author.mention}", inline=False)
            if result.warn_max is not None:
                embed.add_field(name="경고 개수", value=f"{result.new_count}개 (+{result.delta}) / {result.warn_max}개", inline=False)
            else:
                embed.add_field(name="경고 개수", value=f"{result.new_count}개 (+{result.delta})", inline=False)
            embed.add_field(name="사유", value=result.reason, inline=False)

            channel = context["bot"].get_channel(context["get_block_log_channel"](message.guild.id))
            if channel:
                await channel.send(embed=embed)

            if message.guild.id == context["using_server"]:
                log_channel = context["bot"].get_channel(context["message_log"])
                if log_channel:
                    await log_channel.send(embed=embed)

            await message.reply(embed=embed, mention_author=False)

            if result.reached_limit:
                try:
                    await message.guild.ban(사용자, reason="경고 한도 도달", delete_message_days=0)
                except discord.Forbidden:
                    embed = discord.Embed(
                        title="오류",
                        description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `멤버 차단하기` 권한이 있는지 확인해 주세요.\n- 차단 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같은지 확인해 주세요.",
                        color=discord.Color.red(),
                    )
                    await message.reply(embed=embed, mention_author=False)
                    return True, error_count
                except Exception as exc:
                    print(f"오류 #{error_count}: {exc}")
                    embed = discord.Embed(
                        title="오류",
                        description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                        color=discord.Color.red(),
                    )
                    error_count += 1
                    await message.reply(embed=embed, mention_author=False)
                    return True, error_count

                await finalize_warn_limit_ban(
                    server_id=message.guild.id,
                    user_id=사용자.id,
                    bot_user_id=1316579106749681664,
                )
                embed = discord.Embed(title="차단", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
                embed.add_field(name="관리자", value="<@1316579106749681664>", inline=False)
                embed.add_field(name="사유", value="경고 한도 도달", inline=False)

                await message.reply(embed=embed, mention_author=False)
                channel = context["bot"].get_channel(context["get_block_log_channel"](message.guild.id))
                if channel:
                    await channel.send(embed=embed)

                if message.guild.id == context["using_server"]:
                    log_channel = context["bot"].get_channel(context["message_log"])
                    if log_channel:
                        await log_channel.send(embed=embed)

            return True, error_count

        elif 경고차감_pattern:
            user_id, 개수, 사유 = 경고차감_pattern.groups()
            개수 = int(개수)
            guild = message.guild
            사용자 = guild.get_member(int(user_id))

            if not message.author.guild_permissions.ban_members:
                embed = discord.Embed(title="오류", description="권한이 부족합니다. 다음 권한이 필요합니다: `멤버 차단하기`", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if 개수 <= 0:
                embed = discord.Embed(title="오류", description="개수의 값은 1 이상이여야 합니니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if 개수 > 1000:
                embed = discord.Embed(title="오류", description="개수의 값은 1000 이하여야 합니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if not 사용자:
                embed = discord.Embed(title="오류", description="사용자의 값이 올바르지 않습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if message.author.top_role <= 사용자.top_role:
                embed = discord.Embed(title="오류", description="경고 차감 대상의 최상위 역할이 사용자의 최상위 역할보다 높거나 같습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            result = await remove_warning_action(
                server_id=message.guild.id,
                user_id=int(user_id),
                admin_id=message.author.id,
                amount=개수,
                reason=사유,
            )

            embed = discord.Embed(title="경고 차감", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
            embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
            embed.add_field(name="관리자", value=f"{message.author.mention}", inline=False)
            if result.warn_max is not None:
                embed.add_field(name="경고 개수", value=f"{result.new_count}개 (-{result.delta}) / {result.warn_max}개", inline=False)
            else:
                embed.add_field(name="경고 개수", value=f"{result.new_count}개 (-{result.delta})", inline=False)
            embed.add_field(name="사유", value=result.reason, inline=False)

            channel = context["bot"].get_channel(context["get_block_log_channel"](message.guild.id))
            if channel:
                await channel.send(embed=embed)

            if message.guild.id == context["using_server"]:
                log_channel = context["bot"].get_channel(context["message_log"])
                if log_channel:
                    await log_channel.send(embed=embed)

            await message.reply(embed=embed, mention_author=False)
            return True, error_count

        if timeout_pattern:
            user_id, duration, unit, reason = timeout_pattern.groups()
            member = message.guild.get_member(int(user_id))
            if not member:
                embed = discord.Embed(title="오류", description="해당 사용자를 찾을 수 없습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if member.id == message.guild.owner_id:
                embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if not message.author.guild_permissions.moderate_members:
                embed = discord.Embed(title="오류", description="권한이 부족합니다. 다음 권한이 필요합니다: `타임아웃 멤버`", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if member.id == 1316579106749681664:
                if message.author.id in context["friendly_list"]:
                    embed = discord.Embed(title="오류", description="잘못했어요.. 한 번만..", color=discord.Color.red())
                    await message.reply(embed=embed, mention_author=False)
                    return True, error_count
                embed = discord.Embed(title="오류", description="마늘이를 타임아웃할 수 없습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if member.top_role >= message.author.top_role:
                embed = discord.Embed(title="오류", description="타임아웃 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            duration = parse_timeout_duration(int(duration), unit)

            if duration > 2419200:
                embed = discord.Embed(title="오류", description="duration의 값은 2419200 이하여야 합니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            reason = reason if reason else None

            try:
                await context["add_timeout"](member, duration, reason=reason)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="오류",
                    description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `타임아웃 멤버` 권한이 있는지 확인해 주세요.\n- 타임아웃 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
                    color=discord.Color.red(),
                )
                await message.reply(embed=embed, mention_author=False)
                return True, error_count
            except Exception as exc:
                print(f"오류 #{error_count}: {exc}")
                embed = discord.Embed(
                    title="오류",
                    description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                    color=discord.Color.red(),
                )
                await message.reply(embed=embed, mention_author=False)
                error_count += 1
                return True, error_count

            result = record_timeout_action(
                server_id=message.guild.id,
                user_id=member.id,
                admin_id=message.author.id,
                duration=duration,
                reason=reason,
            )

            if duration > 0:
                time_text = context["print_time"](duration)
            else:
                time_text = f"{duration}초"

            embed = discord.Embed(title="타임아웃", color=discord.Color.red(), timestamp=discord.utils.utcnow())
            embed.add_field(name="사용자", value=f"{member.mention}", inline=False)
            embed.add_field(name="관리자", value=f"{message.author.mention}", inline=False)
            embed.add_field(name="기간", value=f"{time_text}", inline=False)
            embed.add_field(name="사유", value=result.reason, inline=False)

            channel = context["bot"].get_channel(context["get_block_log_channel"](message.guild.id))
            if channel:
                await channel.send(embed=embed)

            if message.guild.id == context["using_server"]:
                log_channel = context["bot"].get_channel(context["message_log"])
                if log_channel:
                    await log_channel.send(embed=embed)

            await message.reply(embed=embed, mention_author=False)
            return True, error_count

        elif remove_timeout_pattern:
            user_id, reason = remove_timeout_pattern.groups()
            member = message.guild.get_member(int(user_id))
            if not member:
                embed = discord.Embed(title="오류", description="해당 사용자를 찾을 수 없습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            if not message.author.guild_permissions.moderate_members:
                embed = discord.Embed(title="오류", description="권한이 부족합니다. 다음 권한이 필요합니다: `타임아웃 멤버`", color=discord.Color.red())
                await message.channel.send(embed=embed)
                return True, error_count

            if member.top_role >= message.author.top_role:
                embed = discord.Embed(title="오류", description="타임아웃 해제 대상의 역할이 명령어 사용자의 역할보다 높거나 같습니다.", color=discord.Color.red())
                await message.reply(embed=embed, mention_author=False)
                return True, error_count

            reason = reason if reason else None
            try:
                await member.edit(timed_out_until=None, reason=reason)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="오류",
                    description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `타임아웃 멤버` 권한이 있는지 확인해 주세요.\n- 타임아웃 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
                    color=discord.Color.red(),
                )
                await message.reply(embed=embed, mention_author=False)
                return True, error_count
            except Exception as exc:
                print(f"오류 #{error_count}: {exc}")
                embed = discord.Embed(
                    title="오류",
                    description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                    color=discord.Color.red(),
                )
                await message.reply(embed=embed, mention_author=False)
                error_count += 1
                return True, error_count

            result = record_untimeout_action(
                server_id=message.guild.id,
                user_id=member.id,
                admin_id=message.author.id,
                reason=reason,
            )

            embed = discord.Embed(title="타임아웃 해제", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
            embed.add_field(name="사용자", value=f"{member.mention}", inline=False)
            embed.add_field(name="관리자", value=f"{message.author.mention}", inline=False)
            embed.add_field(name="사유", value=result.reason, inline=False)

            channel = context["bot"].get_channel(context["get_block_log_channel"](message.guild.id))
            if channel:
                await channel.send(embed=embed)

            if message.guild.id == context["using_server"]:
                log_channel = context["bot"].get_channel(context["message_log"])
                if log_channel:
                    await log_channel.send(embed=embed)

            await message.reply(embed=embed, mention_author=False)
            return True, error_count

        await context["process_commands"](message)

    return False, error_count


async def handle_using_server_role_watchers(message, *, context: Mapping[str, Any]) -> None:
    if message.guild.id != context["using_server"]:
        return

    mentioned_role_ids = [role.id for role in message.role_mentions]

    if any(role_id in context["do_mention_role"] for role_id in mentioned_role_ids):
        user_id = message.author.id
        now = datetime.utcnow()
        context["mention_timestamps"][user_id].append(now)
        five_minutes_ago = now - timedelta(minutes=5)
        context["mention_timestamps"][user_id] = [
            timestamp for timestamp in context["mention_timestamps"][user_id] if timestamp > five_minutes_ago
        ]

        if len(context["mention_timestamps"][user_id]) >= 4:
            await context["handle_spamming"](message, "멘션 스팸으로 의심되는 활동", 15 * 60 * 60, False, None, False)

    if "<@&1375687128708677682>" in message.content or "<@&1400872501378158764>" in message.content:
        embed = discord.Embed(
            title="안내",
            description="해당 대화하자! 역할은 더 이상 사용되지 않습니다. 관련 공지사항을 https://discord.com/channels/1320303102703702037/1320304882393153586/1418484921432932402에서 확인하세요.",
            color=discord.Color.orange(),
        )
        await message.channel.send(embed=embed)


async def handle_automod_message(message, *, context: Mapping[str, Any]) -> bool:
    if context["get_automod_exception_channel"](message.guild.id, message.channel.id) is True:
        return True

    if isinstance(message.channel, discord.Thread):
        if context["get_automod_exception_channel"](message.guild.id, message.channel.parent.id) is True:
            return True
        if message.channel.parent.category is not None:
            if context["get_automod_exception_channel"](message.guild.id, message.channel.parent.category.id) is True:
                return True
    else:
        if message.channel.category is not None:
            if context["get_automod_exception_channel"](message.guild.id, message.channel.category.id) is True:
                return True

    automod_setting = context["get_automod"](message.guild.id)

    if automod_setting["invite_link"][0]:
        if isinstance(message.channel, discord.Thread) and message.channel.parent.id == 1394966782426484796:
            return True

        pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
        if re.search(pattern1, message.content):
            await context["handle_spamming"](message, "디스코드 서버 초대 링크", automod_setting["invite_link"][1], True, None)
            return True
        elif "discord://-/invite/" in message.content:
            await context["handle_spamming"](message, "디스코드 서버 초대 링크", automod_setting["invite_link"][1], True, None)
            return True
        elif message.message_snapshots:
            if re.search(pattern1, message.message_snapshots[0].content):
                await context["handle_spamming"](message, "디스코드 서버 초대 링크", automod_setting["invite_link"][1], True, None)
                return True
            elif "discord://-/invite/" in message.message_snapshots[0].content:
                await context["handle_spamming"](message, "디스코드 서버 초대 링크", automod_setting["invite_link"][1], True, None)
                return True

    message_content = re.sub(r"[^가-힣a-zA-Z]", "", message.content)
    if message.message_snapshots:
        message_content2 = re.sub(r"[^가-힣a-zA-Z]", "", message.message_snapshots[0].content)
    else:
        message_content2 = ""

    if automod_setting["political"][0]:
        for keyword in context["automod_keyword"]:
            if keyword in message_content or keyword in message_content2:
                await context["handle_spamming"](message, context["automod_reason"], automod_setting["political"][1], True, keyword, True)
                return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword2"]:
            if keyword in message_content or keyword in message_content2:
                await context["handle_spamming"](message, context["automod_reason2"], 5 * 60 * 60, True, keyword)
                return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword3"]:
            if keyword in message_content.replace("\\", "") or keyword in message_content2.replace("\\", ""):
                await context["handle_spamming"](message, context["automod_reason3"], 24 * 60 * 60, False, keyword)
                return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword4"]:
            if keyword in message.content and message.content.startswith("!번역 "):
                await context["handle_spamming"](message, context["automod_reason4"], 15 * 60 * 60, True, keyword)
                return True
            if message.message_snapshots:
                if keyword in message.message_snapshots[0].content and message.message_snapshots[0].content.startswith("!번역 "):
                    await context["handle_spamming"](message, context["automod_reason4"], 15 * 60 * 60, True, keyword)
                    return True

    if automod_setting["sexual"][0]:
        if message.channel.id != 1344617642312597585:
            for keyword in context["automod_keyword5"]:
                if keyword in message_content or keyword in message_content2:
                    await context["handle_spamming"](message, context["automod_reason5"], automod_setting["sexual"][1], True, keyword, True)
                    return True

    if automod_setting["mention"][0]:
        if message.channel.id != 1320304882393153586:
            if message.guild.id == context["using_server"]:
                for role_mention in context["do_mention_role2"]:
                    if role_mention in message.content:
                        return True
            for keyword in context["automod_keyword6"]:
                if keyword in message.content:
                    await context["handle_spamming"](message, context["automod_reason6"], automod_setting["mention"][1], True, keyword)
                    return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword7"]:
            if keyword in message.content or keyword in message_content2:
                await context["handle_spamming"](message, context["automod_reason7"], 48 * 60 * 60, True, keyword)
                return True

    if message.guild.id == context["using_server"]:
        if message.channel.id != 1322203223028793396:
            for keyword in context["automod_keyword8"]:
                if keyword in message_content or keyword in message_content2:
                    await context["handle_spamming"](message, context["automod_reason8"], 10 * 60, True, keyword)
                    return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword9"]:
            if keyword in message_content or keyword in message_content2:
                await context["handle_spamming"](message, context["automod_reason9"], 20 * 60, True, keyword)
                return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword10"]:
            if keyword in message_content or keyword in message_content2:
                await context["handle_spamming"](message, context["automod_reason10"], 3 * 60 * 60, True, keyword)
                return True

    if message.guild.id == context["using_server"]:
        for keyword in context["automod_keyword11"]:
            if keyword in message.content or keyword in message_content2:
                await context["handle_spamming"](message, context["automod_reason11"], 24 * 60 * 60, True, keyword)
                return True

    if message.guild.id == context["using_server"]:
        for keyword in context["raid_keyword1"]:
            if keyword in message_content or keyword in message_content2:
                await context["handle_spamming"](message, "테러로 의심되는 활동", 72 * 60 * 60, True, keyword)
                await message.guild.edit(invites_disabled=True, invites_disabled_until=discord.utils.utcnow() + timedelta(days=1), reason="레이드 감지")
                await message.guild.edit(dms_disabled_until=discord.utils.utcnow() + timedelta(days=1), reason="레이드 감지")
                return True

    if message.guild.id == context["using_server"]:
        mention_cnt = message.content.count("<@")
        if mention_cnt > 7:
            await context["handle_spamming"](message, "멘션 스팸으로 의심되는 활동", 7 * 60 * 60, True, None)
            return True

    return False
