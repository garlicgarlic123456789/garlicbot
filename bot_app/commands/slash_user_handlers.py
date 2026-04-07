from __future__ import annotations

from typing import Any, Mapping

import discord
import pytz

from bot_app.services.likeability_service import force_adjust_likeability, get_likeability_snapshot
from bot_app.services.user_service import (
    build_user_profile_snapshot,
    get_displayed_profile_xp_snapshot,
    get_user_classification,
    get_user_money_lookup,
    get_user_warning_count,
)
from bot_app.types.readability_contracts import SlashCommandResult, UserBlockState, UserProfileSnapshot


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


def _format_datetime_label(dt, timezone) -> str:
    return dt.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S")


def _resolve_member_role_mentions(member) -> tuple[str, ...]:
    role_mentions = [role.mention for role in member.roles if role.name != "@everyone"]
    return tuple(reversed(role_mentions))


def _resolve_timeout_status_label(member) -> str:
    if member.timed_out_until:
        now = discord.utils.utcnow()
        if member.timed_out_until > now:
            timeout_end_kst = member.timed_out_until.astimezone(pytz.timezone("Asia/Seoul"))
            formatted_time = timeout_end_kst.strftime("%Y-%m-%d %H:%M:%S")
            return f"타임아웃 중 ({formatted_time}까지)"
    return "제한되지 않음"


async def _resolve_ban_status_label(guild, user) -> str:
    try:
        ban_entry = await guild.fetch_ban(user)
    except discord.NotFound:
        return "제한되지 않음"
    reason = ban_entry.reason or "사유 없음"
    return f"차단 중 (사유: {reason})"


def _build_user_profile_embed(snapshot: UserProfileSnapshot) -> discord.Embed:
    embed = discord.Embed(
        title=f"{snapshot.display_name}님의 정보",
        color=int("a5f0ff", 16),
    )
    embed.add_field(name="사용자 ID", value=f"`{snapshot.user_id}`", inline=False)
    embed.add_field(name="별명", value=snapshot.display_name, inline=False)
    embed.add_field(name="멘션", value=snapshot.mention, inline=False)

    if snapshot.source == "guild_member":
        role_text = ", ".join(snapshot.role_mentions) if snapshot.role_mentions else "*(부여된 역할 없음)*"
        embed.add_field(name="보유한 역할", value=role_text, inline=False)

    if snapshot.xp_snapshot is not None:
        embed.add_field(
            name="레벨",
            value=f"{snapshot.xp_snapshot.total_level} 레벨 (월간 레벨: {snapshot.xp_snapshot.displayed_month_level} 레벨)",
            inline=False,
        )
        embed.add_field(
            name="보유한 경험치",
            value=(
                f"{snapshot.xp_snapshot.total_xp} {snapshot.xp_snapshot.unit} "
                f"(월간 경험치: {snapshot.xp_snapshot.displayed_month_xp} {snapshot.xp_snapshot.unit})"
            ),
            inline=False,
        )

    embed.add_field(name="계정 생성일", value=snapshot.account_created_at_label, inline=False)
    if snapshot.source == "guild_member" and snapshot.joined_at_label is not None:
        embed.add_field(name="서버 참가일", value=snapshot.joined_at_label, inline=False)

    embed.add_field(
        name="제재 내역",
        value=(
            "자세한 제재 내역은 </제재내역확인:1343799676545138771>을 사용하여 확인해 주세요.\n"
            f"- 부여된 경고: {snapshot.warning_count}개\n"
            f"- 제한 (타임아웃 또는 차단) 상태: {snapshot.restriction_status_label}"
        ),
        inline=False,
    )
    embed.add_field(name="유저 구분", value=snapshot.classification_label, inline=False)
    embed.set_thumbnail(url=snapshot.avatar_url)
    return embed


async def run_check_likeability_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User | None,
) -> SlashCommandResult:
    await interaction.response.defer()
    resolved_user = target_user or interaction.user
    snapshot = get_likeability_snapshot(resolved_user.id)
    embed = discord.Embed(
        title="알림",
        description=f"{resolved_user.mention}의 호감도는 {snapshot.score}입니다.",
        color=int("a5f0ff", 16),
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="likeability_checked")


async def run_add_likeability_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    amount: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    if interaction.user.id != context["developer"]:
        embed = discord.Embed(
            title="오류",
            description="권한이 부족합니다. 다음 권한이 필요합니다: `개발자`",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="missing_developer_permission")

    result = force_adjust_likeability(user_id=target_user.id, delta=amount)
    embed = discord.Embed(
        title="알림",
        description=f"{target_user.id}의 새 호감도는 {result.score}({amount}만큼 추가됨)입니다.",
        color=int("a5f0ff", 16),
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="likeability_updated")


async def run_info_slash_command(
    interaction: discord.Interaction,
    *,
    target_user,
) -> SlashCommandResult:
    try:
        result = get_user_money_lookup(target_user.id)
        if result.status == "found":
            await interaction.response.send_message(
                f"## {target_user.display_name} 정보\n사용자명: {target_user.name}\n돈 보유량: {result.money}"
            )
            return _slash_result(status="completed", reason_code="user_money_found")
        await interaction.response.send_message("**[오류!]** DB에서 해당 사용자를 찾을 수 없습니다.")
        return _slash_result(status="rejected", reason_code="user_money_missing")
    except Exception:
        await interaction.response.send_message("**[오류!]** 알 수 없는 오류가 발생했습니다.")
        return _slash_result(status="failed", reason_code="user_money_lookup_failed")


async def run_user_profile_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    kst = pytz.timezone("Asia/Seoul")
    xp_snapshot = get_displayed_profile_xp_snapshot(
        server_id=interaction.guild.id,
        user_id=target_user.id,
        xp_settings=context["xp_setting"],
    )
    warning_count = await get_user_warning_count(server_id=interaction.guild.id, user_id=target_user.id)
    classification = get_user_classification(
        user=target_user,
        block_checker=context["is_blocked"],
    )

    try:
        resolved_member = await interaction.guild.fetch_member(target_user.id)
    except discord.NotFound:
        profile_snapshot = build_user_profile_snapshot(
            source="external_user",
            user=target_user,
            role_mentions=(),
            xp_snapshot=xp_snapshot,
            account_created_at_label=_format_datetime_label(target_user.created_at, kst),
            joined_at_label=None,
            warning_count=warning_count,
            restriction_status_label=await _resolve_ban_status_label(interaction.guild, target_user),
            classification_status=classification.status,
            classification_label=classification.label,
        )
    else:
        profile_snapshot = build_user_profile_snapshot(
            source="guild_member",
            user=resolved_member,
            role_mentions=_resolve_member_role_mentions(resolved_member),
            xp_snapshot=xp_snapshot,
            account_created_at_label=_format_datetime_label(resolved_member.created_at, kst),
            joined_at_label=_format_datetime_label(resolved_member.joined_at, kst),
            warning_count=warning_count,
            restriction_status_label=_resolve_timeout_status_label(resolved_member),
            classification_status=classification.status,
            classification_label=classification.label,
        )

    await interaction.followup.send(embed=_build_user_profile_embed(profile_snapshot))
    return _slash_result(status="completed", reason_code="user_profile_checked")
