import discord
import re
from discord import app_commands
from commands.database import *
from commands.define import *
from commands import define
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import asyncio
import datetime
import holidays
from discord.ui import View, Button
import base64

class xp_import_export(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="경험치데이터", description="경험치 데이터 관련 명령어")

    @app_commands.command(name = "가져오기", description = "경험치 데이터를 가져옵니다.")
    @app_commands.default_permissions(administrator = True)
    @app_commands.choices(
        옵션 = [
            app_commands.Choice(name = "기존 경험치 데이터를 삭제하고 새 데이터를 추가 (권장)", value = "add"),
            app_commands.Choice(name = "기존 경험치 데이터를 삭제하고 새 데이터로 대체", value = "overwrite"),
        ]
    )
    async def 가져오기(self, interaction: discord.Interaction, 파일: discord.Attachment, 옵션: str) :
        await interaction.response.defer()

        file = 파일

        if interaction.user.id != interaction.guild.owner_id : 
            embed = discord.Embed(
                title = "오류",
                description = "권한이 부족합니다. 다음 권한이 필요합니다: `소유자`",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if file.size > 1024 * 1024:
            embed = discord.Embed(
                title = "오류",
                description = "파일 크기가 너무 큽니다. 1MB 이하여야 합니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if not file.filename.endswith('.json'):
            embed = discord.Embed(
                title = "오류",
                description = "파일 형식이 올바르지 않습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        try : 
            await import_xp(interaction.guild.id, file, 옵션)
            embed = discord.Embed(
                title = "완료",
                description = f"완료되었습니다.",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
        
        except Exception as e : 
            embed = discord.Embed(
                title = "오류",
                description = "오류",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)

    @app_commands.command(name = "내보내기", description = "경험치 데이터를 내보냅니다.")
    @app_commands.default_permissions(administrator = True)
    @app_commands.describe(채널 = "내보내기 데이터를 받을 채널")
    async def 내보내기(self, interaction: discord.Interaction, 채널: discord.TextChannel) :
        await interaction.response.defer()
        if interaction.user.id != interaction.guild.owner_id : 
            embed = discord.Embed(
                title = "오류",
                description = "권한이 부족합니다. 다음 권한이 필요합니다: `소유자`",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        channel = interaction.guild.get_channel(채널.id)
        if channel is None : 
            embed = discord.Embed(
                title = "오류",
                description = "채널이 올바르지 않습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        embed = discord.Embed(
            title = "처리 중",
            description = f"경험치 데이터 내보내기 처리 중입니다. 처리가 완료되면 <#{채널.id}>에 결과가 전송됩니다.\n\n주의: 내보내기 작업 중 다른 내보내기 작업을 추가로 시작할 시 내보내기 결과 파일이 올바르지 않게 처리될 수 있습니다.",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)
        file_path = await export_xp(interaction.guild.id)
        export_file = discord.File(file_path, filename=file_path)
        await channel.send(f"{interaction.guild.owner.mention} 경험치 데이터 내보내기가 완료되었습니다.", file = export_file)