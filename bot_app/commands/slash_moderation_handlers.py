from __future__ import annotations

from typing import Any, Mapping

import discord

from bot_app.services.moderation_service import (
    add_warning_action,
    finalize_warn_limit_ban,
    get_warning_status,
    parse_timeout_duration,
    record_ban_action,
    record_kick_action,
    record_timeout_action,
    record_untimeout_action,
    record_unban_action,
    remove_warning_action,
    set_warn_limit,
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


async def run_set_warn_limit_slash_command(
    interaction: discord.Interaction,
    warn_limit: int,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(
            title="오류",
            description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="missing_manage_guild_permission")

    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    if warn_limit < 0 or warn_limit > 100:
        embed = discord.Embed(
            title="오류",
            description="한도의 값은 0 이상 100 이하이어야 합니다. 한도를 없애고 싶다면, 한도에 `0`을 입력하시면 경고 한도가 비활성화됩니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="warn_limit_out_of_range")

    persisted_limit = None if warn_limit == 0 else warn_limit
    result = set_warn_limit(server_id=interaction.guild.id, warn_max=persisted_limit)
    embed = discord.Embed(
        title="완료",
        description=f"경고 한도가 {result.warn_max}개로 설정되었습니다." if result.warn_max is not None else "경고 한도가 비활성화되었습니다.",
        color=int("a5f0ff", 16),
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="warn_limit_updated")


async def run_check_warning_slash_command(
    interaction: discord.Interaction,
    target_user: discord.User | None,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    resolved_user = target_user or interaction.user
    warning_status = await get_warning_status(server_id=interaction.guild.id, user_id=resolved_user.id)

    embed = discord.Embed(
        title="경고 확인",
        color=int("a5f0ff", 16),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="사용자", value=f"{resolved_user.mention}", inline=False)
    if warning_status.warn_max is not None:
        embed.add_field(name="경고 개수", value=f"{warning_status.warning_count}개 / {warning_status.warn_max}개", inline=False)
    else:
        embed.add_field(name="경고 개수", value=f"{warning_status.warning_count}개", inline=False)

    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="warning_checked")


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


async def run_kick_slash_command(
    interaction: discord.Interaction,
    target_user: discord.Member,
    reason_text: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    if target_user.id == BOT_USER_ID:
        description = "잘못했어요.. 한 번만.." if interaction.user.id in context["friendly_list"] else "마늘이를 추방할 수 없습니다."
        embed = discord.Embed(title="오류", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="kick_bot_protected")

    if target_user.top_role >= interaction.user.top_role:
        embed = discord.Embed(
            title="오류",
            description="추방 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="kick_role_hierarchy")

    await interaction.response.defer()

    if target_user.id == interaction.guild.owner_id:
        embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="kick_owner_protected")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_slash_result(error_count, status="rejected", reason_code="blocked_user")

    reason_arg = None if reason_text == "None" else reason_text
    try:
        await interaction.guild.kick(target_user, reason=reason_arg)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `멤버 추방하기` 권한이 있는지 확인해 주세요.\n- 추방 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="failed", reason_code="kick_forbidden")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count + 1, status="failed", reason_code="kick_error")

    result = record_kick_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        reason=reason_arg,
    )
    embed = discord.Embed(title="추방", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    if interaction.guild.id == context["using_server"]:
        record_channel = context["bot"].get_channel(context["record_channel"])
        if record_channel:
            await record_channel.send(embed=embed)

        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)
    await context["process_anti_nuke_ban"](interaction.guild.id, interaction.user.id, interaction.guild)
    return _tracked_slash_result(error_count, status="completed", reason_code="kick_processed")


async def run_ban_slash_command(
    interaction: discord.Interaction,
    target_user: discord.User,
    reason_text: str,
    visibility: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    if target_user.id == BOT_USER_ID:
        description = "잘못했어요.. 한 번만.." if interaction.user.id in context["friendly_list"] else "마늘이를 차단할 수 없습니다."
        embed = discord.Embed(title="오류", description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="ban_bot_protected")

    if interaction.guild.owner_id != interaction.user.id and visibility == "비공개":
        embed = discord.Embed(
            title="오류",
            description="제재 내역을 비공개 처리할 수 있는 권한이 부족합니다.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="ban_private_visibility_denied")

    await interaction.response.defer(ephemeral=visibility == "비공개")

    if target_user.id == interaction.guild.owner_id:
        embed = discord.Embed(title="오류", description="서버 주인을 제재할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="ban_owner_protected")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_slash_result(error_count, status="rejected", reason_code="blocked_user")

    try:
        member = await interaction.guild.fetch_member(target_user.id)
        if member.top_role >= interaction.user.top_role:
            embed = discord.Embed(
                title="오류",
                description="차단 적용 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return _tracked_slash_result(error_count, status="rejected", reason_code="ban_role_hierarchy")
    except discord.NotFound:
        print("서버에 사용자가 존재하지 않음. /차단 명령어에서 예외 처리됨")

    reason_arg = None if reason_text == "None" else reason_text
    try:
        await interaction.guild.ban(target_user, reason=reason_arg, delete_message_seconds=0)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `멤버 차단하기` 권한이 있는지 확인해 주세요.\n- 차단 대상의 최상위 역할이 봇의 최상위 역할보다 높거나 같지는 않은지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="failed", reason_code="ban_forbidden")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count + 1, status="failed", reason_code="ban_error")

    result = record_ban_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        reason=reason_arg,
    )

    embed = discord.Embed(title="차단", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    if visibility == "공개":
        channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
        if channel:
            await channel.send(embed=embed)
    elif interaction.guild.id == context["using_server"]:
        owner_notify_channel = context["bot"].get_channel(context["owner_notify"])
        if owner_notify_channel:
            await owner_notify_channel.send(embed=embed)

    if interaction.guild.id == context["using_server"]:
        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)
    await context["process_anti_nuke_ban"](interaction.guild.id, interaction.user.id, interaction.guild)
    return _tracked_slash_result(error_count, status="completed", reason_code="ban_processed")


async def run_unban_slash_command(
    interaction: discord.Interaction,
    target_user: discord.User,
    reason_text: str,
    visibility: str,
    *,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    if interaction.guild.owner_id != interaction.user.id and visibility == "비공개":
        embed = discord.Embed(
            title="오류",
            description="제재 내역을 비공개 처리할 수 있는 권한이 부족합니다.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="rejected", reason_code="unban_private_visibility_denied")

    await interaction.response.defer(ephemeral=visibility == "비공개")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_slash_result(error_count, status="rejected", reason_code="blocked_user")

    reason_arg = None if reason_text == "None" else reason_text
    try:
        await interaction.guild.unban(target_user, reason=reason_arg)
    except discord.Forbidden:
        embed = discord.Embed(
            title="오류",
            description="봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `멤버 차단하기` 권한이 있는지 확인해 주세요.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return _tracked_slash_result(error_count, status="failed", reason_code="unban_forbidden")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count + 1, status="failed", reason_code="unban_error")

    result = record_unban_action(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        admin_id=interaction.user.id,
        reason=reason_arg,
    )

    embed = discord.Embed(title="차단 해제", color=int("a5f0ff", 16), timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=f"{target_user.mention}", inline=False)
    embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
    embed.add_field(name="사유", value=result.reason, inline=False)

    if visibility == "공개":
        channel = get_block_log_channel_for_guild(context["bot"], interaction.guild.id)
        if channel:
            await channel.send(embed=embed)
    elif interaction.guild.id == context["using_server"]:
        owner_notify_channel = context["bot"].get_channel(context["owner_notify"])
        if owner_notify_channel:
            await owner_notify_channel.send(embed=embed)

    if interaction.guild.id == context["using_server"]:
        log_channel = context["bot"].get_channel(context["message_log"])
        if log_channel:
            await log_channel.send(embed=embed)

    await interaction.followup.send(embed=embed)
    return _tracked_slash_result(error_count, status="completed", reason_code="unban_processed")
