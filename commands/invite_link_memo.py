import discord
from discord import app_commands
from commands.define import *
from commands.database import *
import asyncio
import os
load_dotenv()

class invite_link_memo(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="초대링크메모", description="초대링크 메모 관련 명령어")
    
    @bot.tree.command(name = "설정", description = "특정 초대 링크에 대해 메모를 추가 또는 수정합니다.")
    @app_commands.default_permissions(administrator = True)
    @app_commands.describe(초대링크 = "생성한 초대 링크 (discord.gg/나 discord.com/invite/는 생략하고 입력)", 메모 = "메모 내용")
    async def 초대링크메모(self, interaction: discord.Interaction, 초대링크: str, 메모: str = None) : 
        await interaction.response.defer(ephemeral=True)
        status, until, reason = is_blocked(interaction.user)
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        if len(메모) > 150 : 
            embed = discord.Embed(
                title = "오류",
                description = "메모의 값은 150자를 초과할 수 없습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        await update_server_join_route_memo(interaction.guild.id, 초대링크, 메모)

        embed = discord.Embed(
            title = "완료",
            description = f"완료되었습니다.",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name = "삭제", description = "특정 초대 링크에 대해 메모를 삭제합니다.")
    @app_commands.default_permissions(administrator = True)
    @app_commands.describe(초대링크 = "초대 링크 (discord.gg/나 discord.com/invite/는 생략하고 입력)")
    async def delete_invitelinkmemo(self, interaction: discord.Interaction, 초대링크: str) : 
        await interaction.response.defer(ephemeral=True)
        status, until, reason = is_blocked(interaction.user)
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        await delete_server_join_route_memo(interaction.guild.id, 초대링크)

        embed = discord.Embed(
            title = "완료",
            description = f"완료되었습니다.",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed=embed)
    
    @bot.tree.command(name = "목록", description = "메모가 있는 초대 링크 목록을 확인합니다.")
    @app_commands.default_permissions(administrator = True)
    async def delete_invitelinkmemo(self, interaction: discord.Interaction) : 
        await interaction.response.defer(ephemeral=True)
        status, until, reason = is_blocked(interaction.user)
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        result = await list_server_join_route_memo(interaction.guild.id)

        content = "이 서버의 초대 링크 목록입니다.\n\n"

        for i in result : 
            content += f"- {i["link"]}: {i["memo"]}\n"
        
        embed = discord.Embed(
            title = "메모가 추가된 초대 링크 목록",
            description = content,
            color = int("a5f0ff", 16),
        )
        await interaction.followup.send(embed=embed)