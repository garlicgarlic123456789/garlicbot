import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv
from commands.define import *

REGION_COORDS = {
    '서울': {'lat': 37.5665, 'lon': 126.9780},
    '부산': {'lat': 35.1796, 'lon': 129.0756},
    '대구': {'lat': 35.8714, 'lon': 128.6014},
    '인천': {'lat': 37.4563, 'lon': 126.7052},
    '광주': {'lat': 35.1595, 'lon': 126.8526},
    '제주': {'lat': 33.4996, 'lon': 126.5312},
    '백령도': {'lat': 37.9796, 'lon': 124.6276},
    '춘천': {'lat': 37.8800, 'lon': 127.7253},
    '수원': {'lat': 37.2636, 'lon': 127.0286},
    '천안': {'lat': 36.8151, 'lon': 127.1139},
    '청주': {'lat': 36.6359, 'lon': 127.4912},
    '강릉': {'lat': 37.7513, 'lon': 128.8760},
    '전주': {'lat': 35.8205, 'lon': 127.1509},
    '대전': {'lat': 36.3504, 'lon': 127.3845},
    '안동': {'lat': 36.5662, 'lon': 128.7201},
    '울릉도/독도': {'lat': 37.4138, 'lon': 131.8694},
    '목포': {'lat': 34.8128, 'lon': 126.3917},
    '여수': {'lat': 34.7608, 'lon': 127.6622},
    '울산': {'lat': 35.5384, 'lon': 129.3114}
}

REGION_CHOICES = [
    discord.app_commands.Choice(name=key, value=key)
    for key in REGION_COORDS
]

def get_weather_emoji(desc):
    if "맑음" in desc: return "☀️"
    if "구름" in desc: return "⛅"
    if "비" in desc: return "🌧️"
    if "눈" in desc: return "❄️"
    if "천둥" in desc: return "⛈️"
    return "🌫️"


def setup(bot):
    @bot.tree.command(name="날씨", description="지역을 선택하여 현재 날씨를 확인합니다.")
    @app_commands.describe(지역="날씨를 볼 지역 선택")
    @app_commands.choices(지역=REGION_CHOICES)
    async def 날씨(interaction: discord.Interaction, 지역: discord.app_commands.Choice[str]):
        await interaction.response.defer()

        load_dotenv()
        OWM_API_KEY = os.getenv("Weather_api")

        coords = REGION_COORDS[지역.value]
        lat, lon = coords['lat'], coords['lon']
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric&lang=kr"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    global error
                    print(f"오류 #{error}: {resp.status}")
                    embed = discord.Embed(
                        title = "오류",
                        description = f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                        color = int("a5f0ff", 16)
                    )
                    await interaction.followup.send(embed=embed)
                    error += 1
                    return
                data = await resp.json()

        weather = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        emoji = get_weather_emoji(weather)

        embed = discord.Embed(title=f"{지역.name}의 현재 날씨", description=f"{emoji} {weather}", color=int("a5f0ff", 16))
        embed.add_field(name="🌡 온도", value=f"{temp}°C", inline=True)
        embed.add_field(name="🥵 체감온도", value=f"{feels_like}°C", inline=True)
        embed.add_field(name="💧 습도", value=f"{humidity}%", inline=True)
        embed.set_footer(text="출처: OpenWeatherMap API")

        await interaction.followup.send(embed=embed)