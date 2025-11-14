import discord
import re
from discord import app_commands
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
        super().__init__(name="철도", description="철도 관련 명령어")

    @app_commands.command(name = "빠른환승", description = "수도권 전철 빠른 환승 정보를 확인합니다.")
    @app_commands.describe(노선 = "정보를 확인할 노선을 입력해 주세요.", 역 = "정보를 확인할 역을 입력해 주세요. (뒤에 \'역\' 자 제외)")
    async def 빠른환승(self, interaction: discord.Interaction, 노선: str, 역: str) :
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        if 역 == "총신대입구" : 
            역 = "이수"
        
        역 += "역"

        try : 
            transfer_info = fast_transfer[노선]
        except Exception as e :
            await interaction.followup.send("**[오류!]** 노선 정보를 가져오는 도중 오류가 발생했습니다. 등록되지 않은 노선이거나 노선명이 유효하지 않은 경우 일반적으로 이 오류가 표시됩니다.")
            return

        try :
            await interaction.followup.send(f"{역}의 빠른 환승 정보는 다음과 같습니다:\n\n{transfer_info[역]}")
        except Exception as e :
            global error
            print(f"오류 #{error}: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            error += 1
            return
    
    @app_commands.command(name = "도착정보", description = "특정 역의 전철 도착 정보를 확인합니다.")
    @app_commands.describe(역종류 = "확인할 역의 종류", 역명 = "역명 (뒤에 \'역\' 자 제외)", 열차종류 = "확인할 열차의 종류 (선택 사항)", 행선지 = "확인할 열차의 행선지 (선택 사항)")
    @app_commands.choices(
        역종류 = [
            app_commands.Choice(name = "수도권 전철 (일부 경전철 노선 미지원)", value = "수도권"),
            app_commands.Choice(name = "동남권 전철 (부산김해경전철, 동해선 미지원)", value = "부산"),
        ]
        열차종류 = [app_commands.Choice(name="전체", value="전체"), app_commands.Choice(name="특급", value="특급"), app_commands.Choice(name="급행", value="급행"), app_commands.Choice(name="일반", value="일반")]
    )
    async def 지하철도착정보(self, interaction: discord.Interaction, 역종류: str, 역명: str, 열차종류: str = None, 행선지: str = None):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        if 역종류 == "수도권" : 
            if 열차종류 == "전체" : 
                열차종류 = None
            
            실제입력역명 = 역명
            
            if 역명 == "평택지제" : 
                역명 = "지제"
            elif 역명 == "총신대입구" or 역명 == "이수" or 역명 == "이수(총신대입구)" : 
                역명 = "총신대입구(이수)"
            elif 역명 == "응암" : 
                역명 = "응암순환(상선)"
            elif 역명 == "공릉" : 
                역명 = "공릉(서울산업대입구)"
            elif 역명 == "남한산성입구" : 
                역명 = "남한산성입구(성남법원, 검찰청)"
            elif 역명 == "대모산입구" : 
                역명 = "대모산"
            elif 역명 == "천호" : 
                역명 = "천호(풍납토성)"
            elif 역명 == "몽촌토성" : 
                역명 = "몽촌토성(평화의문)"
            elif 역명 == "쌍용" : 
                역명 = "쌍용(나사렛대)"
            elif 역명 == "신정" : 
                역명 = "신정(은행정)"
            elif 역명 == "오목교" : 
                역명 = "오목교(목동운동장앞)"
            elif 역명 == "군자" : 
                역명 = "군자(능동)"
            elif 역명 == "아차산" : 
                역명 = "아차산(어린이대공원후문)"
            elif 역명 == "광나루" : 
                역명 = "광나루(장신대)"
            elif 역명 == "굽은다리" : 
                역명 = "굽은다리(강동구민회관앞)"
            elif 역명 == "올림픽공원" : 
                역명 = "올림픽공원(한국체대)"
            elif 역명 == "새절" : 
                역명 = "새절(신사)"
            elif 역명 == "증산" : 
                역명 = "증산(명지대앞)"
            elif 역명 == "월드컵경기장" : 
                역명 = "월드컵경기장(성산)"
            elif 역명 == "대흥" : 
                역명 = "대흥(서강대앞)"
            elif 역명 == "안암" : 
                역명 = "안암(고대병원앞)"
            elif 역명 == "월곡" : 
                역명 = "월곡(동덕여대)"
            elif 역명 == "상월곡" : 
                역명 = "상월곡(한국과학기술연구원)"
            elif 역명 == "화랑대" : 
                역명 = "화랑대(서울여대입구)"
            elif 역명 == "어린이대공원" : 
                역명 = "어린이대공원(세종대)"
            elif 역명 == "숭실대입구" : 
                역명 = "숭실대입구(살피재)"
            elif 역명 == "상도" : 
                역명 = "상도(중앙대앞)"
            elif "신촌" in 역명 : 
                if "경의" in 역명 or "민자" in 역명 or "지상" in 역명 : 
                    역명 = "신촌(경의중앙선)"
                elif "지하" in 역명 or "2" in 역명 : 
                    역명 = "신촌"
                else : 
                    embed = discord.Embed(
                        title="오류",
                        description=f"경의선 신촌역과 2호선 신촌역을 구분하여 입력해 주세요.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    return

            try : 
                data = get_subway_info(역명)

                arrivals = data["realtimeArrivalList"]
            except Exception as e : 
                global error
                print(f"오류 #{error}: {e}")
                embed = discord.Embed(
                    title="오류",
                    description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                error += 1
                return

            print(arrivals)
            print("----------------------")

            subway_info = {}

            for arrival in arrivals:
                if 열차종류 is not None and arrival["btrainSttus"] != 열차종류 : 
                    continue
                if 행선지 != None and arrival["bstatnNm"] != 행선지 : 
                    continue
                
                if arrival["subwayId"] == "1001" :
                    line = "1호선"
                elif arrival["subwayId"] == "1002" :
                    line = "2호선"
                elif arrival["subwayId"] == "1003" :
                    line = "3호선"
                elif arrival["subwayId"] == "1004" :
                    line = "4호선"
                elif arrival["subwayId"] == "1005" :
                    line = "5호선"
                elif arrival["subwayId"] == "1006" :
                    line = "6호선"
                elif arrival["subwayId"] == "1007" :
                    line = "7호선"
                elif arrival["subwayId"] == "1008" :
                    line = "8호선"
                elif arrival["subwayId"] == "1063" :
                    line = "경의중앙선"
                elif arrival["subwayId"] == "1065" :
                    line = "공항철도"
                elif arrival["subwayId"] == "1077" :
                    line = "신분당선"
                elif arrival["subwayId"] == "1075" :
                    line = "수인분당선"
                elif arrival["subwayId"] == "1081" :
                    line = "경강선"
                elif arrival["subwayId"] == "1067" :
                    line = "경춘선"
                elif arrival["subwayId"] == "1092" :
                    line = "우이신설선"
                elif arrival["subwayId"] == "1009" :
                    line = "9호선"
                elif arrival["subwayId"] == "1093" :
                    line = "서해선"
                elif arrival["subwayId"] == "1032" : 
                    line = "GTX-A"
                elif arrival["subwayId"] == "1094" : 
                    line = "신림선"
                else : 
                    line = arrival["subwayId"]  # 노선 ID (1001: 1호선, 1002: 2호선 등)
                direction = arrival["updnLine"]  # 상행/하행
                arrival_info = arrival["arvlMsg2"]
                match = re.search(r"\[(\d+)\]번째 전역 \((.*?)\)", arrival_info)
                if match:
                    number = int(match.group(1))
                    content = match.group(2)
                    if content == "지제" : 
                        content = "평택지제"
                    elif content == "총신대입구" or content == "이수(총신대입구)" or content == "총신대입구(이수)" : 
                        content = "이수"
                    
                    if number == 2 : 
                        arrival_info = f"전전역 ({content})"
                    else : 
                        arrival_info = f"{number}전역 ({content})"
                elif arrival_info == f"{역명} 도착" : 
                    arrival_info = "당역 도착"
                elif arrival_info == f"{역명} 진입" : 
                    arrival_info = "당역 진입"
                elif arrival_info == f"{역명} 출발" : 
                    arrival_info = "당역 출발"
                
                train_info = {
                    "열차번호": arrival["btrainNo"],
                    "행선지": arrival["bstatnNm"] + " (" + arrival["btrainSttus"] + ")",
                    "도착 정보": arrival_info,
                    "도착 예정": f"약 {int(arrival['barvlDt']) // 60} 분 {int(arrival['barvlDt']) % 60}초 후"
                }

                if line not in subway_info:
                    subway_info[line] = {}

                if direction not in subway_info[line]:
                    subway_info[line][direction] = []

                subway_info[line][direction].append(train_info)

            text = f"{실제입력역명}역의 지하철 도착 정보입니다. 참고용으로만 사용하시기 바랍니다.\n"

            if len(subway_info) == 0 : 
                text += "\n도착 정보가 비어 있습니다."
            else : 
                # 정리된 도착 정보 출력
                for line, directions in subway_info.items():
                    text += f"\n노선: {line} 도착 정보\n"
                    for direction, trains in directions.items():
                        text += f"- 방향: {direction}\n"
                        for train in trains:
                            text += f"  - 열차번호: {train['열차번호']}, 행선지: {train['행선지']}, 현재 위치: {train['도착 정보']}, 도착 예정: {train['도착 예정']}\n"
            embed = discord.Embed(
                title=f"{실제입력역명}역의 지하철 도착 정보",
                description=text,
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)
        elif 역종류 == "부산" : 
            if 열차종류 == "급행" or 열차종류 == "특급" : 
                embed = discord.Embed(
                    title = "오류",
                    description = "현재 동남권 전철에는 급행 또는 특급 열차가 운행하지 않습니다.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
            
            # 추후 작성 예정
    
    @app_commands.command(name = "열차정보", description = "열차번호를 입력하고 열차에 대한 정보를 확인합니다.")
    @app_commands.describe(열차번호 = "머리 글자 및 열차 번호", 날짜 = "해당 열차의 날짜 (입력 형식: YYYYMMDD)", 상하행 = "열차의 방향", 개인응답 = "개인응답 사용 여부")
    @app_commands.choices(상하행 = [app_commands.Choice(name="상행", value="상행"), app_commands.Choice(name="하행", value="하행"), app_commands.Choice(name="외선순환 (2호선)", value="외선"), app_commands.Choice(name="내선순환 (2호선)", value="내선")])
    async def train_info(self, interaction: discord.Interaction, 열차번호: str, 상하행: str, 날짜: str = None, 개인응답: bool = False) : 
        await interaction.response.defer(ephemeral=개인응답)

        status, until, reason = is_blocked(interaction.user)
        
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        if 날짜 is None : 
            날짜 = await today_to_text()

        try : 
            기준시각 = await today_to_text2()
            위치, 지연 = await get_train_info_railblue(열차번호, 날짜)
            timetable = await get_train_timetable(열차번호, 날짜, 상하행)
            embed2 = discord.Embed(
                title = f"열차 #{열차번호} 실시간 정보",
                description = f"**[주의!]** 이 정보는 참고용으로만 사용하시기 바랍니다.\n\n- 위치: {위치}\n- 지연: {지연}",
                color = int("a5f0ff", 16),
            )
            embed2.set_footer(text=f"정보 업데이트 시각: {기준시각}")
            if timetable[0] == False : 
                embed2 = discord.Embed(
                    title = f"열차 #{열차번호} 실시간 정보",
                    description = f"**[주의!]** 이 정보는 참고용으로만 사용하시기 바랍니다.\n\n- 위치: {위치}\n- 지연: {지연}",
                    color = int("a5f0ff", 16),
                )
                embed2.set_footer(text=f"정보 업데이트 시각: {기준시각}")
                embed = discord.Embed(
                    title=f"열차 #{열차번호} 시각표 정보",
                    description=f"**[주의!]** 이 정보는 시각표를 기준으로 한 정보입니다. 실제 도착 시각과 차이가 있을 수 있으며 가급적 아래의 지연 시간 정보를 함께 참고하시기 바랍니다.\n\n시각표 정보를 조회할 수 없었습니다. 지원되지 않는 노선이거나 열차 번호가 올바르지 않을 수 있습니다.",
                    color = int("a5f0ff", 16)
                )
                await interaction.followup.send(embeds=[embed, embed2])
                return
            else : 
                embed2 = discord.Embed(
                    title = f"열차 #{열차번호} 실시간 정보",
                    description = f"**[주의!]** 이 정보는 참고용으로만 사용하시기 바랍니다.\n\n- 위치: {위치}\n- 지연: {지연}",
                    color = int("a5f0ff", 16),
                )
                embed2.set_footer(text=f"정보 업데이트 시각: {기준시각}")
            pages = generate_pages(열차번호, timetable[2])
            view = Paginator(pages, embed2)
            await interaction.followup.send(embeds=[pages[0], embed2], view=view)
        except Exception as e : 
            global error
            print(f"오류 #{error}: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            error += 1
            return

ITEMS_PER_PAGE = 5

def generate_pages(train, data):
    items = list(data.items())
    pages = []

    # 데이터 쪼개기
    for i in range(0, len(items), ITEMS_PER_PAGE):
        chunk = items[i:i+ITEMS_PER_PAGE]

        embed = discord.Embed(
            title=f"열차 #{train} 시각표 정보",
            description=f"**[주의!]** 이 정보는 시각표를 기준으로 한 정보입니다. 실제 도착 시각과 차이가 있을 수 있으며 가급적 아래의 지연 시간 정보를 함께 참고하시기 바랍니다.",
            color=int("a5f0ff", 16)
        )
        for k, v in chunk:
            역명 = k
            통과여부 = v['stop']
            도착시간 = v['arrivetime']
            출발시간 = v['departtime']

            title = f"{역명}역 ({통과여부})"
            if 통과여부 == "정차" : 
                des = f"- 도착 시각: {도착시간}\n- 출발 시각: {출발시간}"
            elif 통과여부 == "출발" : 
                des = f"- 출발 시각: {출발시간}"
            elif 통과여부 == "종착" : 
                des = f"- 도착 시각: {도착시간}"
            else : 
                des = f"- 통과 시각: {출발시간}"
            embed.add_field(name=title, value=des, inline=False)
        
        page_count = len(items)//ITEMS_PER_PAGE
        if len(items) % ITEMS_PER_PAGE != 0 : 
            page_count += 1

        embed.set_footer(text=f"페이지 {i//ITEMS_PER_PAGE + 1} / {page_count}")

        pages.append(embed)

    return pages

class Paginator(View):
    def __init__(self, pages, embed):
        super().__init__(timeout=300)
        self.pages = pages
        self.embed = embed
        self.current_page = 0

    @discord.ui.button(label="이전", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embeds=[self.pages[self.current_page], self.embed], view=self)
        else:
            await interaction.response.defer()  # 변화 없을 시 무시

    @discord.ui.button(label="다음", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embeds=[self.pages[self.current_page], self.embed], view=self)
        else:
            await interaction.response.defer()

async def parse_train_info(text):
    # 3. '운행중' 포함 & 분 초 단위 지연
    m = re.match(r'^(.+?) - (.+?), (\d+)분 (\d+)초 지연 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, int(m.group(3)), int(m.group(4))]

    # 2. '운행중' 포함 & 초 단위 지연
    m = re.match(r'^(.+?) - (.+?), (\d+)초 지연 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, 0, int(m.group(3))]

    # 7. '조기 운행중' 분+초
    m = re.match(r'^(.+?) - (.+?), (\d+)분 (\d+)초 조기 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, -int(m.group(3)), -int(m.group(4))]
    
    m = re.match(r'^(.+?) - (.+?), (\d+)초 조기 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, 0, -int(m.group(3))]

    # 8. '지연 운행중' 분만
    m = re.match(r'^(.+?) - (.+?), (\d+)분 지연 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, int(m.group(3)), 0]

    # 9. '조기 운행중' 분만
    m = re.match(r'^(.+?) - (.+?), (\d+)분 조기 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, -int(m.group(3)), 0]

    # 10. '정시 운행중'
    m = re.match(r'^(.+?) - (.+?), 정시 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), True, 0, 0]
    
    # 1. '운행중' 포함 & 지연/조기 없을 때
    m = re.match(r'^(.+?) - (.+?) 운행중$', text)
    if m:
        return [True, m.group(1), m.group(2), False]

    # 5. '조착'
    m = re.match(r'^(.+?)에 (\d+)분 (\d+)초 조착$', text)
    if m:
        return [False, m.group(1), True, -int(m.group(2)), -int(m.group(3))]
    
    m = re.match(r'^(.+?)에 (\d+)분 조착$', text)
    if m:
        return [False, m.group(1), True, -int(m.group(2)), 0]
    
    m = re.match(r'^(.+?)에 (\d+)초 조착$', text)
    if m:
        return [False, m.group(1), True, 0, -int(m.group(2))]

    # 6. '지연 도착'
    m = re.match(r'^(.+?)에 (\d+)분 (\d+)초 지연 도착$', text)
    if m:
        return [False, m.group(1), True, int(m.group(2)), int(m.group(3))]
    
    m = re.match(r'^(.+?)에 (\d+)분 지연 도착$', text)
    if m:
        return [False, m.group(1), True, int(m.group(2)), 0]
    
    m = re.match(r'^(.+?)에 (\d+)초 지연 도착$', text)
    if m:
        return [False, m.group(1), True, 0, int(m.group(2))]

    # 11. '정시 도착'
    m = re.match(r'^(.+?)에 정시 도착$', text)
    if m:
        return [False, m.group(1), True, 0, 0]

    # 4. '도착' 단독
    m = re.match(r'^(.+?) 도착$', text)
    if m:
        return [False, m.group(1), False]
    
    if text == "운행대기" : 
        return [False, "출발역", False]
    elif "로 열차번호 변경" in text : 
        return [False, "종착역", False]
    elif "운행 종료" in text : 
        return [False, "종착역", False]

    # 만약 어느 유형에도 해당하지 않으면 None 반환
    return None

async def get_train_info_railblue(train, date):
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    driver.get(f"https://rail.blue/railroad/logis/Default.aspx?company=&train={train}&date={date}#!")
    await asyncio.sleep(2.5)
    train_info = driver.find_element(by = By.ID, value = "spDrive")
    print(train_info.text)
    train_info = await parse_train_info(train_info.text)
    '''
    반환값 설명:
    0번째 값이 True => 역과 역 사이를 이동 중
    False => 특정 역에 정차 중

    True인 경우 1번째 값이 이전역, 2번째 값이 다음역을 의미하며, 3번째 값이 지연정보가 있는지 True/False로 나타냄. 지연정보가 있다면 4~5번째 값이 지연된 시간을 의미(각각 분, 초)
    False인 경우 1번째 값이 정차 중인 역역을 의미하며, 2번째 값이 지연정보가 있는지 True/False로 나타냄. 지연정보가 있다면 3~4번째 값이 지연된 시간을 의미(각각 분, 초)
    지연 정보에서 음수값은 현재 조기 운행 중임을 의미하고 양수값은 현재 지연 운행 중임을 의미함.
    '''
    if train_info is None : 
        return "*(알 수 없음)*", "*(알 수 없음)*"

    if train_info[0] : 
        loc_msg = f"{train_info[1]} → {train_info[2]}"
        if train_info[3] : 
            if train_info[4] >= 0 : 
                if train_info[4] == 0 and train_info[5] == 0 : 
                    delay_msg = "정시 운행 중"
                elif train_info[4] == 0 : 
                    if train_info[5] > 0 : 
                        delay_msg = f"{train_info[5]}초 지연 운행 중"
                    else : 
                        delay_msg = f"{train_info[5]}초 조기 운행 중"
                else : 
                    delay_msg = f"{train_info[4]}분 {train_info[5]}초 지연 운행 중"
            else : 
                train_info[4] = abs(train_info[4])
                train_info[5] = abs(train_info[5])
                if train_info[4] == 0 : 
                    delay_msg = f"{train_info[5]}초 조기 운행 중"
                else : 
                    delay_msg = f"{train_info[4]}분 {train_info[5]}초 조기 운행 중"
        else : 
            delay_msg = "*(알 수 없음)*"
    else : 
        loc_msg = f"{train_info[1]}"
        if train_info[2] : 
            if train_info[3] >= 0 : 
                if train_info[3] == 0 and train_info[4] == 0 : 
                    delay_msg = "정시 운행 중"
                elif train_info[3] == 0 : 
                    if train_info[4] > 0 : 
                        delay_msg = f"{train_info[4]}초 지연 운행 중"
                    else : 
                        delay_msg = f"{train_info[4]}초 조기 운행 중"
                else : 
                    delay_msg = f"{train_info[3]}분 {train_info[4]}초 지연 운행 중"
            else : 
                train_info[3] = abs(train_info[3])
                train_info[4] = abs(train_info[4])
                if train_info[3] == 0 : 
                    delay_msg = f"{train_info[4]}초 조기 운행 중"
                else : 
                    delay_msg = f"{train_info[3]}분 {train_info[4]}초 조기 운행 중"
        else : 
            delay_msg = "*(알 수 없음)*"
    
    driver.quit()
    
    return loc_msg, delay_msg

async def today_to_text() : 
    return datetime.date.today().strftime("%Y%m%d")

async def today_to_text2() : 
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def date_to_datetime(date) : 
    return datetime.datetime.strptime(date, "%Y%m%d")

async def date_to_datetime2(date) : 
    return date.strftime("%Y-%m-%d 05:00:00")

async def date_to_datetime3(date) : 
    return date.strftime("%Y년 %m월 %d일")

async def date_weekend_or_bot(date) : 
    weekday = date.weekday()
    if weekday == 5 or weekday == 6 : 
        return True
    else : 
        return False

async def return_time_now() : 
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    return now_str

async def today_is_hoilday(date) : 
    # 한국 공휴일 목록
    kr_holidays = holidays.KR()

    # 오늘이 공휴일인지 확인
    if date in kr_holidays:
        return True
    else:
        return False

def _time_sort_key(depart_time):
    if not depart_time:
        return float('inf')  # 없음 -> 맨 뒤
    try:
        h, m, s = map(int, depart_time.split(':'))
    except Exception:
        return float('inf')
    if 0 <= h <= 2:
        h += 24
    return h * 60 * 60 + m * 60 + s

# 키 이름이 'departtime' 또는 'departttime' 중 어떤 것이든 처리
def get_depart_key(item):
    return item.get('departtime') or item.get('departttime')

async def get_train_timetable(trainnum, date, updown) : 
    date = await date_to_datetime(date)
    if await date_weekend_or_bot(date) : 
        weekend = "주말"
    elif await today_is_hoilday(date) : 
        weekend = "공휴일"
    else : 
        weekend = "평일"
    
    line = "선"
    time = await date_to_datetime2(date)
    
    url = f"http://apis.data.go.kr/B553766/schedule/getTrainSch?dataType=JSON&serviceKey={train_timetable_api_key}&numOfRows=100&tmprTmtblYn=N&upbdnbSe={updown}&wkndSe={weekend}&lineNm={line}&searchDt={time}&trainno={trainnum}"

    try : 
        response = requests.get(url)
        if response.status_code != 200 : 
            response.raise_for_status()
        data = response.json()
        data = data["response"]["body"]["items"]["item"]

        result = {}

        for i in data : 
            if i["trainno"] != trainnum : 
                continue
            if i["stnNm"] == "서울역" : 
                station_name = "서울"
            else : 
                station_name = i["stnNm"]
            result[station_name] = {
                "arrivetime": i["trainArvlTm"],
                "departtime": i["trainDptreTm"]
            }
            if i["trainArvlTm"] is None and i["stnNm"] == i["dptreStnNm"] : 
                result[station_name]["stop"] = "출발"
            elif i["trainDptreTm"] is None and i["stnNm"] == i["arvlStnNm"] : 
                result[station_name]["stop"] = "종착"
            elif i["trainArvlTm"] is None : 
                result[station_name]["stop"] = "통과"
            else : 
                result[station_name]["stop"] = "정차"
        
        result = sorted(result.items(), key=lambda kv: _time_sort_key(get_depart_key(kv[1])))
        # 필요하면 dict로 다시 만듭니다 (Python 3.7+에서 순서 보존)
        result = dict(result)
        
        print(result)
        if result == {} : 
            return [False, date, None]
        return [True, date, result]
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        # response code 출력
        print(response.status_code)
        return [False, date, None, e]
    except Exception as e : 
        print(e)
        return [False, date, None, e]

def get_subway_info(station_name):
    url = f"http://swopenapi.seoul.go.kr/api/subway/{train_arrivals_api_key}/json/realtimeStationArrival/1/25/{station_name}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        
        return data  # Returning JSON response for further processing
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None