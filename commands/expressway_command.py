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

class train_command(app_commands.Group) : 
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
        
        begin_id = await get_tollgate_id_by_name(출발요금소) # 출발 요금소의 요금소 id
        end_id = await get_tollgate_id_by_name(도착요금소) # 도착 요금소의 요금소 id

        # https://data.ex.co.kr/openapi/trtm/realUnitTrtm?key={ex_api}&type=json&iStartUnitCode=510&iEndUnitCode=651&sumTmUnitTypeCode=3&numOfRows=97&iStartEndStdTypeCode=2

        

async def get_tollgate_id_by_name(tollgate_name: str) : 
    data = await get_tollgate_info_by_name(tollgate_name)
    print(data)

    if data['count'] == 0 : 
        raise ValueError(f"한국도로공사 api에서 `{tollgate_name}` 요금소를 찾을 수 없었습니다.")
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