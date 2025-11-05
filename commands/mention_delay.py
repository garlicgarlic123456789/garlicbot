import discord
from discord.ext import commands
import re

from commands.database import *
from commands.define import *

class mention_delay(app_commands.Group) : 
    def __init__(self) : 
        super().__init__(name="멘션지연", description="멘션지연 관련 명령어")
    
    @app_commands.command(name="차단", description="특정 사용자가 자신을 향해 멘션지연을 하는 것을 차단합니다.")
    @app_commands.describe(사용자 = "차단할 사용자", 차단여부 = "차단 여부")
    async def mention_delay_block(self, interaction: discord.Interaction, 사용자: discord.User, 차단여부: bool):
        await interaction.response.defer(ephemeral=True)
        update_mention_delay_block(interaction.user.id, 사용자.id, 차단여부)
        embed = discord.Embed(
            title=f"알림",
            description=f"{사용자.mention}님이 자신을 향해 멘션지연을 하는 것을 차단할지 여부를 {차단여부}로 설정했습니다.\n**[주의!]** 멘션지연 차단 이전에 이미 예약된 멘션은 차단되지 않습니다. 멘션지연 차단 기능은 차단 **이후**에 추가적으로 예약되는 멘션을 차단합니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)
        return
    
    @app_commands.command(name="역할", description="특정 역할에 속한 유저가 메시지를 보냈을 때 멘션하도록 예약합니다.")
    @app_commands.describe(역할 = "대상 역할", 내용 = "내용", 전달범위 = "명령어를 사용한 서버에서만 또는 마늘봇이 도입된 모든 서버 중 하나에서 대상 사용자가 메시지를 보낼 시 전달", 전달방법 = "역할에 속한 사용자 중 1명에게만 전달 또는 역할에 속한 모든 사용자에게 전달")
    @app_commands.choices(전달범위 = [
        app_commands.Choice(name = "이 서버 (답장으로 전달)", value = "server_reply"),
        app_commands.Choice(name = "이 서버 (DM으로 전달)", value = "server_dm"),
        app_commands.Choice(name = "마늘이 봇이 도입된 모든 서버 (DM으로 전달)", value = "all"),
    ])
    @app_commands.choices(전달방법 = [
        app_commands.Choice(name = "역할에 속한 모든 사용자에게 전달", value = "all"),
        app_commands.Choice(name = "역할에 속한 사용자 중 가장 먼저 오는 1명에게만 전달", value = "one"),
    ])
    async def mention_delay_role(self, interaction: discord.Interaction, 역할: discord.Role, 내용: str, 전달범위: str = "server_reply", 전달방법: str = "all"):
        if 전달범위 == "server_reply" : await interaction.response.defer(ephemeral=False)
        else : await interaction.response.defer(ephemeral=True)
        
        role_users = 역할.members

        if len(role_users) == 0 : 
            embed = discord.Embed(
                title=f"오류",
                description=f"해당 역할에 속한 사용자가 없습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        elif len(role_users) > 70 : 
            embed = discord.Embed(
                title=f"오류",
                description=f"해당 역할에 속한 사용자가 70명 이상이므로, 멘션지연을 예약할 수 없습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        elif len(role_users) >= 10 : 
            if not interaction.user.guild_permissions.mention_everyone : 
                embed = discord.Embed(
                    title=f"오류",
                    description=f"해당 역할에 속한 사용자가 10명 이상이므로, 멘션지연을 예약하기 위해서는 특수 권한이 필요합니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return

        role_users_count = len(role_users)
        role_users_count_before = role_users_count
        for i in range(len(role_users) - 1, -1, -1):
            if role_users[i].bot : 
                role_users.remove(role_users[i])
                role_users_count -= 1
            elif get_mention_delay_block(role_users[i].id, interaction.user.id) : 
                role_users.remove(role_users[i])
                role_users_count -= 1
        
        if role_users_count == 0 : 
            embed = discord.Embed(
                title=f"오류",
                description=f"해당 역할에 속한 사용자 {role_users_count_before}명 모두에게 멘션을 예약할 수 없습니다. \n\n- 해당 사용자에 의해 차단된 작업일 수 있습니다.\n- 해당 사용자 계정이 봇 계정일 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 전달범위 == "server_reply" : 
            send_type = "reply"
        elif 전달범위 == "server_dm" : 
            send_type = "dm"
        elif 전달범위 == "all" : 
            send_type = "dm"
        
        if 전달범위 == "server_reply" or 전달범위 == "server_dm" : 
            mention_server = interaction.guild.id
        elif 전달범위 == "all" : 
            mention_server = None
        else : 
            embed = discord.Embed(
                title=f"오류",
                description=f"전달범위가 잘못되었습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        status, until, reason = is_blocked(interaction.user)
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        if len(내용) > 130 and interaction.user.id != developer:
            embed = discord.Embed(
                title=f"오류",
                description=f"130자를 초과하는 멘션을 예약하기 위해서는 특수 권한이 필요합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        role_users = [user for user in role_users if user.id != interaction.user.id]
        
        if 전달방법 == "all" : 
            mention_ids = []
            for i in range(len(role_users)) : 
                mention_id = add_mention_delay_user(role_users[i].id, interaction.user.id, 내용, 0, mention_server, send_type)
                mention_ids.append(mention_id)

            temp = len(mention_ids)
            for i in range(temp) : 
                mention_ids[i] = str(mention_ids[i])
            
            process_mention_cancel_together(mention_ids)
        elif 전달방법 == "one" : 
            mention_ids = []
            for i in range(len(role_users)) : 
                mention_id = add_mention_delay_user(role_users[i].id, interaction.user.id, 내용, 0, mention_server, send_type)
                mention_ids.append(mention_id)
            
            temp = len(mention_ids)
            for i in range(temp) : 
                mention_ids[i] = str(mention_ids[i])

            process_mention_relation(mention_ids)
            process_mention_cancel_together(mention_ids)
        
        if role_users_count != role_users_count_before : 
            embed = discord.Embed(
                title=f"완료",
                description=f"멘션 #{', '.join(mention_ids)}\n\n{역할.mention} 역할에 속한 사용자가 메시지를 보낼 시 해당 내용이 전달되도록 예약했습니다.\n\n**[주의!]** 해당 역할에 속한 사용자 중 {role_users_count_before - role_users_count}명에게 멘션을 예약할 수 없습니다. \n\n- 해당 사용자에 의해 차단된 작업일 수 있습니다.\n- 해당 사용자 계정이 봇 계정일 수 있습니다.",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embed = embed)
            return
        embed = discord.Embed(
            title=f"완료",
            description=f"멘션 #{', '.join(mention_ids)}\n\n{역할.mention} 역할에 속한 사용자가 메시지를 보낼 시 해당 내용이 전달되도록 예약했습니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)

    @app_commands.command(name="유저", description="특정 사용자가 메시지를 보냈을 때 멘션하도록 예약합니다.")
    @app_commands.describe(사용자 = "대상 사용자", 내용 = "내용", 전달범위 = "명령어를 사용한 서버에서만 또는 마늘봇이 도입된 모든 서버 중 하나에서 대상 사용자가 메시지를 보낼 시 전달")
    @app_commands.choices(전달범위 = [
        app_commands.Choice(name = "이 서버 (답장으로 전달)", value = "server_reply"),
        app_commands.Choice(name = "이 서버 (DM으로 전달)", value = "server_dm"),
        app_commands.Choice(name = "마늘이 봇이 도입된 모든 서버 (DM으로 전달)", value = "all"),
    ])
    async def mention_delay(self, interaction: discord.Interaction, 사용자: discord.Member, 내용: str, 전달범위: str = "server_reply"):
        if 전달범위 == "server_reply" : await interaction.response.defer(ephemeral=False)
        else : await interaction.response.defer(ephemeral=True)

        if get_mention_delay_block(사용자.id, interaction.user.id) : 
            embed = discord.Embed(
                title=f"오류",
                description=f"해당 사용자에 의해 차단된 작업입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        user = 사용자
        content = 내용
        if 전달범위 == "server_reply" or 전달범위 == "server_dm" : 
            mention_server = interaction.guild.id
        elif 전달범위 == "all" : 
            mention_server = None
        else : 
            embed = discord.Embed(
                title=f"오류",
                description=f"전달범위가 잘못되었습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        status, until, reason = is_blocked(interaction.user)
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return

        if user.bot  :
            await interaction.followup.send("**[오류!]** 봇에게는 멘션지연을 예약할 수 없습니다.")
            return
        if len(content) > 130 and interaction.user.id != developer:
            embed = discord.Embed(
                title=f"오류",
                description=f"130자를 초과하는 멘션을 예약하기 위해서는 특수 권한이 필요합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 전달범위 == "server_reply" : 
            send_type = "reply"
        elif 전달범위 == "server_dm" : 
            send_type = "dm"
        elif 전달범위 == "all" : 
            send_type = "dm"
        
        mention_id = add_mention_delay_user(user.id, interaction.user.id, content, 0, mention_server, send_type)
        
        embed = discord.Embed(title="멘션 예약 완료", description=f"멘션 #{mention_id}\n\n{user.mention}님이 메시지를 보낼 시 해당 내용이 전달되도록 예약했습니다.", color=int("a5f0ff", 16))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="목록", description = "/멘션지연 유저나 /멘션지연 역할 명령어로 예약된 메시지들을 확인합니다.")
    async def mention_list(self, interaction: discord.Interaction, user: discord.Member):
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg)
            return
        
        await interaction.response.defer()
        
        if interaction.user.id != user.id and not interaction.user.guild_permissions.mention_everyone:
            await interaction.followup.send("다른 사용자에게 예약된 멘션의 목록을 확인하려면 특수 권한이 필요합니다.")
            return
        
        pending_mentions = get_mention_delay_user(user.id, "server", interaction.guild.id)
        
        if not pending_mentions:
            embed = discord.Embed(
                title=f"오류",
                description=f"{user.display_name}님에게 대기 중인 공개 멘션이 없습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        mention_ids = []
        
        embed = discord.Embed(title="대기 중인 멘션 목록", color=int("a5f0ff", 16))
        for m in pending_mentions:
            embed.add_field(name=f"멘션 ID: {m['id']}", value=f"보낸 사람: <@{m['sender_id']}>\n내용: {m['content']}", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        if interaction.user.id == user.id : 
            for mention in pending_mentions:
                done_mention_delay_user(mention["id"])

    @app_commands.command(name="취소", description = "/멘션지연으로 예약된 메시지 중 한 건을 취소합니다.")
    @app_commands.describe(id = "취소할 멘션 ID", 역할멘션지연일괄취소여부 = "/멘션지연 역할 명령어로 일괄 멘션지연 처리한 모든 유저의 멘션지연 건을 한 번에 취소할지 그 여부")
    @app_commands.choices(역할멘션지연일괄취소여부 = [
        app_commands.Choice(name = "/멘션지연 역할 명령어 사용에 의해 일괄적으로 같이 예약된 모든 멘션지연 건을 일괄적으로 취소 (옵션 활성화)", value = "True"),
        app_commands.Choice(name = "이 ID에 해당되는 건 하나만 취소 (옵션 비활성화, 기본값)", value = "False"),
    ])
    async def cancel_mention(self, interaction: discord.Interaction, id: int, 역할멘션지연일괄취소여부: str = "False"):
        await interaction.response.defer()
        mention_id = id
        if 역할멘션지연일괄취소여부 == "True" : 
            역할멘션지연일괄취소여부 = True
        else : 
            역할멘션지연일괄취소여부 = False

        status, until, reason = is_blocked(interaction.user)
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return

        if interaction.user.guild_permissions.mention_everyone:
            result = cancel_mention_delay_user(mention_id, True, interaction.user.id, interaction.guild.id, 역할멘션지연일괄취소여부)
            if result == True : 
                if 역할멘션지연일괄취소여부 == True : 
                    embed = discord.Embed(
                        title=f"완료",
                        description=f"멘션 #{mention_id} 및 해당 멘션 건 예약 시 일괄적으로 함께 예약된 다른 멘션들이 취소되었습니다.",
                        color=int("a5f0ff", 16)
                    )
                    await interaction.followup.send(embed = embed)
                    return
                else : 
                    embed = discord.Embed(
                        title=f"완료",
                        description=f"멘션 #{mention_id}(이)가 취소되었습니다.",
                        color=int("a5f0ff", 16)
                    )
                    await interaction.followup.send(embed = embed)
                    return
        
        result = cancel_mention_delay_user(mention_id, False, interaction.user.id, interaction.guild.id, 역할멘션지연일괄취소여부)
        if result == True : 
            if 역할멘션지연일괄취소여부 == True : 
                embed = discord.Embed(
                    title=f"완료",
                    description=f"멘션 #{mention_id} 및 해당 멘션 건 예약 시 일괄적으로 함께 예약된 다른 멘션들이 취소되었습니다.",
                    color=int("a5f0ff", 16)
                )
                await interaction.followup.send(embed = embed)
                return
            else : 
                embed = discord.Embed(
                    title=f"완료",
                    description=f"멘션 #{mention_id}(이)가 취소되었습니다.",
                    color=int("a5f0ff", 16)
                )
                await interaction.followup.send(embed = embed)
        else : 
            embed = discord.Embed(
                title=f"오류",
                description=f"해당 멘션을 취소할 수 없습니다. 멘션 ID가 유효한지 확인해 주세요.\n\n멘션 ID가 유효한 것이 확실한 경우, 취소 권한이 있는지 확인해 주세요. 아래 중 하나 이상에 해당되는 사용자여야 합니다.\n\n- 전달 범위가 \'이 서버\'인 멘션지연에 한해, 해당 서버에서 `@everyone, @here, 모든 역할 멘션하기` 권한을 보유하고 있음\n- 멘션지연을 예약한 본인",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)

