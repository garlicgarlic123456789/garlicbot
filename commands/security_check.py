import discord
from commands.define import *

import asyncio
import re
from discord import *
from commands.database import *

def setup(bot) : 
    @bot.tree.command(name="보안점검", description="서버의 권한 설정을 검토합니다.")
    @app_commands.default_permissions(administrator=True)
    async def security_check(interaction: discord.Interaction, 인증역할: discord.Role = None):
        await interaction.response.defer()

        status, until, reason = is_blocked(interaction.user)
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        dangerous = False
        warning = False

        # 검사할 역할 설정
        check_role = 인증역할 if 인증역할 else interaction.guild.default_role
        if 인증역할 is not None : 
            check_role2 = interaction.guild.default_role
        else : 
            check_role2 = None

        # 위험 권한 확인
        dangerous_perms_found = []
        for perm, perm_name in dangerous_permissions.items():
            if getattr(check_role.permissions, perm):
                dangerous_perms_found.append(perm_name)
            if check_role2 is not None : 
                if getattr(check_role2.permissions, perm):
                    dangerous_perms_found.append(perm_name)
        
        description = ""

        # 임베드 생성
        embed = discord.Embed(
            title="서버 보안 점검 결과",
            description = "서버 보안 점검 결과는 다음과 같습니다. [자세히 알아보기](https://asdfasdfqwer.notion.site/1fc4a653ce0180038f81f2fb001c7943?source=copy_link)",
        )

        # 위험 권한 상태 메시지
        if dangerous_perms_found:
            status_msg = f"일반 사용자에게 위험한 권한 {len(dangerous_perms_found)}개가 부여되어 있습니다: " + \
                        ", ".join(f"{perm}" for perm in dangerous_perms_found)
            dangerous = True
        else:
            status_msg = "일반 사용자에게 위험한 권한이 부여되어 있지 않습니다."
        
        all_bot_admin = await check_all_bot_admin_perm(interaction)

        if all_bot_admin : 
            all_bot_admin_msg = "모든 봇에게 관리자 권한을 일괄적으로 부여하는 것은 권장되지 않습니다. 봇별로 개별적으로 권한을 다르게 부여하시기 바랍니다."
            warning = True
        else : 
            all_bot_admin_msg = "모든 봇에게 관리자 권한을 일괄적으로 부여하고 있지 않습니다."
        
        
        embed.add_field(name = "역할 권한 보안", value = f"- 일반 사용자 위험한 권한 부여 여부: {status_msg}\n- 모든 봇 관리자 권한 부여 여부: {all_bot_admin_msg}", inline = False)

        check_role = 인증역할 if 인증역할 else interaction.guild.default_role

        dangerous_perms_found = []

        for channel in interaction.guild.channels:
            overwrites = channel.overwrites_for(check_role)
            for perm, perm_name in dangerous_permissions.items():
                if getattr(overwrites, perm, None):  # 채널에서 명시적으로 허용된 권한만 체크
                    dangerous_perms_found.append(f"{channel.mention}: {perm_name}")
        if check_role2 is not None : 
            for channel in interaction.guild.channels:
                overwrites = channel.overwrites_for(check_role2)
                for perm, perm_name in dangerous_permissions.items():
                    if getattr(overwrites, perm, None):  # 채널에서 명시적으로 허용된 권한만 체크
                        dangerous_perms_found.append(f"{channel.mention}: {perm_name}")

        if dangerous_perms_found:
            status_msg = f"일반 사용자에게 위험한 채널 권한 {len(dangerous_perms_found)}개가 부여되어 있습니다: " + \
                        ", ".join(f"{perm}" for perm in dangerous_perms_found)
            dangerous = True
        else:
            status_msg = "일반 사용자에게 위험한 채널 권한이 부여되어 있지 않습니다."
        
        embed.add_field(name = "채널 권한 보안", value = f"- 일반 사용자 위험한 권한 부여 여부: {status_msg}", inline = False)

        automod_rules = await interaction.guild.fetch_automod_rules()

        bot_automod = False
        invite_link_keyword_automod = False
        invite_link_keyword_automod2 = False
        invite_link_regex_automod = False

        automod = get_automod(interaction.guild.id)['invite_link'][0]

        if automod == True : 
            bot_automod = True

        for automod_rule in automod_rules : 
            if invite_link_regex_automod == True : 
                break
            if automod_rule.enabled == True : 
                if automod_rule.trigger.regex_patterns is not None : 
                    for i in automod_rule.trigger.regex_patterns : 
                        regex = re.compile(i)
                        if regex.search("discord.gg/discord") is not None : 
                            if regex.search("discord.com/invite/discord") is not None : 
                                if regex.search("discord.com:443/invite/discord") is not None : 
                                    if regex.search("discord.gg:443/discord") is not None : 
                                        invite_link_regex_automod = True
                if automod_rule.trigger.keyword_filter is not None : 
                    for i in automod_rule.trigger.keyword_filter : 
                        if "discord.gg" in i : 
                            invite_link_keyword_automod = True
                        if "discord.com/invite" in i : 
                            invite_link_keyword_automod2 = True
        
        if bot_automod == True : 
            embed.add_field(name = "특정 메시지 차단 보안", value = "- 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 마늘이 자동 검열 기능이 활성화되어 있습니다.", inline = False)
        elif invite_link_regex_automod == True : 
            embed.add_field(name = "특정 메시지 차단 보안", value = "- 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 Automod가 활성화되어 있습니다.", inline = False)
        elif invite_link_keyword_automod == True and invite_link_keyword_automod2 == True : 
            embed.add_field(name = "특정 메시지 차단 보안", value = "- 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 Automod가 활성화되어 있으나, 정규표현식으로 되어 있지 않거나 정규표현식이 올바르지 않아 일부 우회가 가능합니다. 정규표현식을 통해 우회를 방지하는 방법을 [자세히 알아보세요](https://asdfasdfqwer.notion.site/1fc4a653ce0180038f81f2fb001c7943?source=copy_link).", inline = False)
            warning = True
        else : 
            embed.add_field(name = "특정 메시지 차단 보안", value = "- 초대 링크 자동 차단: 디스코드 서버 초대 링크를 무단으로 게시하는 것을 차단하는 Automod가 활성화되어 있지 않습니다. 정규표현식을 통해 이러한 링크를 차단하는 방법을 [자세히 알아보세요](https://asdfasdfqwer.notion.site/1fc4a653ce0180038f81f2fb001c7943?source=copy_link).", inline = False)
            dangerous = True

        if dangerous : 
            embed.color = discord.Color.red()
        elif warning : 
            embed.color = discord.Color.yellow()
        else : 
            embed.color = int("a5f0ff", 16)

        await interaction.followup.send(embed=embed)

async def check_all_bot_admin_perm(interaction):
    # 모든 역할을 순회
    for role in interaction.guild.roles:
        # 관리자 권한이 없으면 패스
        if not role.permissions.administrator:
            continue

        # 이 역할이 부여된 멤버들 가져오기
        members_with_role = [member for member in interaction.guild.members if role in member.roles]

        # 조건 1: 역할이 부여된 봇 계정이 5명 이상인지 확인
        if len(members_with_role) >= 5 and all(member.bot for member in members_with_role):
            return True  # 조건을 만족하는 역할이 존재

    return False  # 끝까지 돌았는데 조건을 만족하는 역할이 없음