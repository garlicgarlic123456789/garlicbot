from __future__ import annotations

from typing import Any, Mapping

import discord

from bot_app.services.moderation_service import (
    add_warning_action,
    finalize_warn_limit_ban,
    parse_timeout_duration,
    record_timeout_action,
    record_untimeout_action,
    remove_warning_action,
)
from bot_app.services.settings_service import get_block_log_channel_for_guild


BOT_USER_ID = 1316579106749681664


async def run_warn_slash_command(
    interaction: discord.Interaction,
    사용자: discord.User,
    개수: int,
    사유: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> int:
    if 사용자.id == BOT_USER_ID:
        description = "잘못했어요.. 한 번만.." if interaction.user.id in context["friendly_list"] else "마늘이에게 경고를 부여할 수 없습니다."
        embed = discord.Embed(title="오류", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return error_count

    await interaction.response.defer()

    if 사용자.id == interaction.guild.owner_id:
        embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    if 개수 <= 0:
        embed = discord.Embed(title="오류", description="개수의 값은 1 이상이여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    if 개수 > 1000:
        embed = discord.Embed(title="오류", description="개수의 값은 1000 이하여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    member = interaction.guild.get_member(사용자.id)
    if not member:
        embed = discord.Embed(title="오류", description="사용자의 값이 올바르지 않습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    if interaction.user.top_role <= member.top_role:
        embed = discord.Embed(
            title="오류",
            description="경고 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
        return error_count

    result = await add_warning_action(
        server_id=interaction.guild.id,
        user_id=사용자.id,
        admin_id=interaction.user.id,
        amount=개수,
        reason=사유,
    )

    embed = discord.Embed(title="경고", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    if result.warn_max is not None:
        embed.add_field(name="경고 개수", value=f"{result.new_count}개 (+{result.delta}) / {result.warn_max}개", inline=False)
    else:
        embed.add_field(name="경고 개수", value=f"{result.new_count}개 (+{result.delta})", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
    if channel:
        await channel.send(embed=embed)

    if interaction.guild.id == context["using_server"]:
        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)

    if result.reached_limit:
        try:
            await interaction.guild.ban(사용자, reason="경고 한도 도달", delete_message_days=0)
        except discord.Forbidden:
            embed = discord.Embed(
                title="오류",
                description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `멤버 차단하기` 권한이 있는지 확인해 주세요.\n- 차단 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return error_count
        except Exception as exc:
            print(f"오류 #{error_count}: {exc}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return error_count + 1

        await finalize_warn_limit_ban(
            server_id=interaction.guild.id,
            user_id=사용자.id,
            bot_user_id=BOT_USER_ID,
        )
        embed = discord.Embed(title="차단", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
        embed.add_field(name="관리자", value=f"<@{BOT_USER_ID}>", inline=False)
        embed.add_field(name="사유", value="경고 한도 도달", inline=False)

        await interaction.followup.send(embed=embed)
        channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
        if channel:
            await channel.send(embed=embed)

        if interaction.guild.id == context["using_server"]:
            log_channel = context["bot"].get_channel(context["message_log"])
            if log_channel:
                await log_channel.send(embed=embed)

    return error_count


async def run_unwarn_slash_command(
    interaction: discord.Interaction,
    사용자: discord.User,
    개수: int,
    사유: str,
    *,
    context: Mapping[str, Any],
) -> None:
    await interaction.response.defer()

    if 개수 <= 0:
        embed = discord.Embed(title="오류", description="개수의 값은 1 이상이여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

    if 개수 > 1000:
        embed = discord.Embed(title="오류", description="개수의 값은 1000 이하여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

    member = interaction.guild.get_member(사용자.id)
    if not member:
        embed = discord.Embed(title="오류", description="사용자의 값이 올바르지 않습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

    if interaction.user.top_role <= member.top_role:
        embed = discord.Embed(
            title="오류",
            description="경고 차감 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
        return

    result = await remove_warning_action(
        server_id=interaction.guild.id,
        user_id=사용자.id,
        admin_id=interaction.user.id,
        amount=개수,
        reason=사유,
    )

    embed = discord.Embed(title="경고 차감", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    if result.warn_max is not None:
        embed.add_field(name="경고 개수", value=f"{result.new_count}개 (-{result.delta}) / {result.warn_max}개", inline=False)
    else:
        embed.add_field(name="경고 개수", value=f"{result.new_count}개 (-{result.delta})", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
    if channel:
        await channel.send(embed=embed)

    if interaction.guild.id == context["using_server"]:
        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)


async def run_timeout_slash_command(
    interaction: discord.Interaction,
    사용자: discord.Member,
    시간: int,
    단위: str,
    사유: str,
    개인응답: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> int:
    if 사용자.id == BOT_USER_ID:
        description = "잘못했어요.. 한 번만.." if interaction.user.id in context["friendly_list"] else "마늘이를 타임아웃할 수 없습니다."
        embed = discord.Embed(title="오류", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return error_count

    await interaction.response.defer(ephemeral=개인응답 == "True")

    if 사용자.id == interaction.guild.owner_id:
        embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return error_count

    if 사용자.top_role >= interaction.user.top_role:
        embed = discord.Embed(
            title="오류",
            description="타임아웃 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
        return error_count

    시간 = parse_timeout_duration(시간, 단위)

    if 시간 > 2419200:
        embed = discord.Embed(title="오류", description="시간의 값은 2419200 이하여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count

    reason_arg = None if 사유 == "None" else 사유
    try:
        await context["add_timeout"](사용자, 시간, reason_arg)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `타임아웃 멤버` 권한이 있는지 확인해 주세요.\n- 타임아웃 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return error_count + 1

    result = record_timeout_action(
        server_id=interaction.guild.id,
        user_id=사용자.id,
        admin_id=interaction.user.id,
        duration=시간,
        reason=reason_arg,
    )
    time_text = context["print_time"](시간) if 시간 > 0 else f"{시간}초"

    embed = discord.Embed(title="타임아웃", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    embed.add_field(name="기간", value=f"{time_text}", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
    if channel:
        await channel.send(embed=embed)

    if interaction.guild.id == context["using_server"]:
        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)
    return error_count


async def run_remove_timeout_slash_command(
    interaction: discord.Interaction,
    사용자: discord.Member,
    사유: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> int:
    if 사용자.top_role >= interaction.user.top_role:
        embed = discord.Embed(
            title="오류",
            description="타임아웃 해제 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return error_count

    await interaction.response.defer()

    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
        return error_count

    reason_arg = None if 사유 == "None" else 사유
    try:
        await 사용자.edit(timed_out_until=None, reason=reason_arg)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `타임아웃 멤버` 권한이 있는지 확인해 주세요.\n- 타임아웃 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return error_count
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return error_count + 1

    result = record_untimeout_action(
        server_id=interaction.guild.id,
        user_id=사용자.id,
        admin_id=interaction.user.id,
        reason=reason_arg,
    )

    embed = discord.Embed(title="타임아웃 해제", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{사용자.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
    if channel:
        await channel.send(embed=embed)

    if interaction.guild.id == context["using_server"]:
        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)
    return error_count
