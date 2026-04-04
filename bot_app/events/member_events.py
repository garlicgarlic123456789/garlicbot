from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random
import time
from typing import Any, Mapping

import discord


def should_assign_autorole(bot_user: str, *, is_bot: bool) -> bool:
    if bot_user == "all":
        return True
    if bot_user == "user":
        return not is_bot
    if bot_user == "bot":
        return is_bot
    return False


def prune_recent_members(members: list[Any], *, now: datetime, interval_seconds: int) -> list[Any]:
    return [member for member in members if (now - member.joined_at).total_seconds() <= interval_seconds]


def resolve_used_invite(new_invites: list[Any], old_invites: list[Any]):
    for invite in new_invites:
        for old_invite in old_invites:
            if invite.code == old_invite.code and invite.uses > old_invite.uses:
                return invite
    return None


def build_member_departure_embed(member_mention: str) -> discord.Embed:
    return discord.Embed(
        title="회원 탈퇴 알림",
        description=f"{member_mention}님이 철도역에서 떠나셨습니다.",
        color=discord.Color.red(),
    )


def build_block_action_embed(
    *,
    title: str,
    color: discord.Colour | int,
    user_mention: str,
    moderator_mention: str,
    reason: str,
    duration_text: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=user_mention, inline=False)
    embed.add_field(name="관리자", value=moderator_mention, inline=False)
    if duration_text is not None:
        embed.add_field(name="기간", value=duration_text, inline=False)
    embed.add_field(name="사유", value=reason, inline=False)
    return embed


def build_welcome_embed(
    *,
    member_mention: str,
    display_name: str,
    time_text: str,
    train_number: int,
    platform_number: int,
    detailed: bool,
) -> discord.Embed:
    description = (
        f"{member_mention}님이 철도역에 도착하셨습니다.\n\n"
        f"{time_text}에 철도역으로 가는 {display_name} #{train_number} 열차를 이용할 고객께서는 타는 곳 {platform_number}번으로 가시기 바랍니다."
    )

    if detailed:
        description += (
            " \n\n- 저희 서버는 채팅률이 쩌는 친목 서버입니다!\n"
            "- 활동 전 <#1483037563383185461>을 확인해 주세요.\n"
            "- <id:customize>에서 원하시는 역할을 받으실 수 있습니다. "
            "(저희 서버는 `@everyone`이나 `@here` 멘션을 거의 하지 않습니다.)\n"
            "- 서버에 대하여 문의하거나 제안하고 싶으신 사항이 있으신 경우 <#1483037563991232548>을 이용해 주시기 바라며, "
            "규정을 위반하는 사용자를 신고하고 싶으신 경우에도 <#1483037563991232548>을 이용해 주시기 바랍니다."
        )

    return discord.Embed(
        title="환영합니다!",
        description=description,
        color=int("a5f0ff", 16),
    )


def build_role_change_embed(
    *,
    title: str,
    color: discord.Colour | int,
    user_mention: str,
    role_mention: str,
) -> discord.Embed:
    embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
    embed.add_field(name="사용자", value=user_mention, inline=False)
    embed.add_field(name="역할", value=role_mention, inline=False)
    return embed


async def _send_message_log(bot, guild_id: int, embed: discord.Embed, context: Mapping[str, Any]) -> None:
    if guild_id != context["using_server"]:
        return

    log_channel = bot.get_channel(context["message_log"])
    if log_channel:
        await log_channel.send(embed=embed)


def register_member_events(bot, context: Mapping[str, Any]) -> None:
    state = context["state"]

    @bot.event
    async def on_member_remove(member):
        guild = member.guild
        if guild.id == context["using_server"]:
            channel = member.guild.get_channel(context["byebye_channel"])
            if channel:
                await channel.send(embed=build_member_departure_embed(member.mention))

        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                사용자 = member
                관리자 = entry.user
                사유 = entry.reason
                if 관리자.id == 1316579106749681664:
                    return
                if 사유 is None or 사유 == "None":
                    사유 = "*(사유 입력되지 않음)*"

                embed = build_block_action_embed(
                    title="추방",
                    color=discord.Color.red(),
                    user_mention=사용자.mention,
                    moderator_mention=관리자.mention,
                    reason=사유,
                )

                channel = bot.get_channel(context["get_block_log_channel"](guild.id))
                if channel:
                    await channel.send(embed=embed)

                await _send_message_log(bot, guild.id, embed, context)

                context["add_blockhistory"](사용자.id, 관리자.id, 사유, "kick", 0, guild.id)
                await context["process_anti_nuke_ban"](guild.id, 관리자.id, guild)

    @bot.event
    async def on_member_ban(guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            사용자 = user
            관리자 = entry.user
            사유 = entry.reason
            if 관리자.id == 1316579106749681664:
                return
            if 사유 is None:
                사유 = "*(사유 입력되지 않음)*"

            context["add_blockhistory"](사용자.id, 관리자.id, 사유, "ban", 0, guild.id)
            embed = build_block_action_embed(
                title="차단",
                color=discord.Color.red(),
                user_mention=사용자.mention,
                moderator_mention=관리자.mention,
                reason=사유,
            )

            channel = bot.get_channel(context["get_block_log_channel"](guild.id))
            if channel:
                await channel.send(embed=embed)

            await _send_message_log(bot, guild.id, embed, context)
            await context["process_anti_nuke_ban"](guild.id, 관리자.id, guild)

    @bot.event
    async def on_member_unban(guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            사용자 = user
            관리자 = entry.user
            사유 = entry.reason
            if 관리자.id == 1316579106749681664:
                return
            if 사유 is None:
                사유 = "*(사유 입력되지 않음)*"

            context["add_blockhistory"](사용자.id, 관리자.id, 사유, "unban", 0, guild.id)
            embed = build_block_action_embed(
                title="차단 해제",
                color=int("a5f0ff", 16),
                user_mention=사용자.mention,
                moderator_mention=관리자.mention,
                reason=사유,
            )

            channel = bot.get_channel(context["get_block_log_channel"](guild.id))
            if channel:
                await channel.send(embed=embed)

            await _send_message_log(bot, guild.id, embed, context)

    @bot.event
    async def on_member_join(member):
        guild = member.guild
        guild_id = guild.id

        servers_anti_raid_settings = await context["get_anti_raid_settings"](guild.id)

        if servers_anti_raid_settings["on_off"]:
            join_check_interval = servers_anti_raid_settings["duration"]
            join_count = servers_anti_raid_settings["join_time"]
            now = datetime.now(timezone.utc)

            recent_joins = state["recent_joins"]
            if guild_id not in recent_joins:
                recent_joins[guild_id] = []

            recent_joins[guild_id].append(member)
            recent_joins[guild_id] = prune_recent_members(
                recent_joins[guild_id],
                now=now,
                interval_seconds=join_check_interval,
            )

            if len(recent_joins[guild_id]) > join_count:
                raid_detect_time = int(time.time())
                action = servers_anti_raid_settings["action"]
                pause_invite_success = False

                if action in {"pause_invite", "timeout", "ban", "isolate"}:
                    try:
                        await guild.edit(
                            invites_disabled_until=discord.utils.utcnow() + timedelta(seconds=86397),
                            reason="레이드 감지",
                        )
                        pause_invite_success = True
                    except Exception:
                        pause_invite_success = False

                punished_user = []

                if action == "ban":
                    punish_failed = 0
                    for joined_member in recent_joins[guild.id]:
                        try:
                            await guild.ban(joined_member, reason="레이드 감지", delete_message_seconds=0)
                            punished_user.append(joined_member)
                        except Exception:
                            punish_failed += 1
                elif action == "timeout":
                    punish_failed = 0
                    for joined_member in recent_joins[guild.id]:
                        try:
                            await joined_member.edit(
                                timed_out_until=discord.utils.utcnow() + timedelta(seconds=2419197),
                                reason="레이드 감지",
                            )
                            punished_user.append(joined_member)
                        except Exception:
                            punish_failed += 1
                elif action == "isolate":
                    punish_failed = 0
                    try:
                        isolate_role = guild.get_role(context["get_quarantine_role"](guild.id))
                    except Exception:
                        isolate_role = None
                    for joined_member in recent_joins[guild.id]:
                        roles_to_remove = [role for role in joined_member.roles if role != guild.default_role]
                        try:
                            await joined_member.remove_roles(*roles_to_remove)
                            if isolate_role is None:
                                raise ValueError("isolate_role이 None입니다.")
                            await joined_member.add_roles(isolate_role)
                        except Exception:
                            punish_failed += 1
                else:
                    punish_failed = 0

                if action == "ban":
                    for joined_member in punished_user:
                        context["add_blockhistory"](
                            joined_member.id, 1316579106749681664, "레이드 감지", "ban", 0, guild_id
                        )
                elif action == "timeout":
                    for joined_member in punished_user:
                        context["add_blockhistory"](
                            joined_member.id,
                            1316579106749681664,
                            "레이드 감지",
                            "timeout",
                            2419200,
                            guild_id,
                        )

                alert_channel_id = servers_anti_raid_settings["alert_channel_id"]
                raid_action_done_time = int(time.time())
                raid_account_text = ", ".join([f"<@{joined_member.id}>" for joined_member in recent_joins[guild_id]])
                recent_joins[guild_id].clear()

                if action == "ban":
                    embed = discord.Embed(
                        title="레이드 감지",
                        description=(
                            f"레이드가 감지되어 조치했습니다.\n\n- 레이드 관련 계정: {raid_account_text}\n"
                            f"- 레이드 감지 시각: <t:{raid_detect_time}> (<t:{raid_detect_time}:R>)\n"
                            f"- 레이드 조치 완료 시각: <t:{raid_action_done_time}> (<t:{raid_action_done_time}:R>)"
                        ),
                        color=discord.Color.red(),
                    )
                    if punish_failed > 0:
                        embed.description += f"\n- 레이드 조치 결과: 계정 {punish_failed}개에 대해 차단 실패"
                    else:
                        embed.description += "\n- 레이드 조치 결과: 모든 계정 차단 성공"
                    embed.description += " 및 초대 일시정지 성공" if pause_invite_success else " 및 초대 일시정지 실패"
                elif action == "timeout":
                    embed = discord.Embed(
                        title="레이드 감지",
                        description=(
                            f"레이드가 감지되어 조치했습니다.\n\n- 레이드 관련 계정: {raid_account_text}\n"
                            f"- 레이드 감지 시각: <t:{raid_detect_time}> (<t:{raid_detect_time}:R>)\n"
                            f"- 레이드 조치 완료 시각: <t:{raid_action_done_time}> (<t:{raid_action_done_time}:R>)"
                        ),
                        color=discord.Color.red(),
                    )
                    if punish_failed > 0:
                        embed.description += f"\n- 레이드 조치 결과: 계정 {punish_failed}개에 대해 타임아웃 실패"
                    else:
                        embed.description += "\n- 레이드 조치 결과: 모든 계정 타임아웃 성공"
                    embed.description += " 및 초대 일시정지 성공" if pause_invite_success else " 및 초대 일시정지 실패"
                elif action == "isolate":
                    embed = discord.Embed(
                        title="레이드 감지",
                        description=(
                            f"레이드가 감지되어 조치했습니다.\n\n- 레이드 관련 계정: {raid_account_text}\n"
                            f"- 레이드 감지 시각: <t:{raid_detect_time}> (<t:{raid_detect_time}:R>)\n"
                            f"- 레이드 조치 완료 시각: <t:{raid_action_done_time}> (<t:{raid_action_done_time}:R>)"
                        ),
                        color=discord.Color.red(),
                    )
                    if punish_failed > 0:
                        embed.description += f"\n- 레이드 조치 결과: 계정 {punish_failed}개에 대해 격리 실패"
                    else:
                        embed.description += "\n- 레이드 조치 결과: 모든 계정 격리 성공"
                    embed.description += " 및 초대 일시정지 성공" if pause_invite_success else " 및 초대 일시정지 실패"
                elif action == "pause_invite":
                    embed = discord.Embed(
                        title="레이드 감지",
                        description=(
                            f"레이드가 감지되어 조치했습니다.\n\n- 레이드 관련 계정: {raid_account_text}\n"
                            f"- 레이드 감지 시각: <t:{raid_detect_time}> (<t:{raid_detect_time}:R>)\n"
                            f"- 레이드 조치 완료 시각: <t:{raid_action_done_time}> (<t:{raid_action_done_time}:R>)"
                        ),
                        color=discord.Color.red(),
                    )
                    embed.description += (
                        "\n- 레이드 조치 결과: 초대 일시정지 성공"
                        if pause_invite_success
                        else "\n- 레이드 조치 결과: 초대 일시정지 실패"
                    )
                else:
                    embed = discord.Embed(
                        title="레이드 감지",
                        description=(
                            f"레이드가 감지되었습니다.\n\n- 레이드 관련 계정: {raid_account_text}\n"
                            f"- 레이드 감지 시각: <t:{raid_detect_time}> (<t:{raid_detect_time}:R>)"
                        ),
                        color=discord.Color.red(),
                    )

                try:
                    alert_channel = guild.get_channel(alert_channel_id)
                except Exception:
                    alert_channel = None

                if alert_channel is not None:
                    try:
                        await alert_channel.send(f"<@{guild.owner.id}>", embed=embed)
                    except Exception:
                        try:
                            await guild.owner.send(embed=embed)
                        except Exception:
                            context["add_mention_delay_user"](
                                member.id, 1316579106749681664, embed.description, 0, guild_id, "reply"
                            )
                else:
                    try:
                        await guild.owner.send(embed=embed)
                    except Exception:
                        context["add_mention_delay_user"](
                            member.id, 1316579106749681664, embed.description, 0, guild_id, "reply"
                        )

        try:
            new_invites = await member.guild.invites()
            old_invites = state["invite_cache"].get(member.guild.id, [])
            used_invite = resolve_used_invite(new_invites, old_invites)
            state["invite_cache"][member.guild.id] = new_invites

            if used_invite:
                context["save_invite_log"](member.id, used_invite.code, member.guild.id)
            else:
                context["save_invite_log"](member.id, None, member.guild.id)

        except Exception as error:
            print(f"Error on member join: {error}")
            context["save_invite_log"](member.id, None, member.guild.id)

        autoroles = await context["get_autorole"](member.guild.id)
        for autorole in autoroles:
            if should_assign_autorole(autorole["bot_user"], is_bot=member.bot):
                await member.add_roles(
                    member.guild.get_role(autorole["role_id"]),
                    reason="자동 역할 설정에 의한 역할 부여",
                )

    @bot.event
    async def on_member_update(before, after):
        if before.guild.id == context["using_server"]:
            added_roles = [role for role in after.roles if role not in before.roles]
            for role in added_roles:
                if role.id == context["verify_role"]:
                    time_text = datetime.now().strftime("%H시 %M분")
                    train_number = random.randint(1, 9999)
                    platform_number = random.randint(1, 14)

                    channel = after.guild.get_channel(context["greeting_channel"])
                    if channel:
                        await channel.send(
                            embed=build_welcome_embed(
                                member_mention=after.mention,
                                display_name=after.display_name,
                                time_text=time_text,
                                train_number=train_number,
                                platform_number=platform_number,
                                detailed=False,
                            )
                        )

                    mention_channel = after.guild.get_channel(1483037564159131762)
                    if mention_channel:
                        state["last_member_join_mention"] = datetime.now()
                        await mention_channel.send(
                            f"<@{after.id}>",
                            embed=build_welcome_embed(
                                member_mention=after.mention,
                                display_name=after.display_name,
                                time_text=time_text,
                                train_number=train_number,
                                platform_number=platform_number,
                                detailed=True,
                            ),
                        )

        if before.timed_out_until != after.timed_out_until:
            channel = bot.get_channel(context["get_block_log_channel"](after.guild.id))

            if before.timed_out_until and not after.timed_out_until:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    moderator = entry.user
                    if entry.user.id == 1316579106749681664:
                        return
                    reason = entry.reason or "*(사유 입력되지 않음)*"

                    embed = build_block_action_embed(
                        title="타임아웃 해제",
                        color=int("a5f0ff", 16),
                        user_mention=after.mention,
                        moderator_mention=moderator.mention,
                        reason=reason,
                    )

                    await channel.send(embed=embed)
                    context["add_blockhistory"](after.id, moderator.id, reason, "untimeout", 0, after.guild.id)
                    await _send_message_log(bot, after.guild.id, embed, context)

            elif not before.timed_out_until and after.timed_out_until:
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id:
                        moderator = entry.user
                        if entry.user.id == 1316579106749681664:
                            return
                        reason = entry.reason or "*(사유 입력되지 않음)*"
                        if (
                            after.guild.id == context["using_server"]
                            and entry.user.id == 218010938807287808
                            and reason == "by Russian"
                        ):
                            await after.edit(timed_out_until=None, reason="러시안 룰렛에 의한 타임아웃 무효화")
                            return
                        timeout_duration = after.timed_out_until - discord.utils.utcnow()

                        embed = build_block_action_embed(
                            title="타임아웃",
                            color=discord.Color.red(),
                            user_mention=after.mention,
                            moderator_mention=moderator.mention,
                            duration_text=context["format_duration"](timeout_duration),
                            reason=reason,
                        )

                        context["add_blockhistory"](
                            after.id,
                            moderator.id,
                            reason,
                            "timeout",
                            int(timeout_duration.total_seconds()),
                            after.guild.id,
                        )

                        await channel.send(embed=embed)
                        await _send_message_log(bot, after.guild.id, embed, context)
                    else:
                        if entry.user.id == 1316579106749681664:
                            return
                        reason = "*(알 수 없음)*"
                        timeout_duration = after.timed_out_until - discord.utils.utcnow()

                        embed = build_block_action_embed(
                            title="타임아웃",
                            color=discord.Color.red(),
                            user_mention=after.mention,
                            moderator_mention="*(알 수 없음)*",
                            duration_text=context["format_duration"](timeout_duration),
                            reason=reason,
                        )

                        context["add_blockhistory"](
                            after.id,
                            None,
                            reason,
                            "timeout",
                            int(timeout_duration.total_seconds()),
                            after.guild.id,
                        )

                        await channel.send(embed=embed)
                        await _send_message_log(bot, after.guild.id, embed, context)

        if before.roles != after.roles:
            channel_id = context["get_log_channel"](after.guild.id)["role"]
            if channel_id is not None:
                channel = bot.get_channel(channel_id)
                if channel:
                    added_roles = [role for role in after.roles if role not in before.roles]
                    removed_roles = [role for role in before.roles if role not in after.roles]

                    for role in added_roles:
                        await channel.send(
                            embed=build_role_change_embed(
                                title="역할 부여",
                                color=int("a5f0ff", 16),
                                user_mention=after.mention,
                                role_mention=role.mention,
                            )
                        )

                    for role in removed_roles:
                        await channel.send(
                            embed=build_role_change_embed(
                                title="역할 회수",
                                color=discord.Color.red(),
                                user_mention=after.mention,
                                role_mention=role.mention,
                            )
                        )
