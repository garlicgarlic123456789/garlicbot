import discord
from datetime import datetime
from discord import app_commands


def setup(bot):
    @bot.tree.command(name="채팅시간확인", description="특정 시간 동안 사용자의 채팅 활동을 계산합니다.")
    @app_commands.describe(
        시작시각="시작 시각 (형식: YYYY-MM-DD HH:MM)",
        종료시각="종료 시각 (형식: YYYY-MM-DD HH:MM)"
    )
    async def 채팅시간확인(interaction: discord.Interaction, 시작시각: str, 종료시각: str):
        if interaction.user.id != 1305492487137267722:
            embed = discord.Embed(
                title="오류",
                description="권한이 부족합니다. 다음 권한이 필요합니다: `개발자`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.defer()
        try:
            await interaction.followup.send("처리 중입니다.")
            start_time = datetime.strptime(시작시각, "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(종료시각, "%Y-%m-%d %H:%M")

            if start_time >= end_time:
                await interaction.followup.send("종료 시각은 시작 시각보다 늦어야 합니다.")
                return

            user_messages = {}
            
            for channel in interaction.guild.text_channels:
                try:
                    async for message in channel.history(after=start_time, before=end_time, limit=None):
                        user = message.author.id
                        if not message.author.bot :
                            timestamp = message.created_at

                            if user not in user_messages:
                                user_messages[user] = []
                            
                            user_messages[user].append(timestamp)
                except Exception as e:
                    print(f"채널 {channel.name}에서 데이터를 가져오는 중 오류 발생: {e}")
            
            temp = ""
            for user, timestamps in user_messages.items():
                timestamps.sort()
                total_time = 0
                session_start = None
                session_end = None
                
                for timestamp in timestamps:
                    if session_start is None:
                        session_start = timestamp
                        session_end = timestamp
                    elif (timestamp - session_end).total_seconds() / 60 <= 3:
                        session_end = timestamp
                    else:
                        total_time += (session_end - session_start).total_seconds() / 60
                        session_start = timestamp
                        session_end = timestamp
                
                if session_start and session_end:
                    total_time += (session_end - session_start).total_seconds() / 60
                    
                temp += f"\n<@{user}>: {total_time:.1f}"
                print(f"<@{user}>: {total_time:.3f}")

            embed = discord.Embed(
                title="서버 채팅 활동 보고서 (단위: 분)",
                description=f"{start_time.strftime('%Y-%m-%d %H:%M')}부터 {end_time.strftime('%Y-%m-%d %H:%M')}까지\n{temp}",
                color=int("a5f0ff", 16)
            )
            
            await interaction.followup.send(embed=embed)

        except ValueError:
            await interaction.followup.send("날짜 형식이 잘못되었습니다. 올바른 형식: YYYY-MM-DD HH:MM")
        except Exception as e:
            await interaction.followup.send(f"오류가 발생했습니다: {str(e)}")
