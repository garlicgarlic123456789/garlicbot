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
from bot_app.types.readability_contracts import (
    ErrorTrackedSlashCommandResult,
    SlashCommandResult,
    UserBlockState,
)


BOT_USER_ID = 1316579106749681664


def _resolve_user_block_state(block_checker, user) -> UserBlockState:
    is_blocked_now, blocked_until, block_reason = block_checker(user)
    if not is_blocked_now:
        return UserBlockState(status="not_blocked")
    blocked_until_label = None if blocked_until is None else str(blocked_until)
    return UserBlockState(
        status="blocked",
        blocked_until_label=blocked_until_label,
        reason=block_reason,
    )


def _format_blocked_message(user_id: int, block_state: UserBlockState) -> str:
    return f"**[오류!]** {user_id}님은 `{block_state.reason}` 사유로 {block_state.blocked_until_label}까지 차단 중입니다."


def _tracked_slash_result(
    error_count: int,
    *,
    status: str,
    reason_code: str | None = None,
) -> ErrorTrackedSlashCommandResult:
    return ErrorTrackedSlashCommandResult(
        status=status,
        error_count=error_count,
        reason_code=reason_code,
    )


def _slash_result(*, status: str, reason_code: str | None = None) -> SlashCommandResult:
    return SlashCommandResult(
        status=status,
        reason_code=reason_code,
    )


async def run_warn_slash_command(
    interaction: discord.Interaction,
    target_user: discord.User,
    warning_amount: int,
    reason_text: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    """Execute the /경고 slash command through the service boundary."""
    if target_user.id == BOT_USER_ID:
        description = "잘못했어요.. 한 번만.." if interaction.user.id in context["friendly_list"] else "마늘이에게 경고를 부여할 수 없습니다."
        embed = discord.Embed(title="오류", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="warn_bot_protected")

    await interaction.response.defer()

    if target_user.id == interaction.guild.owner_id:
        embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="warn_owner_protected")

    if warning_amount <= 0:
        embed = discord.Embed(title="오류", description="개수의 값은 1 이상이여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="warn_amount_too_small")

    if warning_amount > 1000:
        embed = discord.Embed(title="오류", description="개수의 값은 1000 이하여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="warn_amount_too_large")

    member = interaction.guild.get_member(target_user.id)
    if not member:
        embed = discord.Embed(title="오류", description="사용자의 값이 올바르지 않습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="warn_member_not_found")

    if interaction.user.top_role <= member.top_role:
        embed = discord.Embed(
            title="오류",
            description="경고 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="warn_role_hierarchy")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_slash_result(error_count, status="rejected", reason_code="blocked_user")

    result = await add_warning_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        amount=warning_amount,
        reason=reason_text,
    )

    embed = discord.Embed(title="경고", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
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
            await interaction.guild.ban(target_user, reason="경고 한도 도달", delete_message_days=0)
        except discord.Forbidden:
            embed = discord.Embed(
                title="오류",
                description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `멤버 차단하기` 권한이 있는지 확인해 주세요.\n- 차단 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return _tracked_slash_result(error_count, status="failed", reason_code="warn_limit_ban_forbidden")
        except Exception as exc:
            print(f"오류 #{error_count}: {exc}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return _tracked_slash_result(error_count + 1, status="failed", reason_code="warn_limit_ban_error")

        await finalize_warn_limit_ban(
            server_id=interaction.guild.id,
            user_id=target_user.id,
            bot_user_id=BOT_USER_ID,
        )
        embed = discord.Embed(title="차단", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
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

    return _tracked_slash_result(error_count, status="completed", reason_code="warn_processed")


async def run_unwarn_slash_command(
    interaction: discord.Interaction,
    target_user: discord.User,
    warning_amount: int,
    reason_text: str,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    """Execute the /경고차감 slash command through the service boundary."""
    await interaction.response.defer()

    if warning_amount <= 0:
        embed = discord.Embed(title="오류", description="개수의 값은 1 이상이여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="unwarn_amount_too_small")

    if warning_amount > 1000:
        embed = discord.Embed(title="오류", description="개수의 값은 1000 이하여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="unwarn_amount_too_large")

    member = interaction.guild.get_member(target_user.id)
    if not member:
        embed = discord.Embed(title="오류", description="사용자의 값이 올바르지 않습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="unwarn_member_not_found")

    if interaction.user.top_role <= member.top_role:
        embed = discord.Embed(
            title="오류",
            description="경고 차감 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="unwarn_role_hierarchy")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    result = await remove_warning_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        amount=warning_amount,
        reason=reason_text,
    )

    embed = discord.Embed(title="경고 차감", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
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
    return _slash_result(status="completed", reason_code="unwarn_processed")


async def run_timeout_slash_command(
    interaction: discord.Interaction,
    target_user: discord.Member,
    timeout_value: int,
    timeout_unit: str,
    reason_text: str,
    private_response: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    """Execute the /타임아웃 slash command through the service boundary."""
    if target_user.id == BOT_USER_ID:
        description = "잘못했어요.. 한 번만.." if interaction.user.id in context["friendly_list"] else "마늘이를 타임아웃할 수 없습니다."
        embed = discord.Embed(title="오류", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="timeout_bot_protected")

    await interaction.response.defer(ephemeral=private_response == "True")

    if target_user.id == interaction.guild.owner_id:
        embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count, status="rejected", reason_code="timeout_owner_protected")

    if target_user.top_role >= interaction.user.top_role:
        embed = discord.Embed(
            title="오류",
            description="타임아웃 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="timeout_role_hierarchy")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_slash_result(error_count, status="rejected", reason_code="blocked_user")

    timeout_seconds = parse_timeout_duration(timeout_value, timeout_unit)

    if timeout_seconds > 2419200:
        embed = discord.Embed(title="오류", description="시간의 값은 2419200 이하여야 합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="timeout_duration_too_large")

    reason_arg = None if reason_text == "None" else reason_text
    try:
        await context["add_timeout"](target_user, timeout_seconds, reason_arg)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `타임아웃 멤버` 권한이 있는지 확인해 주세요.\n- 타임아웃 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="failed", reason_code="timeout_forbidden")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count + 1, status="failed", reason_code="timeout_error")

    result = record_timeout_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        duration=timeout_seconds,
        reason=reason_arg,
    )
    time_text = context["print_time"](timeout_seconds) if timeout_seconds > 0 else f"{timeout_seconds}초"

    embed = discord.Embed(title="타임아웃", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
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
    return _tracked_slash_result(error_count, status="completed", reason_code="timeout_processed")


async def run_remove_timeout_slash_command(
    interaction: discord.Interaction,
    target_user: discord.Member,
    reason_text: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    """Execute the /타임아웃해제 slash command through the service boundary."""
    if target_user.top_role >= interaction.user.top_role:
        embed = discord.Embed(
            title="오류",
            description="타임아웃 해제 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="untimeout_role_hierarchy")

    await interaction.response.defer()

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_slash_result(error_count, status="rejected", reason_code="blocked_user")

    reason_arg = None if reason_text == "None" else reason_text
    try:
        await target_user.edit(timed_out_until=None, reason=reason_arg)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `타임아웃 멤버` 권한이 있는지 확인해 주세요.\n- 타임아웃 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="failed", reason_code="untimeout_forbidden")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count + 1, status="failed", reason_code="untimeout_error")

    result = record_untimeout_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        reason=reason_arg,
    )

    embed = discord.Embed(title="타임아웃 해제", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
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
    return _tracked_slash_result(error_count, status="completed", reason_code="untimeout_processed")
