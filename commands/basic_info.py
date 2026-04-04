import discord
from discord import app_commands

from commands.define import is_blocked


def setup(bot):
    @bot.tree.command(name="도움말", description="도움말을 확인합니다.")
    async def show_help(interaction: discord.Interaction):
        embed = discord.Embed(
            title="도움말",
            description="[도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce018010ba92e5741e6ac72a?pvs=4)",
            color=int("a5f0ff", 16),
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="프로필사진", description="특정 사용자의 프로필 사진을 보여줍니다.")
    @app_commands.describe(사용자="프로필 사진을 확인할 대상 사용자")
    async def show_profile_image(interaction: discord.Interaction, 사용자: discord.User):
        status, until, reason = is_blocked(interaction.user)
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.response.send_message(msg)
            return

        await interaction.response.defer()
        avatar_url = 사용자.display_avatar.url

        embed = discord.Embed(
            title=f"{사용자.display_name}님의 프로필 사진",
            color=int("a5f0ff", 16),
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"요청자: {interaction.user.id}")

        await interaction.followup.send(embed=embed)
