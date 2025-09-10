import discord
from discord import app_commands
from discord import *
from commands.define import *
from commands.database import *

class phrase(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="문구", description="문구 관련 명령어")
    
    @app_commands.command(name="추가", description="문구를 추가합니다.")
    @app_commands.describe(문구이름="추가할 문구", 문구내용="추가할 문구", 사용권한="권한 설정")
    @app_commands.choices(
        사용권한=[
            app_commands.Choice(name="개인 (본인만 사용이 가능하도록 설정)", value="user"),
            app_commands.Choice(name="서버 유저 (해당 서버의 모든 유저가 사용이 가능하도록 설정)", value="server_all"),
            app_commands.Choice(name="서버 관리자 (해당 서버에서 멤버 차단하기 권한을 가진 관리자만 사용이 가능하도록 설정)", value="server_admin")
        ]
    )
    async def add_phrase(self, interaction: discord.Interaction, 문구이름: str, 문구내용: str, 사용권한: str):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status:
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        if (사용권한 == "server_all" or 사용권한 == "server_admin") and not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if len(문구내용) > 2000:
            embed = discord.Embed(
                title="오류",
                description="문구 내용이 2000자를 초과합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if len(문구이름) > 70:
            embed = discord.Embed(
                title="오류",
                description="문구 이름이 70자를 초과합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        문구내용.replace("\\n", "\n")
        
        if 사용권한 == "user" : 
            await add_phrase(문구이름, 사용권한, None, interaction.user.id, 문구내용)
        elif 사용권한 == "server_all" : 
            await add_phrase(문구이름, 사용권한, interaction.guild.id, None, 문구내용)
        elif 사용권한 == "server_admin" : 
            await add_phrase(문구이름, 사용권한, interaction.guild.id, None, 문구내용)
        else : 
            embed = discord.Embed(
                title="오류",
                description="잘못된 사용권한 값입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="완료",
            description=f"`{문구이름}` 문구가 추가되었습니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
        return
    
    @app_commands.command(name="제거", description="문구를 제거합니다.")
    @app_commands.describe(문구이름="제거할 문구")
    @app_commands.autocomplete(문구이름=phrase_autocomplete)
    async def remove_phrase(self, interaction: discord.Interaction, 문구이름: str):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status:
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        try : 
            문구이름 = int(문구이름)
        except : 
            embed = discord.Embed(
                title="오류",
                description="잘못된 문구 이름입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        phrase = await get_phrase(문구이름)

        if phrase is None:
            phrase = await get_phrase_by_name(문구이름, interaction.user.id, interaction.guild.id, interaction.user.guild_permissions.ban_members)
            if phrase is None:
                embed = discord.Embed(
                    title="오류",
                    description="해당 문구가 존재하지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
        
        if phrase["type"] == "user" and phrase["user_id"] != interaction.user.id:
            embed = discord.Embed(
                title="오류",
                description="해당 문구가 존재하지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if (phrase["type"] == "server_all" or phrase["type"] == "server_admin") and phrase["server_id"] != interaction.guild.id:
            embed = discord.Embed(
                title="오류",
                description="해당 문구가 존재하지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if (phrase["type"] == "server_admin" or phrase["type"] == "server_all") and not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        await remove_phrase(문구이름)
        
        embed = discord.Embed(
            title="완료",
            description=f"문구가 제거되었습니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
        return
    
    @app_commands.command(name="출력", description="문구를 출력합니다.")
    @app_commands.describe(문구이름="출력할 문구")
    @app_commands.autocomplete(문구이름=phrase_autocomplete)
    async def print_phrase(self, interaction: discord.Interaction, 문구이름: str, 개인응답: bool = False):
        if 개인응답 == False:
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)
            
        status, until, reason = is_blocked(interaction.user)
        if status:
            await interaction.followup.send(f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.")
            return
        
        # 문구 ID 또는 이름으로 조회
        phrase = None
        try:
            phrase_id = int(문구이름)
            phrase = await get_phrase(phrase_id)
        except:
            pass
        if not phrase:
            phrase = await get_phrase_by_name(
                문구이름,
                interaction.user.id,
                interaction.guild.id,
                interaction.user.guild_permissions.ban_members,
            )
        if not phrase:
            embed = discord.Embed(
                title="오류",
                description="해당 문구가 존재하지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        if phrase["type"] == "user" and phrase["user_id"] != interaction.user.id:
            embed = discord.Embed(
                title="오류",
                description="해당 문구가 존재하지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if (phrase["type"] == "server_all" or phrase["type"] == "server_admin") and phrase["server_id"] != interaction.guild.id:
            embed = discord.Embed(
                title="오류",
                description="해당 문구가 존재하지 않습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if phrase["type"] == "server_admin" and not interaction.user.guild_permissions.ban_members:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        if ("discord.com/invite/" in phrase["phrase"] or "discord://-/invite/" in phrase["phrase"] or "discord.gg/" in phrase["phrase"]) and 개인응답 == False:
            embed = discord.Embed(
                title="오류",
                description="문구에 디스코드 서버 초대 링크가 포함되어 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"문구 {phrase['name']}",
            description=phrase["phrase"],
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
        return