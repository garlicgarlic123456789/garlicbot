import discord
from discord import app_commands
from discord.ext import commands
from commands.database import *
from commands.define import *

class ServerRuleModal(discord.ui.Modal, title="서버 규정 설정"):
    규정 = discord.ui.TextInput(
        label="서버 규정",
        placeholder="서버 규정을 입력하세요.",
        style=discord.TextStyle.paragraph
    )
    규정가이드 = discord.ui.TextInput(
        label="규정 가이드",
        placeholder="규정 가이드를 입력하세요. (운영진이나 AI 판사 봇이 업무 수행 시 참고할 수 있는 가이드)",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        self.규정 = self.규정.value
        self.규정가이드 = self.규정가이드.value
        if len(self.규정) > 1500 or len(self.규정가이드) > 1500 : 
            embed = discord.Embed(
                title="오류",
                description="서버 규정 또는 규정 가이드가 1500자를 초과합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        # 여기서 DB 저장 함수 호출 가능
        await update_server_rules(self.guild_id, str(self.규정), str(self.규정가이드))

        embed = discord.Embed(
            title="완료",
            description="서버 규정이 정상적으로 설정되었습니다.",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)

def setup(bot) : 
    @bot.tree.command(name="서버규정설정", description="서버 규정을 설정합니다.")
    @app_commands.default_permissions(administrator=True)
    async def server_rules_setting(interaction: discord.Interaction):
        status, until, reason = is_blocked(interaction.user)
        if status : 
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg)
            return
        
        modal = ServerRuleModal(interaction.guild.id)
        await interaction.response.send_modal(modal)
    
    @bot.tree.command(name="서버규정삭제", description="서버 규정을 삭제합니다.")
    @app_commands.default_permissions(administrator=True)
    async def server_rules_delete(interaction: discord.Interaction):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status : 
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        temp = await delete_server_rules(interaction.guild.id)
        if temp[0] : 
            embed = discord.Embed(
                title="완료",
                description="서버 규정이 정상적으로 삭제되었습니다!",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)
        else : 
            if temp[1] == "server_rules_not_found" : 
                embed = discord.Embed(
                    title="오류",
                    description="서버 규정이 설정되어 있지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
            else : 
                embed = discord.Embed(
                    title="오류",
                    description="서버 규정 삭제에 실패했습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name="서버규정확인", description="서버 규정을 확인합니다.")
    async def server_rules_check(interaction: discord.Interaction):
        status, until, reason = is_blocked(interaction.user)
        if status : 
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg)
            return
        
        await interaction.response.defer()
        
        temp = await get_server_rules(interaction.guild.id)
        if temp[0] : 
            rule = temp[1]
            rule_guide = temp[2]
        else : 
            rule = "설정된 규정이 없습니다."
            rule_guide = "설정된 규정 가이드가 없습니다."

        embed = discord.Embed(
            title="서버 규정",
            description=f"```{rule}```",
            color=int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
    