import discord
import re
from discord import app_commands
from commands.database import *
from commands.define import *
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import asyncio
import datetime
import holidays
from discord.ui import View, Button

class expressway_command(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="고속도로", description="고속도로 관련 명령어")

    @app_commands.command(name = "소요시간", description = "고속도로 요금소 간 소요시간을 확인합니다.")
    @app_commands.describe(출발요금소 = "출발 요금소의 이름", 도착요금소 = "도착 요금소의 이름")
    async def howmuchtime(self, interaction: discord.Interaction, 출발요금소: str, 도착요금소: str) :
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        try : 
            begin_id = await get_tollgate_id_by_name(출발요금소) # 출발 요금소의 요금소 id
            end_id = await get_tollgate_id_by_name(도착요금소) # 도착 요금소의 요금소 id

            time = await get_expressway_time(begin_id, end_id, 2)
        except ValueError as e : 
            embed = discord.Embed(
                title = "오류",
                description = f"명령어 실행 도중 오류가 발생했습니다.\n\n{e}",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if time['Avg'] == '-1' or time['Min'] == '0' or time['Max'] == '0' : 
            try: 
                time = await get_expressway_time(begin_id, end_id, 1)
            except ValueError as e : 
                embed = discord.Embed(
                    title = "오류",
                    description = f"명령어 실행 도중 오류가 발생했습니다.\n\n{e}",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
        
        if time['Avg'] == '-1' or time['Min'] == '0' or time['Max'] == '0' : 
            embed = discord.Embed(
                title = "오류",
                description = f"소요시간 정보가 비어있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        embed = discord.Embed(
            title = f"{출발요금소} → {도착요금소} 소요시간",
            description = f"주의: 이 정보는 보증되지 않습니다. 참고용으로만 사용하시기 바랍니다.\n\n- 최소 소요시간: 약 {print_time(int(time['Min']))}\n- 최대 소요시간: 약 {print_time(int(time['Max']))}\n- 예상 소요시간: 약 {print_time(int(time['Avg']))}",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)

def print_time(x):
    days = x // 86400
    hours = (x % 86400) // 3600
    minutes = (x % 3600) // 60
    seconds = x % 60

    parts = []
    if hours == 0 and minutes == 0 and seconds == 0 :
        if days > 0:
            parts.append(f"{days}일")
    elif minutes == 0 and seconds == 0 :
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0 or days > 0:  # 시간이 0이어도 '일'이 있으면 포함
            parts.append(f"{hours}시간")
    elif seconds == 0 :
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0 or days > 0:  # 시간이 0이어도 '일'이 있으면 포함
            parts.append(f"{hours}시간")
        if minutes > 0 or hours > 0 or days > 0:  # 분이 0이어도 '일' 또는 '시간'이 있으면 포함
            parts.append(f"{minutes}분")
    else : 
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0 or days > 0:  # 시간이 0이어도 '일'이 있으면 포함
            parts.append(f"{hours}시간")
        if minutes > 0 or hours > 0 or days > 0:  # 분이 0이어도 '일' 또는 '시간'이 있으면 포함
            parts.append(f"{minutes}분")
        parts.append(f"{seconds}초")  # 초는 항상 포함

    return " ".join(parts)

async def get_expressway_time(begin_id: str, end_id: str, tmtype: int) : 
    url = f"https://data.ex.co.kr/openapi/odhour/upDownTrafficTime?key={ex_api}&type=json&startUnitCode={begin_id}&endUnitCode={end_id}&tmType={tmtype}&carType=1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data['count'] == 0 : 
            timeAvg = '-1'
            timeMax = '0'
            timeMin = '0'
            return {
                'Avg': timeAvg,
                'Max': timeMax,
                'Min': timeMin,
            }
        else : 
            data = data['list'][0]
            print(data)
            timeAvg = data['timeAvg']
            timeMax = data['timeMax']
            timeMin = data['timeMin']
            return {
                'Avg': timeAvg,
                'Max': timeMax,
                'Min': timeMin,
            }
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

async def get_tollgate_id_by_name(tollgate_name: str) : 
    data = await get_tollgate_info_by_name(tollgate_name)
    print(data)

    if data['count'] == 0 : 
        raise ValueError(f"한국도로공사 api에서 `{tollgate_name}` 요금소를 찾을 수 없었습니다.\n\n요청 URL: `https://data.ex.co.kr/openapi/basicinfo/unitList?key=[마스킹]&type=json&unitName={tollgate_name}`")
    elif data['count'] == 1 : 
        return data['unitLists'][0]['unitCode']
    elif data['count'] < 0 : 
        raise ValueError(f"한국도로공사 api의 반환값이 유효하지 않습니다. 나중에 다시 시도하세요.")
    else : 
        data2 = data['unitLists']
        for i in data2 : 
            if i["unitName"] == tollgate_name : 
                return i["unitCode"]
        
        return data2[0]["unitCode"]


async def get_tollgate_info_by_name(tollgate_name):
    url = f"https://data.ex.co.kr/openapi/basicinfo/unitList?key={ex_api}&type=json&unitName={tollgate_name}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        return data
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None