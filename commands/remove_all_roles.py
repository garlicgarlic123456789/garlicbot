import discord

from discord import app_commands

from commands.define import *


def setup(bot) : 
    @bot.tree.command(name="모든역할회수", description="특정 사용자의 모든 역할을 회수합니다.")
    @app_commands.default_permissions(manage_roles=True)
    async def 모든역할회수(interaction: discord.Interaction, 사용자: discord.User):
        if 사용자.top_role >= interaction.user.top_role :
            embed = discord.Embed(
                title="오류",
                description="역할 회수 대상의 최상위 역할이 명령어를 사용한 사용자의 최상위 역할보다 높거나 같습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return
        
        guild = interaction.guild
        if guild is None:
            embed = discord.Embed(
                title="오류",
                description="guild_only_command",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        member = guild.get_member(사용자.id)
        if member is None:
            embed = discord.Embed(
                title="오류",
                description="해당 사용자를 찾을 수 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        # 명령어 실행 권한 확인
        if not interaction.user.guild_permissions.manage_roles:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `역할 관리하기`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        await interaction.response.defer()
        
        try:
            # 역할 제거
            roles = member.roles[1:]  # @everyone 역할 제외
            for role in roles:
                await member.remove_roles(role)

            embed = discord.Embed(
                title=f"완료", # name
                description=f"{사용자.mention}의 모든 역할을 회수했습니다.",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed, ephemeral=False)
        except discord.Forbidden : 
            embed = discord.Embed(
                title="오류",
                description=f"봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `역할 관리하기` 권한이 있는지 확인해 주세요.\n- 봇의 최상위 역할이 역할 회수 대상 사용자의 최상위 역할보다 낮거나 같지는 않은지 확인해 주세요.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        except Exception as e:
            global error
            print(f"오류 #{error}: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            error += 1
            return