import discord
from discord import app_commands

from bot_app.commands.slash_ai_support_handlers import (
    run_show_help_slash_command,
    run_show_profile_image_slash_command,
)
from commands.define import is_blocked


def setup(bot):
    @bot.tree.command(name="도움말", description="도움말을 확인합니다.")
    async def show_help(interaction: discord.Interaction):
        await run_show_help_slash_command(interaction)

    @bot.tree.command(name="프로필사진", description="특정 사용자의 프로필 사진을 보여줍니다.")
    @app_commands.describe(사용자="프로필 사진을 확인할 대상 사용자")
    async def show_profile_image(interaction: discord.Interaction, 사용자: discord.User):
        await run_show_profile_image_slash_command(
            interaction,
            target_user=사용자,
            context={
                "is_blocked": is_blocked,
            },
        )
