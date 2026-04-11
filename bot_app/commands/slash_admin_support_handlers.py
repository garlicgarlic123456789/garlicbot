from __future__ import annotations

import asyncio
import os
import re
import statistics
from datetime import datetime, timedelta
from typing import Any, Mapping

import aiohttp
import discord

from bot_app.services.admin_support_service import (
    add_blockhistory_entry,
    build_channel_backup_message,
    build_invite_route_report,
    build_role_info_snapshot,
    delete_blockhistory_entry,
    get_user_join_route_entry,
    load_channel_backup_manifest,
    update_invite_route_memo_entry,
    update_role_description_entry,
    update_user_join_route_entry,
    write_channel_backup_manifest,
)
from bot_app.types.readability_contracts import ChannelBackupManifest, SlashCommandResult, UserBlockState


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


def _build_permission_embed(description: str) -> discord.Embed:
    return discord.Embed(title="오류", description=description, color=discord.Color.red())


def _build_completed_embed(description: str) -> discord.Embed:
    return discord.Embed(title="완료", description=description, color=int("a5f0ff", 16))


async def run_developer_command_slash_command(
    interaction: discord.Interaction,
    *,
    command_id: int,
    input1: str | None,
    input2: str | None,
    input3: str | None,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    """Move the sprawling 개발명령 implementation behind a helper boundary without changing UX."""
    if interaction.user.id != context["developer"]:
        await interaction.response.send_message("개발자 전용입니다.")
        return _slash_result(status="rejected", reason_code="missing_developer_permission")

    if command_id == 1:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("더 이상 사용되지 않는 개발 명령어입니다. 커밋 4da0d33을 확인하세요.")
        return _slash_result(status="completed", reason_code="deprecated_command_1")
    if command_id == 2:
        await interaction.response.defer(ephemeral=True)
        if input1 is not None:
            develop_chat_sessions = context["develop_chat_dict2"]
            if develop_chat_sessions.get(interaction.user.id) is not None:
                response = await asyncio.to_thread(
                    develop_chat_sessions[interaction.user.id].send_message,
                    f"사용자명: {interaction.user.display_name}\n사용자의 입력: {input1}",
                    generation_config=context["genai"].types.GenerationConfig(temperature=2.0),
                )
            else:
                develop_chat_sessions[interaction.user.id] = await asyncio.to_thread(context["cute_model4"].start_chat)
                response = await asyncio.to_thread(
                    develop_chat_sessions[interaction.user.id].send_message,
                    f"사용자명: {interaction.user.display_name}\n사용자의 입력: {input1}",
                    generation_config=context["genai"].types.GenerationConfig(temperature=2.0),
                )
            print(response.text)
            match = re.search(r"응답:\s*(.*?)\s*\n호감도:\s*([+-]?\d+)", response.text, re.MULTILINE)
            if match:
                response_text = match.group(1)
                favorability = int(match.group(2))
                await interaction.followup.send(response_text)
                context["add_likeability"](interaction.user.id, favorability)
        return _slash_result(status="completed", reason_code="developer_command_2")
    if command_id == 3:
        await interaction.response.defer(ephemeral=True)
        channel = context["bot"].get_channel(int(input1)) if input1 is not None else context["bot"].get_channel(context["normal_channel"])
        if channel:
            if context["add_or_remove"]():
                embed = discord.Embed(title="무료 경험치 받기", description="아래 '경험치 받기' 버튼을 클릭하고 무료로 150~1000마늘(XP)를 받으세요!", color=int("a5f0ff", 16))
                await channel.send(embed=embed, view=context["ExpButton"]())
            else:
                embed = discord.Embed(title="무료 경험치 받기", description="아래 '경험치 받기' 버튼을 클릭하고 무료로 150~1000마늘(XP)를 잃으세요!", color=int("a5f0ff", 16))
                await channel.send(embed=embed, view=context["ExpRemoveButton"]())
            await interaction.followup.send("처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_3")
    if command_id == 4:
        user1 = await context["bot"].fetch_user(int(input1))
        user2 = await context["bot"].fetch_user(int(input2))
        await context["오리실험"](interaction, user1, user2)
        return _slash_result(status="completed", reason_code="developer_command_4")
    if command_id == 5:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("더 이상 사용되지 않는 개발 명령어입니다. 커밋 55983bc를 확인하세요.")
        return _slash_result(status="completed", reason_code="deprecated_command_5")
    if command_id == 6:
        await interaction.response.defer()
        target_server_id = int(input1)
        await interaction.followup.send(
            f"서버 {target_server_id}: {context['get_anti_nuke_option'](target_server_id)}, <#{context['get_anti_nuke_log_channel'](target_server_id)}>"
        )
        return _slash_result(status="completed", reason_code="developer_command_6")
    if command_id == 7:
        await interaction.response.defer()
        target_server_id = int(input1)
        target_user_id = int(input2)
        await interaction.followup.send(
            f"서버 {target_server_id}의 유저 {target_user_id}: {context['get_anti_nuke_whitelist'](target_server_id, target_user_id)}"
        )
        return _slash_result(status="completed", reason_code="developer_command_7")
    if command_id == 8:
        await interaction.response.defer()
        for command in context["bot"].tree.get_commands():
            print(f"Command: {command.name}")
        await interaction.followup.send("동기화된 명령어 목록을 콘솔에 출력했습니다.")
        return _slash_result(status="completed", reason_code="developer_command_8")
    if command_id == 9:
        await interaction.response.defer()
        print(context["get_asos_data_current"](context["weather_api_key"]))
        await interaction.followup.send("완료!")
        return _slash_result(status="completed", reason_code="developer_command_9")
    if command_id == 10:
        await interaction.response.defer()
        await interaction.followup.send(f"제재 로그 채널: {context['get_block_log_channel'](interaction.guild.id)}")
        return _slash_result(status="completed", reason_code="developer_command_10")
    if command_id == 11:
        await interaction.response.defer(ephemeral=True)
        start_date = input1
        end_date = input2
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=context["KST"])
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=context["KST"]) + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            await interaction.followup.send("❗ 날짜 형식이 잘못되었습니다. `YYYY-MM-DD` 형식으로 입력해주세요.")
            return _slash_result(status="rejected", reason_code="developer_command_invalid_date")

        await interaction.followup.send(f"📊 `{start_date}`부터 `{end_date}`까지(KST 기준) 채팅 건수를 계산 중입니다...", ephemeral=True)
        data = []
        text_channels = interaction.guild.text_channels
        for index, channel in enumerate(text_channels, 1):
            try:
                print(f"🔍 [{index}/{len(text_channels)}] 채널 처리 중: {channel.name}")
                async for message in channel.history(after=start, before=end, oldest_first=True, limit=None):
                    if not message.author.bot and message.created_at is not None:
                        created_kst = message.created_at.astimezone(context["KST"])
                        time_key = created_kst.replace(minute=0, second=0, microsecond=0)
                        data.append({"채널": channel.name, "시간(KST)": time_key.strftime("%Y-%m-%d %H:00")})
            except discord.Forbidden:
                print(f"⚠️ 접근 불가 채널 스킵: {channel.name}")
            await asyncio.sleep(0.2)

        df = context["pd"].DataFrame(data)
        if df.empty:
            await interaction.user.send("📭 지정된 기간 동안 수집된 유효한 메시지가 없습니다.")
            return _slash_result(status="completed", reason_code="developer_command_no_messages")

        grouped = df.groupby(["채널", "시간(KST)"]).size().reset_index(name="건수")
        grouped.sort_values(by=["시간(KST)", "채널"], inplace=True)
        filename = f"chat_counts_{start_date}_{end_date}_KST.csv"
        grouped.to_csv(filename, index=False, encoding="utf-8-sig")
        await interaction.user.send(file=discord.File(filename))
        return _slash_result(status="completed", reason_code="developer_command_11")
    if command_id == 12:
        await interaction.response.defer()
        context["migrate_blockhistory"](int(input1), int(input2), interaction.guild.id)
        await interaction.followup.send("처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_12")
    if command_id == 13:
        await interaction.response.defer()
        user_id = int(input1)
        guild = interaction.guild
        bans = [entry async for entry in guild.bans()]
        banned_user = next((ban for ban in bans if ban.user.id == user_id), None)
        banned = banned_user is not None
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            member = None

        related_accounts = context["get_related_accounts"](user_id)
        related_accounts.remove(user_id)
        all_account_count = len(related_accounts)
        timeout_success = 0
        ban_success = 0
        if len(related_accounts) > 0:
            for related_user_id in related_accounts:
                try:
                    if banned:
                        await guild.ban(discord.Object(id=related_user_id), reason=f"{input1}, {related_user_id} 다중 계정", delete_message_seconds=0)
                        ban_success += 1
                    else:
                        await guild.unban(discord.Object(id=related_user_id), reason=f"{input1}, {related_user_id} 다중 계정")
                        ban_success += 1
                except Exception as error:
                    print(f"Error (un)banning user {related_user_id}: {error}")
                if member is not None:
                    try:
                        member2 = await guild.fetch_member(related_user_id)
                        timeout_value = member.timed_out_until
                        await member2.edit(timed_out_until=timeout_value, reason=f"{input1}, {related_user_id} 다중 계정")
                        timeout_success += 1
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        pass
        await interaction.followup.send(
            f"처리되었습니다. {user_id}의 다중 계정 {all_account_count}개를 처리했습니다.\n\n- 타임아웃: {timeout_success}개\n- 차단: {ban_success}개"
        )
        return _slash_result(status="completed", reason_code="developer_command_13")
    if command_id == 14:
        await interaction.response.defer(ephemeral=True)
        await context["scan_url"](input1)
        await interaction.followup.send("처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_14")
    if command_id == 15:
        await interaction.response.defer()
        context["save_invite_log"](int(input1), input2, interaction.guild.id)
        await interaction.followup.send(f"유저 {input1}: 처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_15")
    if command_id == 16:
        await interaction.response.defer()
        print(context["get_automod"](interaction.guild.id))
        await interaction.followup.send("실행된 서버의 검열 기능 설정을 콘솔에 출력했습니다.")
        return _slash_result(status="completed", reason_code="developer_command_16")
    if command_id == 17:
        await interaction.response.defer(ephemeral=True)
        await context["check_account"](int(input1))
        await interaction.followup.send("처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_17")
    if command_id == 18:
        await interaction.response.defer(ephemeral=True)
        member_counts = [guild.member_count for guild in context["bot"].guilds if guild.member_count is not None]
        total_members = sum(member_counts)
        if member_counts:
            mean_members = statistics.mean(member_counts)
            stdev_members = statistics.stdev(member_counts) if len(member_counts) > 1 else 0.0
        else:
            mean_members = 0.0
            stdev_members = 0.0
        await interaction.followup.send(
            f"봇이 추가된 모든 서버의 인원 수 총합: {total_members}명\n"
            f"평균: {mean_members:.2f}명\n"
            f"표준편차: {stdev_members:.2f}명"
        )
        return _slash_result(status="completed", reason_code="developer_command_18")
    if command_id == 19:
        await interaction.response.defer()
        embed = discord.Embed(title="오류", description="폐지된 명령입니다.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="deprecated_command_19")
    if command_id == 20:
        await interaction.response.defer()
        setting_raw = context["get_xp_setting"](interaction.guild.id)
        setting_dict = context["get_xp_setting_dict"](interaction.guild.id)
        await interaction.followup.send(f"경험치 기능 설정값:\n- db: {setting_raw}\n- 딕셔너리: {setting_dict}")
        return _slash_result(status="completed", reason_code="developer_command_20")
    if command_id == 21:
        await interaction.response.defer()
        xp_value = context["get_xp"](interaction.guild.id, interaction.user.id)
        await interaction.followup.send(f"경험치: {xp_value}")
        return _slash_result(status="completed", reason_code="developer_command_21")
    if command_id == 22:
        await interaction.response.send_message("폐지된 개발 명령.")
        return _slash_result(status="rejected", reason_code="deprecated_command_22")
    if command_id == 23:
        await interaction.response.send_message("폐지된 개발 명령.")
        return _slash_result(status="rejected", reason_code="deprecated_command_23")
    if command_id == 24:
        await interaction.response.send_message("폐지된 개발 명령.")
        return _slash_result(status="rejected", reason_code="deprecated_command_24")
    if command_id == 25:
        await interaction.response.send_message("폐지된 개발 명령.")
        return _slash_result(status="rejected", reason_code="deprecated_command_25")
    if command_id == 26:
        input1_value = input1 is not None and input1 == "True"
        await interaction.response.defer()
        warnings = context["load_warnings"](input1_value)
        for key, value in warnings.items():
            pieces = key.split("/")
            if len(pieces) != 2:
                continue
            await context["set_warning"](int(pieces[0]), int(pieces[1]), value)
        await interaction.followup.send("처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_26")
    if command_id == 27:
        target = datetime(2025, 11, 25, 0, 0, 0)
        if not datetime.now() < target:
            raise context["ObsoleteFunctionError"]("더 이상 사용되지 않는 개발 명령입니다.")
        temp = context["get_all_xp"](interaction.guild.id)
        for key, value in temp.items():
            context["update_month_xp"](interaction.guild.id, key, value)
        await interaction.followup.send("완료되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_27")
    if command_id == 28:
        target = datetime(2026, 1, 25, 0, 0, 0)
        if not datetime.now() < target:
            raise context["ObsoleteFunctionError"]("2026년 1월 25일 0시 0분 0초 이후로 더 이상 사용될 일이 없는 개발 명령입니다. '입력1'의 값을 True로 설정하여 이 개발 명령을 강제로 실행할 수 있습니다. **이 개발 명령이 무엇을 하는지 정확히 아는 것이 아니라면 테스트 환경에서만 실행하십시오..**")

        await interaction.response.send_message("처리 중입니다.")
        message = await interaction.original_response()
        channel_list = await context["get_all_anti_nuke_notify_channel"](True)
        embed = discord.Embed(
            title="긴급 공지",
            description="이 서버는 과거 봇의 테러 방지 기능을 설정했던 것으로 보입니다. 그러나, 봇의 버그로 인해 테러 방지 기능이 제대로 설정되지 않은 것으로 확인됩니다. 우선 봇의 버그를 사전에 확인하여 조치하지 못하고, 이런 일로 심려를 끼려드린 점 사과드립니다..\n\n현재 봇의 db에 테러 방지 기능 사용 여부는 제대로 저장되지 않고 테러 방지 기능 작동 로그 채널만 저장된 것으로 보입니다. 따라서 현재까지 테러 방지 기능 로그 채널만 설정되고 테러 방지 기능 자체는 사용 설정되지 않은 상태였습니다..\n\n테러 방지 기능을 지속해서 사용하시려는 경우, 아래 버튼을 클릭하시면, 테러 방지 기능이 정상적으로 사용 설정됩니다. (버튼이 작동하지 않는 경우 `/테러방지설정` 명령어 사용 부탁드립니다.) 기능을 더 이상 사용하지 않으시려는 경우, 취해야 할 조치는 없습니다.\n\n다시 한 번 이런 일로 심려를 끼쳐 드려 죄송하다는 말씀 드리며, 앞으로 더 안정적인 봇 운영을 위해 노력하겠습니다. 추가적인 문의사항은 asdfasdf_123456789 계정에 친추 후 문의해주시면 감사하겠습니다.",
            color=discord.Color.red(),
        )
        for server_id, channel_id in channel_list:
            guild = context["bot"].get_guild(server_id)
            if guild is None:
                continue
            channel = guild.get_channel(channel_id)
            if channel is None:
                continue
            try:
                await channel.send(f"<@{guild.owner_id}>", embed=embed, view=context["enable_anti_nuke_button_temp"]())
                print(f"서버 {guild.name} ({server_id}) / 채널 {channel.name} ({channel_id}) - 전송 성공")
            except Exception:
                try:
                    await channel.send(embed=embed, view=context["enable_anti_nuke_button_temp"]())
                    print(f"서버 {guild.name} ({server_id}) / 채널 {channel.name} ({channel_id}) - 무멘션 전송 성공")
                except Exception as nested_error:
                    print(f"메시지 전송 실패: 서버 {guild.name} ({server_id}) / 채널 {channel.name} ({channel_id}) / {nested_error}")
            await message.reply("처리되었습니다.")
        return _slash_result(status="completed", reason_code="developer_command_28")

    await interaction.response.send_message("존재하지 않는 개발 명령입니다.")
    return _slash_result(status="rejected", reason_code="unknown_developer_command")


async def run_resolve_post_slash_command(
    interaction: discord.Interaction,
    *,
    resolved: bool,
    reason_text: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    if isinstance(interaction.channel, discord.Thread) and interaction.channel.parent.id == context["forum_parent_id"]:
        if resolved:
            applied_tags = [interaction.channel.parent.get_tag(context["resolved_tag_id"])]
        else:
            applied_tags = [interaction.channel.parent.get_tag(context["unresolved_tag_id"])]
        await interaction.channel.edit(
            applied_tags=applied_tags,
            reason=f"{interaction.user.display_name}({interaction.user.id})의 /해결처리 명령어 사용 (사유: {reason_text})",
        )
        embed = discord.Embed(title="완료", color=int("a5f0ff", 16))
        if resolved:
            embed.description = f"{interaction.user.mention}님이 해당 이슈를 해결 상태로 수정했습니다. \n\n사유: {reason_text}"
        else:
            embed.description = f"{interaction.user.mention}님이 해당 이슈를 답변 필요 상태로 수정했습니다. \n\n사유: {reason_text}"
        await interaction.followup.send(embed=embed)
        return _slash_result(status="completed", reason_code="issue_resolution_updated")

    embed = discord.Embed(
        title="오류",
        description="이 명령어는 특정 채널에서만 사용 가능합니다.",
        color=discord.Color.red(),
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="rejected", reason_code="invalid_channel")


async def run_update_role_description_slash_command(
    interaction: discord.Interaction,
    *,
    role,
    description: str | None,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send(embed=_build_permission_embed("권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`"))
        return _slash_result(status="rejected", reason_code="missing_manage_roles_permission")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    if description is not None and len(description) > 500:
        await interaction.followup.send(embed=_build_permission_embed("설명의 길이가 너무 깁니다. 500자 이하로 입력해 주세요."))
        return _slash_result(status="rejected", reason_code="description_too_long")

    update_role_description_entry(server_id=interaction.guild.id, role_id=role.id, description=description)
    await interaction.followup.send(embed=discord.Embed(title="성공", description="역할 설명이 수정되었습니다.", color=int("a5f0ff", 16)))
    return _slash_result(status="completed", reason_code="role_description_updated")


async def run_role_info_slash_command(
    interaction: discord.Interaction,
    *,
    role,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    snapshot = build_role_info_snapshot(
        role=role,
        server_id=interaction.guild.id,
        permission_map=context["permission_map"],
    )
    if len(snapshot.member_mentions) > 30:
        displayed_mentions = snapshot.member_mentions[:30]
        remainder = len(snapshot.member_mentions) - 30
        member_text = f"{', '.join(displayed_mentions)} 외 {remainder}명"
    elif len(snapshot.member_mentions) == 0:
        member_text = "*(멤버 없음)*"
    else:
        member_text = ", ".join(snapshot.member_mentions)
    permissions_text = ", ".join(snapshot.enabled_permissions) if snapshot.enabled_permissions else "*(권한 없음)*"
    cannot_moderate_text = ", ".join(snapshot.cannot_moderate_role_mentions) if snapshot.cannot_moderate_role_mentions else "*(제재 불가능한 역할 없음)*"

    embed = discord.Embed(
        title="역할 정보",
        description=(
            f"- 역할 이름: {snapshot.role_name}\n"
            f"- 역할 멘션: {snapshot.role_mention}\n"
            f"- 역할 ID: {snapshot.role_id}\n"
            f"- 색상: {snapshot.color_label}\n"
            f"- 멤버 수: {snapshot.member_count}\n"
            f"- 역할 설명: {snapshot.description}\n"
            f"- 부여된 권한: {permissions_text}\n"
            f"- 멤버: {member_text}\n"
            f"- 관리가 불가능한 역할: {cannot_moderate_text}"
        ),
        color=role.color,
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="role_info_checked")


async def run_set_user_join_route_slash_command(
    interaction: discord.Interaction,
    *,
    target_user,
    join_route: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer(ephemeral=True)
    if interaction.guild.id != context["using_server"]:
        embed = discord.Embed(
            title="오류",
            description="이 기능은 아직 여러 서버들에서 지원되지 않습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="unsupported_server")
    if interaction.user.id != context["developer"]:
        await interaction.followup.send(embed=_build_permission_embed("이 기능은 개발자만 사용할 수 있습니다."))
        return _slash_result(status="rejected", reason_code="missing_developer_permission")

    update_user_join_route_entry(user_id=target_user.id, join_route=join_route)
    await interaction.followup.send(embed=_build_completed_embed(f"{target_user.mention}님의 유입 경로가 성공적으로 설정되었습니다."))
    return _slash_result(status="completed", reason_code="join_route_updated")


async def run_check_user_join_route_slash_command(
    interaction: discord.Interaction,
    *,
    target_user,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id != context["developer"]:
        await interaction.followup.send(embed=_build_permission_embed("이 기능은 개발자만 사용할 수 있습니다."))
        return _slash_result(status="rejected", reason_code="missing_developer_permission")

    lookup = get_user_join_route_entry(user_id=target_user.id)
    if lookup.status == "missing":
        embed = discord.Embed(
            title="오류",
            description=f"{target_user.mention}님의 구분 역할은 설정되지 않았습니다.",
            color=discord.Color.red(),
        )
    else:
        embed = discord.Embed(
            title="완료",
            description=f"{target_user.mention}님의 구분 역할은 다음과 같습니다:\n\n{lookup.join_route}",
            color=int("a5f0ff", 16),
        )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="join_route_checked")


async def run_set_invite_route_memo_slash_command(
    interaction: discord.Interaction,
    *,
    invite_code: str,
    memo: str | None,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer(ephemeral=True)
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    await update_invite_route_memo_entry(server_id=interaction.guild.id, invite_code=invite_code, memo=memo)
    await interaction.followup.send(embed=_build_completed_embed("완료되었습니다."))
    return _slash_result(status="completed", reason_code="invite_route_memo_updated")


async def run_check_invite_route_slash_command(
    interaction: discord.Interaction,
    *,
    target_user,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    await interaction.response.defer(ephemeral=True)
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    report = await build_invite_route_report(server_id=interaction.guild.id, user_id=target_user.id)
    if report.status == "unknown":
        embed = discord.Embed(
            title="완료",
            description=f"**{target_user.mention}**님의 유입 경로는 다음과 같습니다:\n\n*(알 수 없음)*",
            color=int("a5f0ff", 16),
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="completed", reason_code="invite_route_unknown")

    rendered_labels = [entry.rendered_label for entry in report.entries]
    if len(rendered_labels) > 2:
        route_text = ", ".join(rendered_labels)
    else:
        route_text = rendered_labels[0]
    embed = discord.Embed(
        title="완료",
        description=f"**{target_user.mention}**님의 유입 경로는 다음과 같습니다:\n\n{route_text}",
        color=int("a5f0ff", 16),
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="invite_route_checked")


async def run_delete_blockhistory_entry_slash_command(
    interaction: discord.Interaction,
    *,
    entry_id: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if interaction.user.id != context["developer"]:
        await interaction.response.send_message(embed=_build_permission_embed("권한이 부족합니다. 다음 권한이 필요합니다: `개발자`"))
        return _slash_result(status="rejected", reason_code="missing_developer_permission")
    await interaction.response.defer()
    delete_blockhistory_entry(entry_id=entry_id)
    await interaction.followup.send(f"제재 내역 #{entry_id} 삭제되었습니다.")
    return _slash_result(status="completed", reason_code="blockhistory_deleted")


async def run_add_blockhistory_entry_slash_command(
    interaction: discord.Interaction,
    *,
    target_user,
    admin_user,
    reason_text: str,
    type_label: str,
    extra_value: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if interaction.user.id != context["developer"]:
        await interaction.response.send_message(embed=_build_permission_embed("권한이 부족합니다. 다음 권한이 필요합니다: `개발자`"))
        return _slash_result(status="rejected", reason_code="missing_developer_permission")
    await interaction.response.defer(ephemeral=True)
    add_blockhistory_entry(
        user_id=target_user.id,
        admin_id=admin_user.id,
        reason=reason_text,
        type_label=type_label,
        extra_value=extra_value,
        server_id=interaction.guild.id,
    )
    embed = discord.Embed(title="완료", description="처리되었습니다.", color=discord.Color.blue())
    await interaction.followup.send(embed=embed, ephemeral=True)
    return _slash_result(status="completed", reason_code="blockhistory_added")


async def run_backup_channel_slash_command(
    interaction: discord.Interaction,
    *,
    backup_name: str,
    limit: int,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if interaction.guild.id != context["using_server"]:
        embed = discord.Embed(
            title="오류",
            description="이 기능은 아직 여러 서버들에서 지원되지 않습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return _slash_result(status="rejected", reason_code="unsupported_server")
    if interaction.user.id != context["developer"]:
        await interaction.response.send_message("**[오류!]** 권한이 부족합니다.", ephemeral=True)
        return _slash_result(status="rejected", reason_code="missing_developer_permission")

    await interaction.response.defer(ephemeral=True)
    backup_path = os.path.join(context["backup_folder"], backup_name)
    os.makedirs(backup_path, exist_ok=True)
    filename_index = 0
    backup_messages = []
    async for message in interaction.channel.history(limit=limit):
        attachment_names = []
        for attachment in message.attachments:
            stored_name = f"{filename_index}_{attachment.filename}"
            attachment_names.append(stored_name)
            file_path = os.path.join(backup_path, stored_name)
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        with open(file_path, "wb") as file_handle:
                            file_handle.write(await response.read())
            filename_index += 1
        backup_messages.append(
            build_channel_backup_message(
                author_id=message.author.id,
                content=message.content,
                attachment_filenames=tuple(attachment_names),
            )
        )
    write_channel_backup_manifest(
        base_folder=context["backup_folder"],
        backup_name=backup_name,
        manifest=ChannelBackupManifest(messages=tuple(backup_messages)),
    )
    await interaction.user.send(f"`{backup_name}` 백업이 완료되었습니다.")
    await interaction.followup.send(f"`{backup_name}` 백업이 완료되었습니다.")
    return _slash_result(status="completed", reason_code="channel_backup_completed")


async def run_restore_channel_slash_command(
    interaction: discord.Interaction,
    *,
    backup_name: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if interaction.guild.id != context["using_server"]:
        embed = discord.Embed(
            title="오류",
            description="이 기능은 아직 여러 서버들에서 지원되지 않습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return _slash_result(status="rejected", reason_code="unsupported_server")
    if interaction.user.id != context["developer"]:
        await interaction.response.send_message("**[오류!]** 권한이 부족합니다.", ephemeral=True)
        return _slash_result(status="rejected", reason_code="missing_developer_permission")

    await interaction.response.defer(ephemeral=True)
    backup_lookup = load_channel_backup_manifest(base_folder=context["backup_folder"], backup_name=backup_name)
    if backup_lookup.status == "missing":
        await interaction.followup.send(f"`{backup_name}` 백업을 찾을 수 없습니다.")
        return _slash_result(status="rejected", reason_code="backup_missing")

    webhook = await interaction.channel.create_webhook(name="채널 복원용")
    for message in reversed(backup_lookup.manifest.messages):
        user = await context["bot"].fetch_user(message.author_id)
        if message.content != "":
            await webhook.send(
                content=message.content,
                username=user.display_name,
                avatar_url=user.avatar.url if user.avatar else None,
            )
        for filename in message.attachment_filenames:
            file_path = os.path.join(backup_lookup.backup_path, filename)
            if os.path.exists(file_path):
                file = discord.File(file_path)
                await webhook.send(
                    content="",
                    username=user.display_name,
                    avatar_url=user.avatar.url if user.avatar else None,
                    file=file,
                )
    await interaction.followup.send(f"`{backup_name}` 복원이 완료되었습니다.")
    return _slash_result(status="completed", reason_code="channel_restore_completed")
