import discord

from discord.ext import commands
from discord import app_commands
from discord import Interaction
from discord import Member
from discord import Embed
from discord import AuditLogAction
from discord import AuditLogDiff
from discord import *

from datetime import datetime
from pytz import timezone

from commands.define import is_blocked, is_valid_time, kst, using_server, record_channel, message_log


def setup(bot: commands.Bot):
    @bot.tree.command(name = "일괄취소", description = "특정 사용자의 특정 시각 이후 관리 권한 사용 행위를 실행취소합니다. 보안봇이 서버에 있는 경우 보안봇 화이트리스트에 마늘이를 추가한 후 사용해 주세요.")
    @app_commands.describe(시각 = "취소 범위의 시작 지점을 입력해 주세요. (형식: YYYY-MM-DD HH:MM:SS)", 사용자 = "어느 사용자의 행위를 실행취소할지 입력해 주세요.")
    async def bulk_cancel(interaction: discord.Interaction, 사용자: discord.User, 시각: str, 사유: str = None) :
        if interaction.guild.owner_id != interaction.user.id:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 주인`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg)
            return

        시각 = 시각.replace("\\", "")
        
        # 시각 형식 확인
        if not is_valid_time(시각):
            embed = discord.Embed(
                title=f"오류", # name
                description=f"유효하지 않은 시각 형식입니다. 올바른 형식으로 입력해 주세요.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed = embed)
            return
        
        # 시각 문자열을 datetime 객체로 변환
        time_obj = datetime.strptime(시각, "%Y-%m-%d %H:%M:%S")

        # KST로 변환
        time_obj = kst.localize(time_obj)

        await interaction.response.defer()
        
        # 감사 로그 조회 (비동기 제너레이터 사용)
        logs = []
        async for log in interaction.guild.audit_logs(after=time_obj, user=사용자, oldest_first=False):
            logs.append(log)
        
        # 오래된 순으로 로그 정렬
        logs.sort(key=lambda x: x.created_at)
        
        # 감사 로그 처리
        canceling_action = []
        for log in logs:
            # 액션 타입에 따른 로그 메시지 생성
            if log.action == discord.AuditLogAction.ban:
                canceling_action.append(['ban', log.target])
            
            if log.action == discord.AuditLogAction.unban:
                canceling_action.append(['unban', log.target])

            if log.action == discord.AuditLogAction.member_update :
                try : 
                    # <AuditLogChanges before=<AuditLogDiff timed_out_until=datetime.datetime(2024, 12, 7, 6, 26, 23, 319000, tzinfo=datetime.timezone.utc)> after=<AuditLogDiff timed_out_until=None>>
                    if log.changes.after.timed_out_until != None and log.changes.before.timed_out_until == None:
                        user = log.user  # 타임아웃을 설정한 사람
                        target = log.target  # 타임아웃을 당한 사용자
                        reason = log.reason  # 타임아웃의 사유
                        canceling_action.append(['timeout', target])
                    elif log.changes.after.timed_out_until == None and log.changes.before.timed_out_until != None :
                        user = log.user  # 타임아웃을 해제한 사람
                        target = log.target  # 타임아웃을 해제당한 사용자
                        reason = log.reason  # 타임아웃의 사유
                        canceling_action.append(['untimeout', target, log.changes.before.timed_out_until])
                except Exception as e :
                    print("error", e)
                try :
                    if log.changes.after.nick != log.changes.before.nick :
                        target = log.target
                        canceling_action.append(['nick_change', target, log.changes.before.nick])
                except Exception as e:
                    print("error", e)
            if log.action == discord.AuditLogAction.member_role_update :
                before_roles = [role for role in log.changes.before.roles if hasattr(role, 'id')]
                after_roles = [role for role in log.changes.after.roles if hasattr(role, 'id')]

                # 역할이 제거된 경우
                if before_roles and not after_roles:
                    for role in before_roles:
                        canceling_action.append(['role_revoke', log.target, role])
                
                # 역할이 부여된 경우
                elif after_roles and not before_roles:
                    for role in after_roles:
                        canceling_action.append(['role_grant', log.target, role])
            if log.action == discord.AuditLogAction.role_update :
                try : 
                    canceling_action.append(['role_update', log.target.id, dict(log.before)])
                except Exception as e :
                    print("error", e)
                    try :
                        canceling_action.append(['role_change_name', log.target.id, log.before.name]) # 역할 이름 수정
                    except Exception :
                        print("error")
                    
                    try :
                        canceling_action.append(['role_change_perm', log.target.id, log.before.permissions]) # 역할 권한 수정
                    except Exception :
                        print("error")

                    try :
                        canceling_action.append(['role_change_color', log.target.id, log.before.color]) # 역할 권한 수정
                    except Exception :
                        print("error")
            if log.action == discord.AuditLogAction.channel_update :
                canceling_action.append(['channel_update', log.target, dict(log.before)])
            if log.action == discord.AuditLogAction.overwrite_create :
                canceling_action.append(['overwrite_create', log.target, log.extra])
            if log.action == discord.AuditLogAction.overwrite_update:
                before_allow = log.before['allow'] if 'allow' in log.before else 0
                before_deny = log.before['deny'] if 'deny' in log.before else 0
                po = discord.PermissionOverwrite.from_pair(
                    allow=discord.Permissions(before_allow),
                    deny=discord.Permissions(before_deny)
                )
                canceling_action.append(['overwrite_update', log.target, log.extra, po])

            if log.action == discord.AuditLogAction.overwrite_delete:
                before_allow = log.before['allow'] if 'allow' in log.before else 0
                before_deny = log.before['deny'] if 'deny' in log.before else 0
                po = discord.PermissionOverwrite.from_pair(
                    allow=discord.Permissions(before_allow),
                    deny=discord.Permissions(before_deny)
                )
                canceling_action.append(['overwrite_delete', log.target, log.extra, po])
            
            if log.action == discord.AuditLogAction.guild_update : 
                canceling_action.append(['guild_update', log.target, dict(log.before)])
            '''
            if log.action == discord.AuditLogAction.channel_delete:
                # log.before에서 삭제된 채널의 속성 정보를 추출
                before_data = log.before if hasattr(log, "before") else {}
                canceling_action.append(['channel_delete', log.target, log.extra, before_data])
            '''
        action_all = len(canceling_action)
        action_cnt = 0
        action_error_cnt = 0

        if 사유 == None :
            reason = f"사용자 {interaction.user.name} ({interaction.user.id}) 의 /일괄취소 명령어 사용"
            사유 = "*(사유 입력되지 않음)*"
        else :
            reason = f"사용자 {interaction.user.name} ({interaction.user.id}) 의 /일괄취소 명령어 사용 (사유: {사유})"
        
        for i in canceling_action :
            if i[0] == 'ban' :
                try : 
                    await interaction.guild.unban(i[1], reason=reason)
                    action_cnt += 1
                except Exception as e:
                    action_error_cnt += 1
            elif i[0] == 'unban' :
                await interaction.guild.ban(i[1], reason=reason)
                action_cnt += 1
            elif i[0] == 'nick_change' :
                try:
                    # 타임아웃 해제
                    await i[1].edit(nick=i[2], reason = reason)
                    action_cnt += 1
                except Exception as e:
                    action_error_cnt += 1
            elif i[0] == 'timeout' :
                try:
                    # 타임아웃 해제
                    await i[1].edit(timed_out_until=None, reason = reason)
                    action_cnt += 1
                except Exception as e:
                    action_error_cnt += 1
            elif i[0] == 'untimeout' :
                try:
                    # 타임아웃 해제
                    await i[1].edit(timed_out_until=i[2], reason = reason)
                    action_cnt += 1
                except Exception as e:
                    action_error_cnt += 1
            elif i[0] == 'role_revoke' :
                try:
                    await i[1].add_roles(i[2], reason = reason)
                    action_cnt += 1
                except Exception as e:
                    action_error_cnt += 1
            elif i[0] == 'role_grant' :
                try:
                    await i[1].remove_roles(i[2], reason = reason)
                    action_cnt += 1
                except Exception as e:
                    action_error_cnt += 1
            elif i[0] == 'channel_update' :
                try : 
                    await i[1].edit(reason = reason, **i[2])
                    action_cnt += 1
                except Exception as e :
                    print(e)
                    action_error_cnt += 1
            elif i[0] == 'role_update' :
                try :
                    i[1] = interaction.guild.get_role(i[1])
                    await i[1].edit(reason = reason, **i[2])
                    action_cnt += 1
                except Exception as e :
                    print(e)
                    action_error_cnt += 1
            elif i[0] == 'role_change_name' :
                try :
                    i[1] = interaction.guild.get_role(i[1])
                    await i[1].edit(name = i[2], reason = reason)
                    action_cnt += 1
                except Exception as e :
                    action_error_cnt += 1
            elif i[0] == 'role_change_perm' :
                try :
                    i[1] = interaction.guild.get_role(i[1])
                    await i[1].edit(permissions = i[2], reason = reason)
                    action_cnt += 1
                except Exception as e :
                    action_error_cnt += 1

            elif i[0] == 'role_change_color' :
                try :
                    i[1] = interaction.guild.get_role(i[1])
                    await i[1].edit(color = i[2], reason = reason)
                    action_cnt += 1
                except Exception as e :
                    action_error_cnt += 1
            elif i[0] == 'overwrite_create' :
                try :
                    await i[1].set_permissions(i[2], overwrite = None, reason=reason)
                    action_cnt += 1
                except Exception as e :
                    action_error_cnt += 1
            elif i[0] == 'overwrite_update' :
                try : 
                    await i[1].set_permissions(i[2], overwrite = i[3], reason=reason)
                    action_cnt += 1
                except Exception as e :
                    print(e)
                    action_error_cnt += 1
            elif i[0] == 'overwrite_delete' :
                try : 
                    await i[1].set_permissions(i[2], overwrite = i[3], reason=reason)
                    action_cnt += 1
                except Exception as e :
                    print(e)
                    action_error_cnt += 1
            elif i[0] == 'guild_update' :
                try : 
                    await interaction.guild.edit(reason = reason, **i[2])
                    action_cnt += 1
                except Exception as e :
                    print(e)
                    action_error_cnt += 1
            elif i[0] == 'channel_delete':
                try:
                    # 삭제된 채널 정보 복원
                    deleted_channel_obj = i[1]   # Object(id=...)
                    extra_info = i[2]            # 로그의 extra 정보 (채널 타입 등)
                    before_data = i[3]           # log.before의 AuditLogDiff
                    if "bitrate" in before_data:
                        channel_type = discord.ChannelType.voice
                        if "type" in before_data and before_data["type"] == 13:  # 13: Stage Voice
                            channel_type = discord.ChannelType.stage_voice

                    elif "default_auto_archive_duration" in before_data:
                        channel_type = discord.ChannelType.forum

                    elif "topic" in before_data:
                        channel_type = discord.ChannelType.text

                    else:
                        channel_type = discord.ChannelType.text

                    name = getattr(before_data, "name", f"복구된-채널-{deleted_channel_obj.id}")
                    position = getattr(before_data, "position", None)
                    category = getattr(before_data, "category", None)
                    topic = getattr(before_data, "topic", None)
                    nsfw = getattr(before_data, "nsfw", False)
                    slowmode = getattr(before_data, "slowmode_delay", 0)
                    bitrate = getattr(before_data, "bitrate", 64000)
                    user_limit = getattr(before_data, "user_limit", 0)
                    rtc_region = getattr(before_data, "rtc_region", None)

                    # overwrites 처리
                    overwrites = None
                    raw_ow = getattr(before_data, "overwrites", None)
                    if isinstance(raw_ow, list):
                        overwrites = {}
                        for ow in raw_ow:
                            ow_id = getattr(ow, "id", None)
                            ow_type = getattr(ow, "type", None)
                            ow_allow = getattr(ow, "allow", 0)
                            ow_deny = getattr(ow, "deny", 0)

                            target = None
                            if ow_type == "member":
                                target = interaction.guild.get_member(ow_id)
                            elif ow_type == "role":
                                target = interaction.guild.get_role(ow_id)

                            if target:
                                po = discord.PermissionOverwrite.from_pair(
                                    allow=discord.Permissions(ow_allow),
                                    deny=discord.Permissions(ow_deny)
                                )
                                overwrites[target] = po

                    kwargs = {
                        "name": name,
                        "reason": reason,
                    }
                    if position is not None:
                        kwargs["position"] = position
                    if category is not None:
                        kwargs["category"] = category
                    if overwrites is not None:
                        kwargs["overwrites"] = overwrites

                    # 디버깅 출력 (필요시 주석 처리)
                    print(f"복구 채널 타입: {channel_type}")

                    if channel_type == discord.ChannelType.text:
                        kwargs.update({
                            "topic": topic,
                            "nsfw": nsfw,
                            "slowmode_delay": slowmode
                        })
                        await interaction.guild.create_text_channel(**kwargs)

                    elif channel_type == discord.ChannelType.voice:
                        kwargs.update({
                            "bitrate": bitrate,
                            "user_limit": user_limit,
                            "rtc_region": rtc_region
                        })
                        await interaction.guild.create_voice_channel(**kwargs)

                    elif channel_type == discord.ChannelType.stage_voice:
                        kwargs.update({
                            "bitrate": bitrate,
                            "user_limit": user_limit,
                            "rtc_region": rtc_region
                        })
                        await interaction.guild.create_stage_channel(**kwargs)

                    elif channel_type == discord.ChannelType.forum:
                        kwargs.update({
                            "nsfw": nsfw
                        })
                        await interaction.guild.create_forum_channel(**kwargs)

                    else:
                        # 기본적으로 텍스트 채널로 생성
                        await interaction.guild.create_text_channel(**kwargs)

                    action_cnt += 1

                except Exception as e:
                    print("채널 삭제 복구 실패:", e)
                    action_error_cnt += 1

            

        embed = discord.Embed(
            title=f"성공", # name
            description=f"{사용자.mention} 사용자의 작업 {action_all}개 중 {action_cnt}개를 실행취소했습니다.\n\n잘못 실행취소한 경우 마늘이의 작업을 다시 일괄적으로 실행취소할 수 있습니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)

        
        if interaction.guild.id != using_server :
            return

        embed = discord.Embed(
            title="일괄 취소",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="대상 사용자", value=f"{사용자.mention}", inline=False)
        embed.add_field(name="대상 기간", value=f"{시각} ~ 현재 시각", inline=False)
        embed.add_field(name="대상 작업", value=f"작업 {action_all}개 중 {action_cnt}개", inline=False)
        embed.add_field(name="관리자", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="사유", value=사유, inline=False)

        channel = bot.get_channel(record_channel)
        if channel:
            await channel.send(embed=embed)

        log_channel = bot.get_channel(message_log)
        await log_channel.send(embed=embed)


