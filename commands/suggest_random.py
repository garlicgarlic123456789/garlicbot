import discord

from discord import app_commands
import sys
from discord.ext import commands

from commands.define import *
import random

train_random_list_seoul = ["운정중앙역", "신창(순천향대)역", "천안역", "1호선 천안 급행", "수원역", "경강선 여주역", "성남역", "김포골병라인", "김포공항역", "서해선 소사역", "경의중앙선 일산역", "대곡역", "잠실역", "사당역", "4호선 남태령 ~ 선바위 구간", "동작(현충원)역", "동두천역", "삼성역", "양주역", "방학역", "청량리역", "왕십리역", "경복궁역", "광화문역", "서울역", "경의터널선 양원 ~ 용문 구간", "시청역", "6호선 버뮤다 응암지대", "강남역", "헬도림역", "신도림역", "1호선 종각 드리프트", "경의재앙선 청량리 ~ 망우 구간", "잠실역", "지평역", "덕소역", "별내역", "수서역", "서울역", "동탄역", "구로역", "철도 여행 가지 않기", "1호선 연천역", "1호선 인천역", "1호선 천안역", "2호선 한바퀴", "3호선 대화역", "3호선 오금역", "4호선 진접역", "4호선 오이도역", "5호선 방화역", "5호선 하남검단산역", "5호선 마천역", "6호선 응암역", "6호선 신내역", "7호선 장암역", "7호선 석남역", "8호선 별내역", "8호선 복정역", "9호선 개화역", "9호선 중앙보훈병원역", "경의중앙선 문산역", "경의중앙선 용문역", "경춘선 전 구간", "신분당선 광교(경기대)역", "신분당선 신사역", "수인분당선 청량리역", "수인분당선 왕십리역", "수인분당선 인천역", "용인 경전철", "의정부 경전철", "신림선"]
train_random_list = ["오송역", "강릉역", "춘천역", "구포역", "서울역", "수원역", "영등포역", "광명역", "수서역", "천안아산역", "서대구역", "동대구역", "부산역", "경주역", "울산(통도사)역", "동탄역", "평택지제역", "대전역", "김천(구미)역", "광주송정역", "철도 여행 가지 않기"]

breakfast_list = ["고구마 + 삶은 계란", "바나나 + 우유 or 두유", "오트밀 + 바나나 + 견과류", "고구마 + 계란 + 견과류", "달걀찜 + 밥 + 김 + 나물 반찬", "스크램블 에그 + 토스트 + 아보카도", "요거트 + 그래놀라 + 블루베리", "샌드위치 (닭가슴살 or 참치 + 치즈 + 채소)", "에너지바 + 커피 or 차"]
lunch_list = ["컵밥", "스테이크 + 구운 채소 + 감자퓨레", "토마토 파스타 + 마늘||요리||빵", "김치찌개 + 밥 + 계란후라이", "제육볶음 + 쌈채소 + 된장국", "햄버거 + 감자튀김 + 탄산음료", "김밥 + 우동", "라면", "샌드위치 + 수프", "카레라이스 + 돈가스", "규동 (소고기덮밥) + 단무지", "돈가스 + 밥 + 미소된장국", "짜장면 + 군만두", "짬뽕 + 중국식 볶음밥", "치킨 샐러드 + 크루통 + 요거트 드레싱"]
dinner_list = ["치킨", "삼겹살 + 쌈장", "라면 + 김밥", "감자튀김 + 치즈소스", "마라샹궈 + 흰밥", "연어 사시미 + 미소국 + 밥", "일본식 카레라이스 + 샐러드", "초밥 세트 + 장국", "연어 스테이크 + 아스파라거스 + 감자퓨레", "삼계탕 + 김치", "불고기 + 쌈채소 + 밥", "리코타치즈 샐러드 + 닭가슴살", "치킨 시저 샐러드 + 수프", "탕수육 + 계란볶음밥", "중국식 채소볶음 + 두부구이"]

punishment_list = [
    "상대방의 소원을 하나 들어주기 (최대 지속 시간: 24시간)",
    "1시간 동안 냥체 사용",
    "상대방이 원하는 프로필 사진을 24시간 동안 사용",
    "타임아웃 3분 부여받기",
    "벌칙 면제!",
    "상대방이 원하는 닉네임을 24시간 동안 사용",
    "상대방에게 애교 떨어주기",
    "타임아웃 1분 부여받기",
    "6시간 동안 상대방의 노예가 되기",
]

quotes = [
    "성공은 최종적인 것이 아니며, 실패는 치명적인 것이 아니다. 중요한 것은 계속하려는 용기이다. - 윈스턴 처칠",
    "인생은 용감한 모험이거나 아무것도 아니다. - 헬렌 켈러",
    "미래는 현재 우리가 무엇을 하는가에 달려 있다. - 마하트마 간디",
    "꿈을 꾸는 자만이 그 꿈을 이룰 수 있다. - 슈바이처",
    "가장 큰 위험은 위험 없는 삶이다. - 스티븐 코비",
    "행복은 습관이다. 그것을 연습하라. - 엘버트 허버드",
    "모든 어려움 뒤에는 기회가 숨어 있다. - 앨버트 아인슈타인",
    "당신이 할 수 있다고 믿든, 할 수 없다고 믿든, 당신이 옳다. - 헨리 포드",
    "흔들리지 않고 피는 꽃이 어디 있으랴",
]

def setup(bot):
    @bot.tree.command(name = "골라", description = "목록에서 랜덤으로 1개(또는 일부 항목)를 선택합니다.")
    @app_commands.describe(목록 = "전체 리스트 (쉼표와 띄어쓰기로 구분)", 개수 = "선택할 개수")
    async def choose(interaction: discord.Interaction, 목록: str, 개수: int = 1) :
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        목록 = 목록.split(", ")
        if 개수 >= len(목록) : 
            embed = discord.Embed(
                title = "오류",
                description = f"목록에 포함된 항목의 개수는 선택할 개수보다 적어야 합니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if 개수 == 1 : 
            temp = random.choice(목록)
            embed = discord.Embed(
                title = "추천된 항목",
                description = f"추천된 항목: {temp}",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return
        else : 
            temp = random.sample(목록, 개수)
            embed = discord.Embed(
                title = "추천된 항목",
                description = f"추천된 항목: {', '.join(map(str, temp))}",
                color = int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return

    @bot.tree.command(name = "추천받기", description = "점심 메뉴, 철도 여행지 등을 추천 받습니다.")
    @app_commands.describe(종류 = "추천받을 것")
    @app_commands.choices(종류 = [
        app_commands.Choice(name = "아침 메뉴", value = "아침 메뉴"),
        app_commands.Choice(name = "점심 메뉴", value = "점심 메뉴"),
        app_commands.Choice(name = "저녁 메뉴", value = "저녁 메뉴"),
        app_commands.Choice(name = "철도 여행지 (수도권)", value = "철도 여행지 수도권"),
        app_commands.Choice(name = "철도 여행지 (전국)", value = "철도 여행지 전국"),
        app_commands.Choice(name = "유저 추천", value = "유저 추천"),
        app_commands.Choice(name = "벌칙 추천", value = "벌칙 추천"),
        app_commands.Choice(name = "홀짝 추천", value = "홀짝 추천"),
        app_commands.Choice(name = "명언 추천", value = "명언 추천"),
    ])
    async def suggest_random(interaction: discord.Interaction, 종류: str) :
        global train_random_list, train_random_list_seoul
        await interaction.response.defer()

        status, until, reason = is_blocked(interaction.user)
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        if 종류 == "철도 여행지 수도권" :
            temp = random.randint(0, len(train_random_list_seoul) - 1)
            await interaction.followup.send(f"추천된 철도 여행지: {train_random_list_seoul[temp]}")
            return
        elif 종류 == "철도 여행지 전국" : 
            temp = random.randint(0, len(train_random_list) - 1)
            await interaction.followup.send(f"추천된 철도 여행지: {train_random_list[temp]}")
            return
        elif 종류 == "아침 메뉴" :
            global breakfast_list
            temp = random.randint(0, len(breakfast_list) - 1)
            await interaction.followup.send(f"추천된 아침 메뉴: {breakfast_list[temp]}")
            return
        elif 종류 == "점심 메뉴" :
            global lunch_list
            temp = random.randint(0, len(lunch_list) - 1)
            await interaction.followup.send(f"추천된 점심 메뉴: {lunch_list[temp]}")
            return
        elif 종류 == "저녁 메뉴" :
            global dinner_list
            temp = random.randint(0, len(dinner_list) - 1)
            await interaction.followup.send(f"추천된 저녁 메뉴: {dinner_list[temp]}")
            return
        elif 종류 == "유저 추천" :
            guild = interaction.guild
            if guild is None:
                await interaction.followup.send("서버에서만 사용할 수 있는 기능입니다.")
                return
            
            members = [member for member in guild.members if not member.bot]
            if not members:
                await interaction.followup.send("추천할 유저가 없습니다.")
                return
            
            selected_member = random.choice(members)
            embed = discord.Embed(
                title=f"추천된 유저", # name
                description=f"추천된 유저: {selected_member.mention} ({selected_member.display_name})",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
            return
        elif 종류 == "벌칙 추천" :
            global punishment_list
            temp = random.randint(0, len(punishment_list) - 1)
            await interaction.followup.send(f"추천된 벌칙: {punishment_list[temp]}")
            return
        elif 종류 == "홀짝 추천" : 
            temp = random.randint(0, 1)
            if temp == 0 : 
                temp = "홀"
            else : 
                temp = "짝"
            await interaction.followup.send(f"추천 결과: {temp}")
            return
        elif 종류 == "명언 추천" :
            global quotes
            quote = random.choice(quotes)
            embed = discord.Embed(
                title="오늘의 명언",
                description=f"\"{quote}\"",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
            return