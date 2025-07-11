# To do: 
# 1. 채널 목록을 채널 이름만 주는게 아니라 채널 권한을 분석하여 비공개채널인지 공개채널인지도 같이 제시
# 2. 역할 정보도 같이 ai에게 제공
# 3. 프롬프트 개선

import discord
from discord.ext import commands
import google.generativeai as genai
from google.genai import types
import asyncio

async def collect_message(bot, interaction, start_message_link, end_message_link):
    start_message_channel = start_message_link.split("/")[-2]
    if end_message_link is not None : 
        end_message_channel = end_message_link.split("/")[-2]
        if start_message_channel != end_message_channel:
            return [False, "different_channel"]
    start_message_id = start_message_link.split("/")[-1]
    if end_message_link is not None : 
        end_message_id = end_message_link.split("/")[-1]
    else : 
        end_message_id = None
    channel = bot.get_channel(int(start_message_channel))
    if not channel:
        return [False, "invaild_channel"]
    messages = []
    if end_message_id is not None : 
        async for message in channel.history(limit=None, after=discord.Object(int(start_message_id), type = discord.Message), before=discord.Object(int(end_message_id), type = discord.Message), oldest_first=True):
            messages.append(f"{message.author.display_name}: {message.content}")
    else : 
        async for message in channel.history(limit=None, after=discord.Object(int(start_message_id), type = discord.Message), oldest_first=True):
            messages.append(f"{message.author.display_name}: {message.content}")
    if not messages:
        return [False, "no_message"]
    return [True, messages]

async def get_channel_list(guild):
    channels = []
    for channel in guild.channels:
        if isinstance(channel, (discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel, discord.ForumChannel)):
            # 채널 타입 문자열 변환
            if isinstance(channel, discord.CategoryChannel):
                type_str = "카테고리"
            elif isinstance(channel, discord.TextChannel):
                type_str = "텍스트"
            elif isinstance(channel, discord.VoiceChannel):
                type_str = "음성"
            elif isinstance(channel, discord.ForumChannel):
                type_str = "포럼"
            else:
                continue

            channels.append(f"{channel.name} ({type_str})")
    if channels : 
        return [True, channels]
    else : 
        return [False, "no_channel"]

async def advice_main(bot, interaction, original_message, message_provide, start_message_link, end_message_link, channel_provide, prompt, role):
    if not interaction.guild:
        embed = discord.Embed(title="오류", description="invaild_guild", color=discord.Color.red())
        await original_message.reply(embed = embed)
        return
    if message_provide : 
        if start_message_link is None : 
            embed = discord.Embed(title="오류", description="invaild_start_message_link", color=discord.Color.red())
            await original_message.reply(embed = embed)
            return
        messages = await collect_message(bot, interaction, start_message_link, end_message_link)
    else : 
        messages = [True, "*(제공되지 않음)*"]
    if not messages[0]:
        embed = discord.Embed(title="오류", description=messages[1], color=discord.Color.red())
        await original_message.reply(embed = embed)
        return
    else : 
        messages = messages[1]
        if channel_provide : 
            channels = await get_channel_list(interaction.guild)
            if channels[0]:
                channels = channels[1]
            else : 
                embed = discord.Embed(title="오류", description=channels[1], color=discord.Color.red())
                await original_message.reply(embed = embed)
                return
        else : 
            channels = [True, "*(제공되지 않음)*"]
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = await asyncio.to_thread(
            model.generate_content,
            f"""
            이름이 '{interaction.guild.name}'인 디스코드 서버에서 아래와 같은 유저가 서버에 관해 조언을 구하고 있습니다.

            유저 이름: {interaction.user.display_name} ({interaction.user.name})
            유저의 역할: {role}
            하려는 조언(유저의 프롬프트): {prompt}

            서버의 메시지 기록 중 일부: {messages}
            서버의 채널 구성: {channels} 
            """
        )
        embed = discord.Embed(title="완료", description=f"인공지능의 조언은 다음과 같습니다: \n\n{response.text}", color=int("a5f0ff", 16))
        await original_message.reply(embed = embed)
        return





