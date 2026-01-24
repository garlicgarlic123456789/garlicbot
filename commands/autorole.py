import discord
from discord import app_commands
from discord import *
from commands.define import *
from commands.database import *

class autorole(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="자동역할", description="자동역할 관련 명령어")
    
    @app_commands.command(name="추가", description="자동역할 설정을 추가합니다.")
    @app_commands.describe(역할="추가할 역할", 계정유형="역할을 추가할 계정의 유형")
    @app_commands.choices(계정유형=[app_commands.Choice(name="모든 계정", value="all"), app_commands.Choice(name="유저 계정", value="user"), app_commands.Choice(name="봇 계정", value="bot")])
    @app_commands.default_permissions(administrator=True)
    async def add_autorole(self, interaction: discord.Interaction, 역할: discord.Role, 계정유형: str, 강제: bool = False):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status:
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        유저유형 = 계정유형
        
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if 역할.position >= interaction.user.top_role.position and interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="오류",
                description=f"{역할.mention} 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        autoroles = await get_autorole(interaction.guild.id)
        if len(autoroles) >= 10:
            embed = discord.Embed(
                title="오류",
                description="자동 역할 설정은 최대 10개까지 설정할 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if 강제 == False :  
            if (역할.permissions.administrator) or (역할.permissions.ban_members) or (역할.permissions.kick_members) or (역할.permissions.manage_messages) or (역할.permissions.manage_roles) or (역할.permissions.manage_channels) or (역할.permissions.manage_guild) : 
                embed = discord.Embed(
                    title="알림",
                    description=f"자동 역할로 <@&{역할.id}> 역할을 추가하려고 합니다. 해당 역할에는 관리 권한이 하나 이상 포함되어 있습니다.\n\n마늘이 봇은 이 서버에 참가하는 {유저유형} 유형의 계정에 전부 <@&{역할.id}> 역할을 부여할 것입니다. 즉, 향후 이 서버에 참가하는 {유저유형} 유형의 계정에 관리 권한 중 하나 이상이 부여됩니다.\n\n의도하지 않은 작업일 수 있으므로 작업을 중단했습니다. 이 사항을 알고 있고, 자동역할 기능에 해당 역할을 추가하려고 하신다면, 입력하신 `/자동역할 추가` 명령어를 다시 전송해주시되, `강제`의 값을 `True`로 설정하시면 작업이 처리됩니다.",
                    color=discord.Color.yellow()
                )
                await interaction.followup.send(embed=embed)
                return

        result = await add_autorole(interaction.guild.id, 역할.id, 유저유형)
        if result[0]:
            embed = discord.Embed(
                title="완료",
                description=f"{역할.mention} 역할이 추가되었습니다.",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)
        else:
            if result[1] == "autorole_already_exists":
                embed = discord.Embed(
                    title="오류",
                    description=f"오류가 발생했습니다.\n\n{역할.mention} 역할은 이미 자동 역할 설정에 추가되어 있습니다. 설정을 수정하려는 경우 자동 역할 설정을 제거 후 다시 추가하시기 바랍니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            embed = discord.Embed(
                title="오류",
                description=f"오류가 발생했습니다.\n\n{역할.mention} 역할을 자동 역할 설정에 추가할 수 없습니다: `{result[1]}`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="제거", description="자동역할 설정을 제거합니다.")
    @app_commands.describe(역할="제거할 역할")
    @app_commands.default_permissions(administrator=True)
    async def remove_autorole(self, interaction: discord.Interaction, 역할: discord.Role):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status:
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if 역할.position >= interaction.user.top_role.position and interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="오류",
                description=f"{역할.mention} 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        result = await remove_autorole(interaction.guild.id, 역할.id)
        if result[0]:
            embed = discord.Embed(
                title="완료",
                description=f"{역할.mention} 역할이 제거되었습니다.",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)
        else:
            if result[1] == "autorole_not_found":
                embed = discord.Embed(
                    title="오류",
                    description=f"오류가 발생했습니다.\n\n{역할.mention} 역할은 자동 역할 설정에 추가되어 있지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            embed = discord.Embed(
                title="오류",
                description=f"오류가 발생했습니다.\n\n{역할.mention} 역할을 자동 역할 설정에서 제거할 수 없습니다: `{result[1]}`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="목록", description="자동역할 설정 목록을 확인합니다.")
    @app_commands.default_permissions(administrator=True)
    async def list_autorole(self, interaction: discord.Interaction):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status:
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        autoroles = await get_autorole(interaction.guild.id)

        embed = discord.Embed(
            title="자동 역할 설정 목록",
            color=int("a5f0ff", 16)
        )
        if len(autoroles) == 0:
            embed.description = "자동 역할 설정이 없습니다."
            embed.color = discord.Color.red()
        else:
            embed.description = f"자동 역할 설정이 {len(autoroles)}건 있습니다.\n\n"
            for autorole in autoroles:
                if autorole['bot_user'] == "all":
                    bot_user = "모든 계정"
                elif autorole['bot_user'] == "user":
                    bot_user = "유저 계정"
                elif autorole['bot_user'] == "bot":
                    bot_user = "봇 계정"
                embed.description += f"- <@&{autorole['role_id']}> 역할 (부여 대상: 서버에 참가하는 {bot_user})\n"
        await interaction.followup.send(embed=embed)
