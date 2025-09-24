import discord
import subprocess
from discord.ext import commands, tasks
from discord import app_commands
from datetime import timedelta

async def add_timeout(user: discord.Member, seconds: int, reason: str = None, ignore_ongoing_timeout_duration: bool = False) : 
    if ignore_ongoing_timeout_duration == True : 
        new_timeout = discord.utils.utcnow() + timedelta(seconds=seconds)
    else : 
        if user.timed_out_until and user.timed_out_until > discord.utils.utcnow():
            # 기존 타임아웃 시간에 추가
            new_timeout = user.timed_out_until + timedelta(seconds=seconds)
        else:
            # 현재 시간에서 타임아웃 시간 계산
            new_timeout = discord.utils.utcnow() + timedelta(seconds=seconds)
    
    await user.edit(timed_out_until=new_timeout, reason=reason)
