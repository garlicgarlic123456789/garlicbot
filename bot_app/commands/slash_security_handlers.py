from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

import discord

from bot_app.types.readability_contracts import (
    AutomodRuleConfig,
    ErrorTrackedSlashCommandResult,
    SlashCommandResult,
    UserBlockState,
)


def add_developer_restriction(*, user_id: int, reason_text: str, until_date_label: str):
    from bot_app.services.security_service import add_developer_restriction as impl

    return impl(user_id, reason=reason_text, until=until_date_label)


def remove_developer_restriction(*, user_id: int):
    from bot_app.services.security_service import remove_developer_restriction as impl

    return impl(user_id=user_id)


def get_developer_restriction_state(*, user_id: int) -> UserBlockState:
    from bot_app.services.security_service import get_developer_restriction_state as impl

    return impl(type("DeveloperRestrictionUser", (), {"id": user_id})())


def update_channel_command_permission(
    *,
    server_id: int,
    command_name: str,
    channel_id: int,
    permission: str | None,
    role_id: int | None,
    user_id: int | None,
):
    from bot_app.services.security_service import update_channel_command_permission as impl

    return impl(
        server_id=server_id,
        command_name=command_name,
        channel_id=channel_id,
        target_kind="role" if role_id is not None else "user",
        role_id=role_id,
        user_id=user_id,
        permitted=permission,
    )


def update_server_command_permission(*, server_id: int, command_name: str, permission: str, role_id: int):
    from bot_app.services.security_service import update_server_command_permission as impl

    return impl(
        server_id=server_id,
        command_name=command_name,
        target_kind="role",
        role_id=role_id,
        permitted=permission,
    )


def update_automod_exception_channel_setting(*, server_id: int, channel_id: int, enabled: bool):
    from bot_app.services.security_service import update_automod_exception_channel_setting as impl

    return impl(server_id=server_id, channel_id=channel_id, enabled=enabled)


def update_automod_setting(
    *,
    server_id: int,
    political_enabled: bool,
    political_timeout_seconds: int,
    sexual_enabled: bool,
    sexual_timeout_seconds: int,
    invite_enabled: bool,
    invite_timeout_seconds: int,
    mention_enabled: bool,
    mention_timeout_seconds: int,
    whitelist_permission: str,
):
    from bot_app.services.security_service import update_automod_setting as impl

    return impl(
        server_id=server_id,
        political=AutomodRuleConfig(enabled=political_enabled, action=political_timeout_seconds),
        sexual=AutomodRuleConfig(enabled=sexual_enabled, action=sexual_timeout_seconds),
        invite_link=AutomodRuleConfig(enabled=invite_enabled, action=invite_timeout_seconds),
        mention=AutomodRuleConfig(enabled=mention_enabled, action=mention_timeout_seconds),
        whitelist_permission=whitelist_permission,
    )


def update_quarantine_role_setting(*, server_id: int, role_id: int):
    from bot_app.services.security_service import update_quarantine_role_setting as impl

    return impl(server_id=server_id, role_id=role_id)


def get_quarantine_role_id(*, server_id: int):
    from bot_app.services.security_service import get_quarantine_role_id as impl

    return impl(server_id=server_id)


def apply_guild_security_action(
    *,
    guild,
    actor,
    server_join_block_seconds: int,
    dm_block_seconds: int,
    reason_text: str,
):
    from bot_app.services.security_service import apply_guild_security_action as impl

    return impl(
        guild=guild,
        actor=actor,
        invite_disabled_seconds=server_join_block_seconds,
        dm_disabled_seconds=dm_block_seconds,
        reason=reason_text,
    )


def update_anti_nuke_setting(*, server_id: int, enabled: bool, log_channel_id: int):
    from bot_app.services.security_service import update_anti_nuke_setting as impl

    return impl(server_id=server_id, enabled=enabled, log_channel_id=log_channel_id)


def update_anti_nuke_whitelist_setting(*, server_id: int, user_id: int, enabled: bool):
    from bot_app.services.security_service import update_anti_nuke_whitelist_setting as impl

    return impl(server_id=server_id, user_id=user_id, enabled=enabled)


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


def _tracked_result(
    error_count: int,
    *,
    status: str,
    reason_code: str | None = None,
) -> ErrorTrackedSlashCommandResult:
    return ErrorTrackedSlashCommandResult(status=status, error_count=error_count, reason_code=reason_code)


def _build_error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="오류", description=description, color=discord.Color.red())


def _build_done_embed(description: str) -> discord.Embed:
    return discord.Embed(title="완료", description=description, color=int("a5f0ff", 16))


def _normalize_optional_reason(reason_text: str | None) -> str | None:
    return None if reason_text in (None, "None") else reason_text


def _normalize_reason_label(reason_text: str | None) -> str:
    return "*(사유 입력되지 않음)*" if reason_text is None else reason_text


def _parse_duration_to_seconds(duration_text: str) -> int | None:
    if duration_text.endswith("초"):
        return int(duration_text.removesuffix("초"))
    if duration_text.endswith("분"):
        return int(duration_text.removesuffix("분")) * 60
    if duration_text.endswith("시간"):
        return int(duration_text.removesuffix("시간")) * 3600
    if duration_text.endswith("일"):
        return int(duration_text.removesuffix("일")) * 86400
    return None


def _split_text(text: str, chunk_size: int = 3000) -> tuple[str, ...]:
    return tuple(text[index : index + chunk_size] for index in range(0, len(text), chunk_size))


async def run_bulk_delete_slash_command(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    target_user: discord.User | None,
    reason_text: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    """Execute /일괄삭제 behind a helper boundary while keeping response/log format intact."""
    if not start_message_link:
        await interaction.response.send_message("**[오류!]** 시작의 값은 필수입니다.", ephemeral=False)
        return _slash_result(status="rejected", reason_code="bulk_delete_missing_start")

    try:
        start_message_id = int(start_message_link.split("/")[-1])
        start_message = await interaction.channel.fetch_message(start_message_id)
    except (IndexError, ValueError, discord.NotFound):
        await interaction.response.send_message("**[오류!]** 시작 메시지가 이 채널에 존재하지 않습니다.", ephemeral=False)
        return _slash_result(status="rejected", reason_code="bulk_delete_start_not_found")

    if end_message_link:
        try:
            end_message_id = int(end_message_link.split("/")[-1])
            end_message = await interaction.channel.fetch_message(end_message_id)
        except (IndexError, ValueError, discord.NotFound):
            await interaction.response.send_message("**[오류!]** 끝 메시지가 이 채널에 존재하지 않습니다.", ephemeral=False)
            return _slash_result(status="rejected", reason_code="bulk_delete_end_not_found")
    else:
        end_message = None

    await interaction.response.defer(ephemeral=True)

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    messages = []
    message_contents: list[tuple[int, str]] = []
    async for message in interaction.channel.history(limit=None, after=start_message, before=end_message):
        if target_user is not None and message.author != target_user:
            continue
        messages.append(message)
        message_contents.append((message.author.id, message.content))

    try:
        for index in range(0, len(messages), 100):
            await interaction.channel.delete_messages(
                messages[index : index + 100],
                reason=f"사용자 {interaction.user.id}의 명령어 사용. 사유: {reason_text}",
            )
    except discord.Forbidden:
        embed = _build_error_embed(
            "봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `메시지 관리하기` 권한이 있는지 확인해 주세요.\n- 봇이 해당 채널을 볼 수 있는지 확인해 주세요."
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="failed", reason_code="bulk_delete_forbidden")

    deleted_count = len(messages)
    await interaction.followup.send(f"**[알림]** {deleted_count}개의 메시지가 삭제되었습니다.", ephemeral=True)

    summary_embed = discord.Embed(
        title="메시지 일괄 삭제",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    summary_embed.add_field(name="대상 채널", value=f"<#{interaction.channel.id}>", inline=False)
    summary_embed.add_field(name="관리자", value=f"<@{interaction.user.id}>", inline=False)
    summary_embed.add_field(name="개수", value=f"{deleted_count}개", inline=False)
    summary_embed.add_field(
        name="대상 범위",
        value=f"{start_message_link} ~ {end_message_link}" if end_message_link else f"{start_message_link} ~",
        inline=False,
    )
    summary_embed.add_field(
        name="대상 사용자",
        value=f"<@{target_user.id}>" if target_user is not None else "모두",
        inline=False,
    )
    summary_embed.add_field(name="사유", value=reason_text, inline=False)

    log_channel = context["bot"].get_channel(context["get_log_channel"](interaction.guild.id)["editdelete"])
    if log_channel:
        await log_channel.send(embed=summary_embed)

        deleted_messages = f"<#{interaction.channel.id}>에서 여러 개의 메시지가 삭제되었습니다.\n"
        for author_id, content in message_contents:
            deleted_messages += f"- <@{author_id}>: {content}\n"
        for message_chunk in _split_text(deleted_messages):
            await log_channel.send(
                embed=discord.Embed(
                    title="메시지 일괄 삭제 로그",
                    color=discord.Color.red(),
                    description=message_chunk,
                )
            )
    else:
        print(f"메시지 일괄 삭제 로그 채널을 찾을 수 없습니다. 서버 ID: {interaction.guild.id}")

    return _slash_result(status="completed", reason_code="bulk_delete_completed")


async def run_delete_invites_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
) -> SlashCommandResult:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("이 명령어는 서버에서만 사용할 수 있습니다.", ephemeral=True)
        return _slash_result(status="rejected", reason_code="invite_delete_guild_only")

    await interaction.response.defer(thinking=True)
    invites = await guild.invites()
    deleted_count = 0
    for invite in [invite for invite in invites if invite.inviter and invite.inviter.id == target_user.id]:
        try:
            await invite.delete()
            deleted_count += 1
        except discord.Forbidden:
            embed = _build_error_embed("봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `서버 관리하기` 권한이 있는지 확인해 주세요.")
            await interaction.followup.send(embed=embed)
            return _slash_result(status="failed", reason_code="invite_delete_forbidden")

    if deleted_count == 0:
        await interaction.followup.send(f"{target_user.id}가 만든 초대 링크를 찾을 수 없습니다.")
        return _slash_result(status="completed", reason_code="invite_delete_none_found")

    await interaction.followup.send(f"{target_user.id}가 만든 초대 링크 {deleted_count}개를 삭제했습니다.")
    return _slash_result(status="completed", reason_code="invite_delete_completed")


async def run_security_action_slash_command(
    interaction: discord.Interaction,
    *,
    server_join_block_text: str,
    dm_block_text: str,
    reason_text: str,
) -> SlashCommandResult:
    if not interaction.user.guild_permissions.moderate_members:
        embed = _build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `타임아웃 멤버`")
        await interaction.response.send_message(embed=embed)
        return _slash_result(status="rejected", reason_code="security_action_missing_permission")

    await interaction.response.defer()
    try:
        dm_block_seconds = _parse_duration_to_seconds(dm_block_text)
        server_join_block_seconds = _parse_duration_to_seconds(server_join_block_text)
        if dm_block_seconds is None or server_join_block_seconds is None:
            raise ValueError("invalid duration")
    except Exception as exc:
        embed = _build_error_embed(f"시간 형식이 올바르지 않습니다. (초, 분, 시간, 일 단위 포함하여 입력)\n{exc}")
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="security_action_invalid_duration")

    if dm_block_seconds > 86400 or server_join_block_seconds > 86400:
        embed = _build_error_embed("보안조치 기간은 최대 24시간까지 설정할 수 있습니다.")
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="security_action_duration_too_large")

    await apply_guild_security_action(
        guild=interaction.guild,
        actor=interaction.user,
        server_join_block_seconds=server_join_block_seconds,
        dm_block_seconds=dm_block_seconds,
        reason_text=reason_text,
    )
    await interaction.followup.send(embed=_build_done_embed("처리되었습니다."))
    return _slash_result(status="completed", reason_code="security_action_completed")


async def run_restrict_user_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    reason_text: str,
    until_date_label: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    if interaction.user.id != context["developer"]:
        await interaction.followup.send("개발자 전용 명령어입니다.")
        return _slash_result(status="rejected", reason_code="developer_only")

    try:
        block_until = datetime.strptime(until_date_label, "%Y-%m-%d").date()
    except ValueError:
        await interaction.followup.send("기간 형식이 올바르지 않습니다. (YYYY-MM-DD 형식)")
        return _slash_result(status="rejected", reason_code="restriction_invalid_date")

    if block_until <= datetime.today().date():
        await interaction.followup.send("차단 기간은 오늘 이후여야 합니다.")
        return _slash_result(status="rejected", reason_code="restriction_past_date")

    add_developer_restriction(user_id=target_user.id, reason_text=reason_text, until_date_label=until_date_label)
    await interaction.followup.send(f"{target_user.id}님을 {until_date_label}까지 `{reason_text}`로 인해 이용제한 처리했습니다.")
    return _slash_result(status="completed", reason_code="restriction_added")


async def run_unrestrict_user_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    if interaction.user.id != context["developer"]:
        await interaction.followup.send("개발자 전용 명령어입니다.")
        return _slash_result(status="rejected", reason_code="developer_only")

    restriction_state = get_developer_restriction_state(user_id=target_user.id)
    if restriction_state.status != "blocked":
        await interaction.followup.send(f"{target_user.id}님은 차단되어 있지 않습니다.")
        return _slash_result(status="rejected", reason_code="restriction_not_found")

    remove_developer_restriction(user_id=target_user.id)
    await interaction.followup.send(f"{target_user.id}님의 이용제한을 해제했습니다.")
    return _slash_result(status="completed", reason_code="restriction_removed")


async def run_check_restriction_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
) -> SlashCommandResult:
    await interaction.response.defer()
    restriction_state = get_developer_restriction_state(user_id=target_user.id)
    if restriction_state.status == "blocked":
        await interaction.followup.send(
            f"{target_user.id}님은 `{restriction_state.reason}` 사유로 {restriction_state.blocked_until_label}까지 이용 제한 중입니다."
        )
        return _slash_result(status="completed", reason_code="restriction_checked_blocked")

    await interaction.followup.send(f"{target_user.id}님은 현재 차단 상태가 아닙니다.")
    return _slash_result(status="completed", reason_code="restriction_checked_clear")


async def run_channel_command_permission_slash_command(
    interaction: discord.Interaction,
    *,
    command_name: str,
    channel: discord.TextChannel,
    permission: str,
    role: discord.Role | None,
    user: discord.Member | None,
) -> SlashCommandResult:
    await interaction.response.defer(ephemeral=False)
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `채널 관리하기`"), ephemeral=False)
        return _slash_result(status="rejected", reason_code="channel_permission_missing_manage_channels")
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`"), ephemeral=False)
        return _slash_result(status="rejected", reason_code="channel_permission_missing_manage_roles")
    if user is not None and role is not None:
        await interaction.followup.send(embed=_build_error_embed("유저와 역할을 동시에 설정할 수 없습니다."), ephemeral=False)
        return _slash_result(status="rejected", reason_code="channel_permission_duplicate_target")
    if user is None and role is None:
        await interaction.followup.send(embed=_build_error_embed("유저 또는 역할을 설정해야 합니다."), ephemeral=False)
        return _slash_result(status="rejected", reason_code="channel_permission_missing_target")

    update_channel_command_permission(
        server_id=interaction.guild.id,
        command_name=command_name,
        channel_id=channel.id,
        permission=None if permission == "None" else permission,
        role_id=None if role is None else role.id,
        user_id=None if user is None else user.id,
    )
    await interaction.followup.send(embed=_build_done_embed("채널별 명령어 권한이 설정되었습니다."), ephemeral=False)
    return _slash_result(status="completed", reason_code="channel_permission_updated")


async def run_server_command_permission_slash_command(
    interaction: discord.Interaction,
    *,
    command_name: str,
    permission: str,
    role: discord.Role,
) -> SlashCommandResult:
    await interaction.response.defer(ephemeral=False)
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `채널 관리하기`"), ephemeral=False)
        return _slash_result(status="rejected", reason_code="server_permission_missing_manage_channels")
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`"), ephemeral=False)
        return _slash_result(status="rejected", reason_code="server_permission_missing_manage_roles")

    update_server_command_permission(
        server_id=interaction.guild.id,
        command_name=command_name,
        permission=permission,
        role_id=role.id,
    )
    await interaction.followup.send(embed=_build_done_embed("서버별 명령어 권한이 설정되었습니다."), ephemeral=False)
    return _slash_result(status="completed", reason_code="server_permission_updated")


async def run_automod_exception_channel_slash_command(
    interaction: discord.Interaction,
    *,
    channel,
    enabled: bool,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `관리자`"))
        return _slash_result(status="rejected", reason_code="automod_exception_missing_admin")

    update_automod_exception_channel_setting(server_id=interaction.guild.id, channel_id=channel.id, enabled=enabled)
    await interaction.followup.send(embed=_build_done_embed(f"채널 {channel.mention}의 자동 검열 예외 설정이 완료되었습니다."))
    return _slash_result(status="completed", reason_code="automod_exception_updated")


async def run_automod_setup_slash_command(
    interaction: discord.Interaction,
    *,
    political_enabled: bool,
    sexual_enabled: bool,
    invite_enabled: bool,
    mention_enabled: bool,
    whitelist_permission: str,
    political_timeout_seconds: int,
    sexual_timeout_seconds: int,
    invite_timeout_seconds: int,
    mention_timeout_seconds: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")
    if (political_enabled or sexual_enabled) and interaction.guild.id != context["using_server"] and interaction.user.id != context["developer"]:
        embed = _build_error_embed(
            "정치 발언 및 성적인 발언 검열 기능은 아직 여러 서버들에서 지원되지 않습니다. 이 외의 검열 설정은 사용하실 수 있습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)"
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="automod_restricted_server")
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `관리자`"))
        return _slash_result(status="rejected", reason_code="automod_missing_admin")
    if min(political_timeout_seconds, sexual_timeout_seconds, invite_timeout_seconds, mention_timeout_seconds) < 0:
        await interaction.followup.send(embed=_build_error_embed("타임아웃 기간은 0 이상이어야 합니다."))
        return _slash_result(status="rejected", reason_code="automod_negative_timeout")

    update_automod_setting(
        server_id=interaction.guild.id,
        political_enabled=political_enabled,
        political_timeout_seconds=political_timeout_seconds,
        sexual_enabled=sexual_enabled,
        sexual_timeout_seconds=sexual_timeout_seconds,
        invite_enabled=invite_enabled,
        invite_timeout_seconds=invite_timeout_seconds,
        mention_enabled=mention_enabled,
        mention_timeout_seconds=mention_timeout_seconds,
        whitelist_permission=whitelist_permission,
    )
    await interaction.followup.send(embed=_build_done_embed("자동 검열 기능 설정이 완료되었습니다."))
    return _slash_result(status="completed", reason_code="automod_updated")


async def run_set_quarantine_role_slash_command(
    interaction: discord.Interaction,
    *,
    quarantine_role: discord.Role,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_result(error_count, status="rejected", reason_code="blocked_user")
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`"), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="quarantine_role_missing_manage_roles")

    try:
        update_quarantine_role_setting(server_id=interaction.guild.id, role_id=quarantine_role.id)
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = _build_error_embed(f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.")
        await interaction.followup.send(embed=embed)
        return _tracked_result(error_count + 1, status="failed", reason_code="quarantine_role_error")

    await interaction.followup.send(embed=_build_done_embed("격리 역할이 설정되었습니다."), ephemeral=False)
    return _tracked_result(error_count, status="completed", reason_code="quarantine_role_updated")


async def run_quarantine_user_slash_command(
    interaction: discord.Interaction,
    *,
    target_user,
    context: Mapping[str, Any],
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _tracked_result(error_count, status="rejected", reason_code="blocked_user")
    if target_user.top_role >= interaction.user.top_role:
        await interaction.followup.send(
            embed=_build_error_embed("역할 회수 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다."),
            ephemeral=False,
        )
        return _tracked_result(error_count, status="rejected", reason_code="quarantine_role_hierarchy")

    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(embed=_build_error_embed("guild_only_command"), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="quarantine_guild_only")

    member = guild.get_member(target_user.id)
    if member is None:
        await interaction.followup.send(embed=_build_error_embed("해당 사용자를 찾을 수 없습니다."), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="quarantine_member_missing")

    if guild.id == context["using_server"]:
        author_member = guild.get_member(interaction.user.id)
        if author_member is None or discord.utils.get(author_member.roles, id=context["admin_role_id"]) is None:
            await interaction.followup.send(
                embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `관리자` 또는 `부관리자`"),
                ephemeral=False,
            )
            return _tracked_result(error_count, status="rejected", reason_code="quarantine_missing_admin_role")
    elif not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send(embed=_build_error_embed("권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`"), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="quarantine_missing_manage_roles")

    quarantine_role_id = get_quarantine_role_id(server_id=guild.id)
    quarantine_role = guild.get_role(quarantine_role_id)
    if quarantine_role is None:
        await interaction.followup.send(embed=_build_error_embed("격리 역할의 값이 올바르지 않습니다."), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="quarantine_role_missing")

    try:
        for role in member.roles[1:]:
            await member.remove_roles(role, reason=f"사용자 {interaction.user.display_name}({interaction.user.id})의 /격리 명령어 사용")
        await member.add_roles(quarantine_role, reason=f"사용자 {interaction.user.display_name}({interaction.user.id})의 /격리 명령어 사용")
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = _build_error_embed(f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.")
        await interaction.followup.send(embed=embed)
        return _tracked_result(error_count + 1, status="failed", reason_code="quarantine_apply_error")

    await interaction.followup.send(
        embed=_build_done_embed(f"{target_user.mention}의 모든 역할을 회수하고 조사/격리 필요 역할을 부여했습니다."),
        ephemeral=False,
    )
    return _tracked_result(error_count, status="completed", reason_code="quarantine_applied")


async def run_anti_nuke_setting_slash_command(
    interaction: discord.Interaction,
    *,
    enabled_label: str,
    log_channel: discord.TextChannel,
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    await interaction.response.defer()
    if interaction.guild is None:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 서버에서만 사용 가능합니다."), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="anti_nuke_guild_only")
    if interaction.guild.owner.id != interaction.user.id:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 서버 주인만 사용 가능합니다."), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="anti_nuke_owner_only")

    try:
        enabled = enabled_label == "활성화"
        update_anti_nuke_setting(server_id=interaction.guild.id, enabled=enabled, log_channel_id=log_channel.id)
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = _build_error_embed(f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.")
        await interaction.followup.send(embed=embed)
        return _tracked_result(error_count + 1, status="failed", reason_code="anti_nuke_update_error")

    description = (
        "테러 방지 기능 옵션이 아래와 같이 설정되었습니다: \n\n"
        f"- 추방/차단 테러 방지: {enabled}\n"
        f"- 로그 채널: <#{log_channel.id}>\n\n"
        "테러방지 기능을 더 안전하게 사용하기 위한 권장사항을 확인해보세요: "
        "- 마늘이 보안 기능과 타 봇 보안 기능을 동시에 사용 시에는 타 봇 보안 기능에서 마늘이를 테러방지 화이트리스트에 추가 및 마늘이 화이트리스트에 타 보안 봇을 추가하시는 것을 권장합니다.\n"
        "- 테러방지 기능 로그 채널은 운영진이 볼 수 없고, 서버 소유자만 볼 수 있는 채널로 설정하시는 것을 권장합니다."
    )
    await interaction.followup.send(embed=_build_done_embed(description), ephemeral=False)
    return _tracked_result(error_count, status="completed", reason_code="anti_nuke_updated")


async def run_anti_nuke_whitelist_slash_command(
    interaction: discord.Interaction,
    *,
    target_user: discord.User,
    enabled_label: str,
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    await interaction.response.defer()
    if interaction.guild is None:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 서버에서만 사용 가능합니다."), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="anti_nuke_whitelist_guild_only")
    if interaction.guild.owner.id != interaction.user.id:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 서버 주인만 사용 가능합니다."), ephemeral=False)
        return _tracked_result(error_count, status="rejected", reason_code="anti_nuke_whitelist_owner_only")

    try:
        enabled = enabled_label == "활성화"
        update_anti_nuke_whitelist_setting(server_id=interaction.guild.id, user_id=target_user.id, enabled=enabled)
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = _build_error_embed(f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.")
        await interaction.followup.send(embed=embed)
        return _tracked_result(error_count + 1, status="failed", reason_code="anti_nuke_whitelist_error")

    await interaction.followup.send(
        embed=_build_done_embed(
            f"<@{target_user.id}>의 테러 방지 기능 화이트리스트 설정이 아래와 같이 설정되었습니다:\n\n- 추방/차단 테러 방지: {enabled}"
        ),
        ephemeral=False,
    )
    return _tracked_result(error_count, status="completed", reason_code="anti_nuke_whitelist_updated")
