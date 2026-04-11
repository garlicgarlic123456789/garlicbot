from __future__ import annotations

import discord

from bot_app.services.settings_service import update_guild_log_channels
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, GuildLogChannelSelection


def _tracked_slash_result(
    error_count: int,
    *,
    status: str,
    reason_code: str | None = None,
) -> ErrorTrackedSlashCommandResult:
    return ErrorTrackedSlashCommandResult(status=status, error_count=error_count, reason_code=reason_code)


def _channel_id(channel: discord.TextChannel | None) -> int | None:
    return None if channel is None else channel.id


async def run_set_log_channel_slash_command(
    interaction: discord.Interaction,
    *,
    editdelete_channel: discord.TextChannel | None,
    reaction_channel: discord.TextChannel | None,
    role_channel: discord.TextChannel | None,
    block_channel: discord.TextChannel | None,
    image_channel: discord.TextChannel | None,
    error_count: int,
) -> ErrorTrackedSlashCommandResult:
    await interaction.response.defer(ephemeral=False)
    selection = GuildLogChannelSelection(
        editdelete=_channel_id(editdelete_channel),
        reaction=_channel_id(reaction_channel),
        role=_channel_id(role_channel),
        image=_channel_id(image_channel),
        block=0 if block_channel is None else block_channel.id,
    )

    try:
        update_guild_log_channels(server_id=interaction.guild.id, selection=selection)
    except Exception as exc:
        print(f"오류 #{error_count}: {exc}")
        embed = discord.Embed(
            title="오류",
            description=f"오류 #{error_count}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_slash_result(error_count + 1, status="failed", reason_code="log_channel_update_error")

    embed = discord.Embed(
        title="완료",
        description="로그 채널 설정이 완료되었습니다.",
        color=int("a5f0ff", 16),
    )
    await interaction.followup.send(embed=embed)
    return _tracked_slash_result(error_count, status="completed", reason_code="log_channel_updated")
