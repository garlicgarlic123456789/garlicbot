import discord
from discord import app_commands
from discord.ext import commands
from utils.helpers import *
from services.database_service import *

class AutoroleCog(commands.Cog):
    """자동 역할 관리 Cog"""

    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="추가", description="자동역할 설정을 추가합니다.")
    @app_commands.describe(역할="추가할 역할")
    @app_commands.choices(유저유형=[app_commands.Choice(name="모든 계정", value="all"), app_commands.Choice(name="유저 계정", value="user"), app_commands.Choice(name="봇 계정", value="bot")])
    @app_commands.default_permissions(administrator=True)
    async def add_autorole(self, interaction: discord.Interaction, 역할: discord.Role, 유저유형: str):
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
        
        autoroles = await get_autorole(interaction.guild.id)
        if len(autoroles) >= 10:
            embed = discord.Embed(
                title="오류",
                description="자동 역할 설정은 최대 10개까지 설정할 수 있습니다.",
                color=discord.Color.red()
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


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(AutoroleCog(bot))
