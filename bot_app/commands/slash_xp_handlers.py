from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import discord

from bot_app.services.xp_service import (
    adjust_xp,
    get_effective_xp_setting,
    get_xp_ranking_page,
    get_xp_snapshot,
    process_attendance_reward,
    transfer_xp,
)
from bot_app.types.readability_contracts import SlashCommandResult, UserBlockState


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


def _slash_result(*, status: str, reason_code: str | None = None) -> SlashCommandResult:
    return SlashCommandResult(status=status, reason_code=reason_code)


async def run_attendance_slash_command(
    interaction: discord.Interaction,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    attendance_xp_setting = get_effective_xp_setting(
        server_id=interaction.guild.id,
        xp_settings=context["xp_setting"],
    )
    if attendance_xp_setting.enabled is False:
        embed = discord.Embed(
            title="오류",
            description="경험치 기능이 사용 중지되어 있는 서버입니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="xp_disabled")

    reward_result = await process_attendance_reward(
        server_id=interaction.guild.id,
        user_id=interaction.user.id,
        user_role_ids={role.id for role in interaction.user.roles},
        xp_settings=context["xp_setting"],
        using_server=context["using_server"],
        server_booster_role_id=context["server_booster_role_id"],
    )

    if reward_result.status == "attendance_disabled":
        embed = discord.Embed(
            title="오류",
            description="출석체크 기능이 사용 중지되어 있는 서버입니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="attendance_disabled")

    today_date = datetime.now(context["kst"]).strftime("%Y-%m-%d")
    if reward_result.status == "already_checked":
        await interaction.followup.send(
            f"**[오류!]** {today_date}: {interaction.user.mention} 오늘 이미 출석체크를 완료하였습니다. 다시 시도하세요."
        )
        return _slash_result(status="rejected", reason_code="already_checked")

    if reward_result.boost_check_xp > 0 and reward_result.streak > 1:
        if interaction.guild.id == context["using_server"]:
            message = (
                f"**[알림]** {today_date}: {interaction.user.mention} 출석체크 완료! (연속 {reward_result.streak}일차!) "
                f"보상으로 `{reward_result.total_xp}` {reward_result.unit}"
                f"(서버 부스터 보너스 `{reward_result.boost_check_xp}` {reward_result.unit} 포함, "
                f"연속 출석 보너스 `{reward_result.streak_bonus}` {reward_result.unit} 포함)(이)가 지급되었습니다."
            )
        else:
            message = (
                f"**[알림]** {today_date}: {interaction.user.mention} 출석체크 완료! (연속 {reward_result.streak}일차!) "
                f"보상으로 `{reward_result.total_xp}` {reward_result.unit}"
                f"(서버 부스터 보너스 `{reward_result.boost_check_xp}` {reward_result.unit} 포함)(이)가 지급되었습니다."
            )
    elif reward_result.streak > 1:
        if interaction.guild.id == context["using_server"]:
            message = (
                f"**[알림]** {today_date}: {interaction.user.mention} 출석체크 완료! (연속 {reward_result.streak}일차!) "
                f"보상으로 `{reward_result.total_xp}` {reward_result.unit}"
                f"(연속 출석 보너스 `{reward_result.streak_bonus}` {reward_result.unit} 포함)(이)가 지급되었습니다."
            )
        else:
            message = (
                f"**[알림]** {today_date}: {interaction.user.mention} 출석체크 완료! (연속 {reward_result.streak}일차!) "
                f"보상으로 `{reward_result.total_xp}` {reward_result.unit}(이)가 지급되었습니다."
            )
    elif reward_result.boost_check_xp > 0:
        message = (
            f"**[알림]** {today_date}: {interaction.user.mention} 출석체크 완료! 보상으로 `{reward_result.total_xp}` "
            f"{reward_result.unit}(서버 부스터 보너스 `{reward_result.boost_check_xp}` {reward_result.unit} 포함)(이)가 지급되었습니다."
        )
    else:
        message = (
            f"**[알림]** {today_date}: {interaction.user.mention} 출석체크 완료! "
            f"보상으로 `{reward_result.total_xp}` {reward_result.unit}(이)가 지급되었습니다."
        )

    await interaction.followup.send(message)
    return _slash_result(status="completed", reason_code="attendance_processed")


def _xp_disabled_embed() -> discord.Embed:
    return discord.Embed(
        title="오류",
        description="경험치 기능이 사용 중지되어 있는 서버입니다.",
        color=discord.Color.red(),
    )


def _resolve_enabled_xp_setting(server_id: int, xp_settings: Mapping[int, object]):
    if server_id not in xp_settings:
        return None
    xp_config = get_effective_xp_setting(server_id=server_id, xp_settings=xp_settings)
    return xp_config if xp_config.enabled else None


async def run_check_xp_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User | None,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()

    xp_config = _resolve_enabled_xp_setting(interaction.guild.id, context["xp_setting"])
    if xp_config is None:
        await interaction.followup.send(embed=_xp_disabled_embed())
        return _slash_result(status="rejected", reason_code="xp_disabled")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    member = target_user or interaction.user
    snapshot = get_xp_snapshot(
        server_id=interaction.guild.id,
        user_id=member.id,
        xp_settings=context["xp_setting"],
        using_server=context["using_server"],
    )

    if snapshot.old_xp is not None:
        description = (
            f"{member.mention}님의 경험치 보유 현황: \n"
            f"- 전체 기간: {snapshot.total_xp} {snapshot.unit} ({snapshot.total_level} 레벨)\n"
            f"- 이번 달: {snapshot.month_xp} {snapshot.unit} ({snapshot.month_level} 레벨)\n"
            f"-# [경험치 초기화](https://discord.com/channels/1320303102703702037/1423235138950529085/1435640425703538768) 전: {snapshot.old_xp} {snapshot.unit}"
        )
    else:
        description = (
            f"{member.mention}님의 경험치 보유 현황: \n"
            f"- 전체 기간: {snapshot.total_xp} {snapshot.unit} ({snapshot.total_level} 레벨)\n"
            f"- 이번 달: {snapshot.month_xp} {snapshot.unit} ({snapshot.month_level} 레벨)"
        )

    embed = discord.Embed(
        title="경험치 확인",
        color=int("a5f0ff", 16),
        description=description,
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="xp_checked")


async def run_gift_xp_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    amount: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()

    xp_config = _resolve_enabled_xp_setting(interaction.guild.id, context["xp_setting"])
    if xp_config is None:
        await interaction.followup.send(embed=_xp_disabled_embed())
        return _slash_result(status="rejected", reason_code="xp_disabled")

    if target_user.bot:
        embed = discord.Embed(title="오류", description="봇은 경험치 선물을 받을 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="gift_target_bot")

    if amount <= 0:
        embed = discord.Embed(title="오류", description="선물하려는 경험치의 양이 비정상적입니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="gift_amount_invalid")

    if interaction.user.id == target_user.id:
        embed = discord.Embed(title="오류", description="자신에게는 경험치를 선물할 수 없습니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="gift_self")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    transfer_result = transfer_xp(
        server_id=interaction.guild.id,
        sender_user_id=interaction.user.id,
        receiver_user_id=target_user.id,
        amount=amount,
        xp_settings=context["xp_setting"],
    )
    if transfer_result.status == "insufficient_balance":
        embed = discord.Embed(title="오류", description="경험치가 부족합니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="gift_insufficient_balance")

    embed = discord.Embed(
        title="완료",
        color=int("a5f0ff", 16),
        description=f"{interaction.user.mention}님이 {target_user.mention}님에게 {transfer_result.amount} {transfer_result.unit}을(를) 선물하였습니다.",
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="gift_processed")


async def run_add_xp_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    amount: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    xp_config = _resolve_enabled_xp_setting(interaction.guild.id, context["xp_setting"])
    if xp_config is None:
        await interaction.response.send_message(embed=_xp_disabled_embed(), ephemeral=False)
        return _slash_result(status="rejected", reason_code="xp_disabled")

    await interaction.response.defer()
    adjust_result = adjust_xp(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        amount=amount,
        xp_settings=context["xp_setting"],
    )
    embed = discord.Embed(
        title="성공",
        color=int("a5f0ff", 16),
        description=(
            f"{target_user.mention}님의 경험치가 {adjust_result.amount}만큼 변경되었습니다. "
            f"현재 경험치: {adjust_result.total_xp} (월간 경험치: {adjust_result.month_xp})"
        ),
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="xp_adjusted")


async def run_xp_ranking_slash_command(
    interaction: discord.Interaction,
    *,
    scope: str,
    page: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    xp_config = _resolve_enabled_xp_setting(interaction.guild.id, context["xp_setting"])
    if xp_config is None:
        await interaction.response.send_message(embed=_xp_disabled_embed(), ephemeral=False)
        return _slash_result(status="rejected", reason_code="xp_disabled")

    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    ranking_page = get_xp_ranking_page(
        server_id=interaction.guild.id,
        scope=scope,
        page=page,
        page_size=context["page_size"],
        xp_settings=context["xp_setting"],
    )

    embed = discord.Embed(title=ranking_page.title, color=int("a5f0ff", 16))
    lines = []
    for entry in ranking_page.entries:
        user = await context["bot"].fetch_user(entry.user_id)
        lines.append(f"{entry.rank}위: {user.mention} {entry.level} 레벨 - {entry.xp} {ranking_page.unit}")
    embed.description = "\n".join(lines) if lines else "해당 페이지에 데이터가 없습니다."
    embed.set_footer(text=f"페이지 {ranking_page.page} / {ranking_page.total_pages}")
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="xp_ranking_checked")
