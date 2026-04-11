from __future__ import annotations

from discord import Interaction
from discord.app_commands import Choice

from bot_app.services.rail_service import create_rail, create_route, delete_route, update_route_dispatch_interval
from bot_app.types.readability_contracts import SlashCommandResult


def _slash_result(*, status: str, reason_code: str) -> SlashCommandResult:
    return SlashCommandResult(status=status, reason_code=reason_code)


async def run_make_rail_slash_command(
    interaction: Interaction,
    *,
    rail_name: str,
    rail_count: int,
) -> SlashCommandResult:
    rail_creation_result = create_rail(
        user_id=interaction.user.id,
        channel_id=interaction.channel_id,
        rail_name=rail_name,
        rail_count=rail_count,
    )
    if rail_creation_result.status == "created":
        await interaction.response.send_message(
            f"**[알림]** 선로 개수가 {rail_creation_result.rail_count}인 {rail_creation_result.rail_name} 선로를 건설했습니다!"
        )
        return _slash_result(status="completed", reason_code="rail_created")
    if rail_creation_result.status == "already_exists":
        await interaction.response.send_message(
            "**[오류!]** 오류가 발생했습니다! 이 오류는 일반적으로 이미 선로가 건설되어 있는 경우에 표시됩니다."
        )
        return _slash_result(status="failed", reason_code="rail_already_exists")
    if rail_creation_result.status == "too_many_tracks":
        await interaction.response.send_message("**[오류!]** 복복선보다 많은 선로를 가진 노선을 건설할 수 없습니다.")
        return _slash_result(status="rejected", reason_code="rail_count_too_large")
    await interaction.response.send_message("**[오류!]** 입력값이 올바르지 않습니다.")
    return _slash_result(status="rejected", reason_code="invalid_input")


async def run_make_route_slash_command(
    interaction: Interaction,
    *,
    route_name: str,
    train_choice: Choice[str],
    dispatch_interval: int,
) -> SlashCommandResult:
    await interaction.response.defer()
    route_creation_result = create_route(
        user_id=interaction.user.id,
        channel_id=interaction.channel_id,
        route_name=route_name,
        train_name=train_choice.value,
        dispatch_interval=dispatch_interval,
    )
    if route_creation_result.status == "created":
        await interaction.followup.send("**[알림]** 운행계통을 신설했습니다.")
        return _slash_result(status="completed", reason_code="route_created")
    if route_creation_result.status == "rail_missing":
        await interaction.followup.send("**[오류!]** 선로가 건설되어 있지 않은 채널입니다. 선로를 먼저 건설해 주세요.")
        return _slash_result(status="rejected", reason_code="rail_missing")
    if route_creation_result.status == "duplicate_name":
        await interaction.followup.send(
            "**[오류!]** 오류가 발생했습니다! 이 오류는 일반적으로 이미 같은 이름의 운행계통이 있는 경우 표시됩니다."
        )
        return _slash_result(status="failed", reason_code="route_duplicate_name")
    if route_creation_result.status == "temporary_single_route_limit":
        await interaction.followup.send(
            "**[오류!]** 하나의 노선에는 하나의 운행계통만 신설할 수 있도록 임시로 개발되었습니다. 추후 업데이트를 통해 수정될 예정입니다."
        )
        return _slash_result(status="rejected", reason_code="temporary_single_route_limit")
    await interaction.followup.send("**[오류!]** 입력값이 올바르지 않습니다.")
    return _slash_result(status="rejected", reason_code="invalid_input")


async def run_delete_route_slash_command(
    interaction: Interaction,
    *,
    route_name: str,
) -> SlashCommandResult:
    await interaction.response.defer()
    route_deletion_result = delete_route(
        user_id=interaction.user.id,
        channel_id=interaction.channel_id,
        route_name=route_name,
    )
    if route_deletion_result.status == "deleted":
        await interaction.followup.send("**[알림]** 운행계통을 삭제했습니다.")
        return _slash_result(status="completed", reason_code="route_deleted")
    if route_deletion_result.status == "permission_denied":
        await interaction.followup.send("**[오류!]** 운행계통 삭제 권한이 부족합니다. 운행계통 소유자(이)여야 합니다.")
        return _slash_result(status="rejected", reason_code="route_permission_denied")
    await interaction.followup.send("**[오류!]** 입력값이 올바르지 않습니다.")
    return _slash_result(status="rejected", reason_code="route_missing")


async def run_update_route_dispatch_interval_slash_command(
    interaction: Interaction,
    *,
    route_name: str,
    dispatch_interval: int,
) -> SlashCommandResult:
    await interaction.response.defer()
    route_update_result = update_route_dispatch_interval(
        user_id=interaction.user.id,
        channel_id=interaction.channel_id,
        route_name=route_name,
        dispatch_interval=dispatch_interval,
    )
    if route_update_result.status == "updated":
        await interaction.followup.send("**[알림]** 운행계통 배차 간격을 수정했습니다.")
        return _slash_result(status="completed", reason_code="route_dispatch_interval_updated")
    if route_update_result.status == "permission_denied":
        await interaction.followup.send("**[오류!]** 운행계통 편집 권한이 부족합니다. 운행계통 소유자(이)여야 합니다.")
        return _slash_result(status="rejected", reason_code="route_permission_denied")
    if route_update_result.status == "interval_too_small":
        await interaction.followup.send("**[오류!]** 입력값이 올바르지 않습니다. dispatch_interval의 값은 2 이상(이)어야 합니다.")
        return _slash_result(status="rejected", reason_code="dispatch_interval_too_small")
    await interaction.followup.send("**[오류!]** 입력값이 올바르지 않습니다.")
    return _slash_result(status="rejected", reason_code="invalid_input")
