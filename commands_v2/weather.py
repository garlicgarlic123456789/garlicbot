"""
GarlicBot Weather Commands

날씨 정보를 확인하는 명령어들입니다.
"""

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from config import settings, constants, permissions
from utils.helpers import format_timestamp


class WeatherCommands(commands.Cog):
    """날씨 관련 명령어 Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    def get_weather_emoji(self, description: str) -> str:
        """날씨 설명에 따른 이모지를 반환합니다."""
        for key, emoji in constants.WEATHER_EMOJIS.items():
            if key in description:
                return emoji
        return "🌫️"  # 기본 이모지

    @app_commands.command(name="날씨", description="지역을 선택하여 현재 날씨를 확인합니다.")
    @app_commands.describe(지역="날씨를 볼 지역 선택")
    async def weather(self, interaction: discord.Interaction, 지역: str):
        """선택한 지역의 현재 날씨 정보를 표시합니다."""

        # 권한 확인
        permission_config = permissions.PermissionConfig()
        if not await permission_config.check_user_permission(interaction.user, "weather"):
            await interaction.response.send_message(
                f"**[오류!]** {interaction.user.mention}님은 이 명령어를 사용할 권한이 없습니다.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # 지역 좌표 확인
        if 지역 not in constants.REGION_COORDS:
            await interaction.followup.send(
                f"**[오류!]** '{지역}'은(는) 지원하지 않는 지역입니다.",
                ephemeral=True
            )
            return

        # API 키 확인
        weather_api_key = settings.WEATHER_API_KEY
        if not weather_api_key:
            await interaction.followup.send(
                "**[오류!]** 날씨 API 키가 설정되지 않았습니다. 관리자에게 문의해주세요.",
                ephemeral=True
            )
            return

        coords = constants.REGION_COORDS[지역]
        lat, lon = coords['lat'], coords['lon']
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_api_key}&units=metric&lang=kr"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        self.logger.error(f"Weather API error: {resp.status} - {resp.reason}")
                        embed = discord.Embed(
                            title="오류",
                            description="날씨 정보를 가져오는 중 오류가 발생했습니다.\n관리자에게 문의해주세요.",
                            color=discord.Color.red()
                        )
                        await interaction.followup.send(embed=embed)
                        return

                    data = await resp.json()

            # 날씨 데이터 추출
            weather_desc = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']

            emoji = self.get_weather_emoji(weather_desc)

            # 임베드 생성
            embed = discord.Embed(
                title=f"{지역}의 현재 날씨",
                description=f"{emoji} {weather_desc}",
                color=int("a5f0ff", 16)
            )

            embed.add_field(name="🌡 온도", value=f"{temp}°C", inline=True)
            embed.add_field(name="🥵 체감온도", value=f"{feels_like}°C", inline=True)
            embed.add_field(name="💧 습도", value=f"{humidity}%", inline=True)

            embed.set_footer(text=f"출처: OpenWeatherMap API | {format_timestamp(interaction.created_at)}")

            await interaction.followup.send(embed=embed)

            self.logger.info(f"Weather command executed by {interaction.user} for region: {지역}")

        except Exception as e:
            self.logger.error(f"Weather command error: {e}")
            embed = discord.Embed(
                title="오류",
                description="날씨 정보를 처리하는 중 오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Cog를 봇에 추가합니다."""
    await bot.add_cog(WeatherCommands(bot))