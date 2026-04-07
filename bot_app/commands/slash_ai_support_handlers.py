from __future__ import annotations

from typing import Any, Mapping

import discord

from bot_app.services.ai_support_service import (
    clear_summary_cooldown,
    load_moderation_log_snapshot,
    reset_chat_history,
)
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, SlashCommandResult, UserBlockState
from bot_app.ui.moderation_log_view import ModerationLogView


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


def _tracked_result(*, status: str, error_count: int, reason_code: str | None = None) -> ErrorTrackedSlashCommandResult:
    return ErrorTrackedSlashCommandResult(status=status, error_count=error_count, reason_code=reason_code)


def _build_error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="오류", description=description, color=discord.Color.red())


def _build_done_embed(description: str) -> discord.Embed:
    return discord.Embed(title="완료", description=description, color=int("a5f0ff", 16))


async def run_show_help_slash_command(interaction: discord.Interaction) -> SlashCommandResult:
    embed = discord.Embed(
        title="도움말",
        description="[도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce018010ba92e5741e6ac72a?pvs=4)",
        color=int("a5f0ff", 16),
    )
    await interaction.response.send_message(embed=embed)
    return _slash_result(status="completed", reason_code="help_shown")


async def run_show_profile_image_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.response.send_message(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    await interaction.response.defer()
    embed = discord.Embed(
        title=f"{target_user.display_name}님의 프로필 사진",
        color=int("a5f0ff", 16),
    )
    embed.set_image(url=target_user.display_avatar.url)
    embed.set_footer(text=f"요청자: {interaction.user.id}")
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="profile_image_shown")


async def run_reset_chat_slash_command(
    interaction: discord.Interaction,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        embed = _build_error_embed(
            f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다. {interaction.user.id}님은 `{block_state.reason}` 사유로 {block_state.blocked_until_label}까지 차단 중입니다."
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="blocked_user")

    reset_chat_history(interaction.user.id)
    await interaction.followup.send(
        embed=_build_done_embed("`마늘아 <할 말>` 및 `/생성형인공지능`으로 대화한 이력이 초기화되었습니다.")
    )
    return _slash_result(status="completed", reason_code="chat_reset")


async def run_check_moderation_log_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User | None,
    admin_user: discord.User | None,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    moderation_log_snapshot = load_moderation_log_snapshot(
        interaction.guild.id,
        target_user_id=None if target_user is None else target_user.id,
        admin_id=None if admin_user is None else admin_user.id,
        include_legacy=interaction.guild.id == context["using_server"],
    )
    if moderation_log_snapshot.status != "found":
        await interaction.followup.send("제재 내역이 없습니다.", ephemeral=False)
        return _slash_result(status="completed", reason_code="moderation_log_missing")

    view = ModerationLogView(moderation_log_snapshot.entries, target_user, interaction.user)
    await interaction.followup.send(embed=view.get_embed(), view=view)
    return _slash_result(status="completed", reason_code="moderation_log_found")


async def run_remove_summary_cooldown_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    await interaction.response.defer()
    if interaction.user.id != context["developer"]:
        await interaction.followup.send(
            embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `개발자`"),
            ephemeral=False,
        )
        return _tracked_result(status="rejected", error_count=error_count, reason_code="developer_only")

    try:
        clear_summary_cooldown(target_user.id, context["bot"].cooldowns)
        await interaction.followup.send(
            embed=discord.Embed(
                title="성공",
                description=f"사용자 <@{target_user.id}>의 쿨타임이 초기화되었습니다.",
                color=int("a5f0ff", 16),
            ),
            ephemeral=False,
        )
        return _tracked_result(status="completed", error_count=error_count, reason_code="summary_cooldown_cleared")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        await interaction.followup.send(
            embed=_build_error_embed(f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.")
        )
        return _tracked_result(status="failed", error_count=error_count + 1, reason_code="summary_cooldown_error")


async def run_server_advice_slash_command(
    interaction: discord.Interaction,
    *,
    prompt_text: str,
    provide_messages: bool,
    provide_channels: bool,
    start_message_link: str | None,
    end_message_link: str | None,
    role_label: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    allowed_user_ids = context["allowed_user_ids"]
    if interaction.user.id not in allowed_user_ids:
        allowed_label = " 또는 ".join(f"`사용자: {user_id}`" for user_id in allowed_user_ids)
        await interaction.response.send_message(f"권한이 부족합니다. 다음 권한이 필요합니다: {allowed_label}")
        return _slash_result(status="rejected", reason_code="server_advice_missing_permission")

    await interaction.response.send_message("처리 중입니다.")
    await context["advice_handler"](
        context["bot"],
        interaction,
        await interaction.original_response(),
        provide_messages,
        start_message_link,
        end_message_link,
        provide_channels,
        prompt_text,
        role_label,
    )
    return _slash_result(status="completed", reason_code="server_advice_started")
