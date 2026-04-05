from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import discord

from bot_app.services.xp_service import get_effective_xp_setting, process_attendance_reward
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
