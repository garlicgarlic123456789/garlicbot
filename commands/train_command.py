import discord
import re
from discord import app_commands
from commands.database import *
from commands.define import *
from commands import define
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import asyncio
import datetime
import holidays
from discord.ui import View, Button
import base64
from itertools import groupby

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
        except Exception:
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
    
    r'''
    @app_commands.command(name = "도착정보", description = "수도권 전철 역의 전철 도착 정보를 확인합니다.")
    @app_commands.describe(역명 = "역명 (뒤에 \'역\' 자 제외)", 열차종류 = "확인할 열차의 종류 (선택 사항)", 행선지 = "확인할 열차의 행선지 (선택 사항)")
    @app_commands.choices(열차종류 = [app_commands.Choice(name="전체", value="전체"), app_commands.Choice(name="특급", value="특급"), app_commands.Choice(name="급행", value="급행"), app_commands.Choice(name="일반", value="일반")])
    async def 지하철도착정보(self, interaction: discord.Interaction, 역명: str, 열차종류: str = None, 행선지: str = None):
        await interaction.response.defer()
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
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
    '''

    @app_commands.command(name = "수도권전철경로", description = "출발역과 도착역을 입력하고 수도권 전철 경로를 탐색합니다.")
    @app_commands.choices(탐색옵션 = [
        app_commands.Choice(name = "최소 시간", value = "duration"),
        app_commands.Choice(name = "최소 환승", value = "transfer"),
    ])
    @app_commands.describe(
        출발역 = "출발역 역명 (\'역\' 자 제외하고 입력)",
        도착역 = "도착역 역명 (\'역\' 자 제외하고 입력)",
        출발시각 = "출발 시각 (YYYY-MM-DD HH:MM:SS 형식)",
        탐색옵션 = "경로 옵션",
        개발자용 = "개발자용 옵션. 기본값은 False이며, 개발자의 확인 없이 활성화하지 않는 것을 권장합니다.",
    )
    async def find_way(self, interaction: discord.Interaction, 출발역: str, 도착역: str, 출발시각: str, 탐색옵션: str, 개발자용: bool = False) : 
        await interaction.response.defer()

        입력출발역 = 출발역
        입력도착역 = 도착역

        if 출발역 == "지하서울역" : 
            출발역 = "서울역"
        elif 출발역 == "지하수원" : 
            출발역 = "수원"
        elif 출발역 == "서울" : 
            출발역 = "서울역"
        elif 출발역 == "지하청량리" : 
            출발역 = "청량리"
        elif 출발역 == "지제" : 
            출발역 = "평택지제"
        
        if 도착역 == "지하서울역" : 
            도착역 = "서울역"
        elif 도착역 == "지하수원" : 
            도착역 = "수원"
        elif 도착역 == "서울" : 
            도착역 = "서울역"
        elif 도착역 == "지하청량리" : 
            도착역 = "청량리"
        elif 도착역 == "지제" : 
            도착역 = "평택지제"
        try : 
            result = await lookup_seoul_route(출발역, 도착역, 탐색옵션, 출발시각)
        except Exception as e : 
            embed = discord.Embed(
                title = "오류",
                description = "오류가 발생하였습니다. 올바르지 않은 역명을 입력했거나 지원되지 않는 노선(GTX-A)의 경로를 탐색하려 했을 수 있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        total_time = result["total_time"]
        path = result["path"]
        transfer_time = result["transfer_time"]

        if 개발자용 : 
            print(f"디버그 정보: {interaction.user.id}가 {입력출발역} → {입력도착역} 경로 탐색\n- 소요시간: {total_time}\n- 환승 횟수: {transfer_time}\n- 경로: 하단 참고\n\n{path}\n")
        
        embed = discord.Embed(
            title = f"{입력출발역} → {입력도착역} 경로",
            description = f"참고: 현재 API 제공자 사정으로 인해 GTX 경로는 제공되지 않습니다.\n\n- 소요시간: {total_time}\n- 환승 횟수: {transfer_time}\n- 경로: 하단 참고\n\n{path}",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)
        return
    
    @app_commands.command(name = "레일블루정책확인", description = "철도 관련 명령어 중 레일블루 사이트에서 정보를 가져와서 제공되는 기능들에 대해 관련 정책을 확인합니다.")
    async def railblue_accept_command(self, interaction: discord.Interaction) : 
        await interaction.response.defer()
        if not define.railblue_onoff : 
            embed = discord.Embed(
                title = "기능 비활성화됨", 
                description = "해당 기능이 비활성화되어 있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        embed = discord.Embed(
            title = "레일블루에서 제공되는 정보에 대한 정책",
            description = "마늘이 봇의 철도 관련 기능 중 열차정보를 포함한 일부 기능은 레일블루 사이트의 허가 하에 레일블루 사이트의 정보를 가져오는 방식으로 제공되고 있습니다.\n\n레일블루 사이트 링크: <https://rail.blue/>\n\n1. 레일블루 사이트를 통해 마늘봇에서 출력되는 정보는 __실시간 정보임이 보장되지 않습니다. 참고용으로만 사용하시기 바랍니다.__\n2. 제공되는 정보는 정보의 정확성, 신뢰성, 최신성을 보장하지 않습니다. 이 정보를 근거로 또는 이 정도에 관하여 철도 운영기관에 민원을 접수하지 마시기 바랍니다.\n3. 레일블루 사이트의 허가 하에 레일블루 사이트의 정보를 불러와서 제공되는 기능이므로, 레일블루 사이트의 사정에 따라 예고없이 정보 제공이 중단될 수 있습니다.\n  - 별도의 허가 없이 레일블루 사이트 측의 정보를 활용하여 다른 서비스를 이용하는 것은 금지됩니다. [자세히 알아보기](https://rail.blue/railroad/logis/bbs/view.aspx?id=faq&no=8&lang=ko)\n\n귀하께서는 이 동의를 거부할 권리가 있으나, 거부 시 관련 기능 이용이 제한될 수 있습니다. 이 사항에 동의하시는 경우 </철도 레일블루정책동의:1391677509111644200> 명령어를 사용하여 동의 의사를 표시할 수 있으며, 추후 동의를 철회하려는 경우 </철도 레일블루정책동의:1391677509111644200> 명령어를 사용하여 동의를 철회할 수 있습니다.",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)
        railblue_accept_ready.append(interaction.user.id)
        return

    @app_commands.command(name = "레일블루정책동의", description = "철도 관련 명령어 중 레일블루 사이트에서 정보를 가져와서 제공되는 기능들에 대해 관련 정책에 동의합니다.")
    @app_commands.describe(동의여부 = "정책 동의 여부")
    @app_commands.choices(동의여부 = [
        app_commands.Choice(name = "동의함", value = "True"),
        app_commands.Choice(name = "동의하지 않음", value = "False"),
    ])
    async def railblue_accept_command2(self, interaction: discord.Interaction, 동의여부: str) : 
        await interaction.response.defer()

        if not define.railblue_onoff : 
            embed = discord.Embed(
                title = "기능 비활성화됨", 
                description = "해당 기능이 비활성화되어 있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        status, until, reason = is_blocked(interaction.user)
        
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        if 동의여부 == "True" : 
            동의여부 = True
        else : 
            동의여부 = False
        if interaction.user.id not in railblue_accept_ready and 동의여부: 
            embed = discord.Embed(
                title = "오류",
                description = "정책에 동의하기 전 먼저 정책 내용을 확인해 주세요. </레일블루정책확인:1391677509111644200> 명령어를 사용해 주세요.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        await railblue_accept_update(interaction.user.id, 동의여부)
        embed = discord.Embed(
            title = "완료",
            description = "설정이 저장되었습니다.",
            color = int("a5f0ff", 16)
        )
        await interaction.followup.send(embed = embed)
        return
    
    @app_commands.command(name = "도착정보", description = "열차번호를 입력하고 열차에 대한 정보를 확인합니다.")
    @app_commands.choices(노선 = [
        app_commands.Choice(name = "수도권 1호선, 경춘선, 수인분당선, 경의중앙선, 경강선, 서해선", value = "Korail"),
        app_commands.Choice(name = "수도권 2호선", value = "Seoul_Line_2"),
        app_commands.Choice(name = "수도권 3호선", value = "Seoul_Line_3"),
        app_commands.Choice(name = "수도권 4호선", value = "Seoul_Line_4"),
        app_commands.Choice(name = "수도권 5~8호선", value = "SMRT"),
        app_commands.Choice(name = "수도권 9호선", value = "Metro9"),
        app_commands.Choice(name = "신분당선", value = "Sinbundang"),
        app_commands.Choice(name = "공항철도", value = "AREX"),
        app_commands.Choice(name = "GTX-A", value = "GTXA"),
        app_commands.Choice(name = "신림선", value = "SL"),
        app_commands.Choice(name = "우이신설선", value = "UI"),
        app_commands.Choice(name = "김포 골드라인", value = "GMP"),
        app_commands.Choice(name = "김포 골병라인", value = "GMP"),
        app_commands.Choice(name = "의정부 경전철", value = "ULRT"),
        app_commands.Choice(name = "용인 경전철", value = "EVER"),
        app_commands.Choice(name = "부산 1~4호선", value = "BTC"),
        app_commands.Choice(name = "부산김해경전철", value = "BGL"),
        app_commands.Choice(name = "동해선 광역전철", value = "Korail"),
        app_commands.Choice(name = "대구 1~3호선", value = "DTRO"),
        app_commands.Choice(name = "대경선", value = "Korail"),
        app_commands.Choice(name = "광주 1호선", value = "GWJ"),
        app_commands.Choice(name = "대전 1호선", value = "DJET"),
    ])
    @app_commands.describe(역명 = "역명", 노선 = "노선", 통과열차표시여부 = "통과 열차 표시 여부", 개인응답 = "개인응답 사용 여부")
    async def arrival_info_railblue(self, interaction: discord.Interaction, 역명: str, 노선: str, 통과열차표시여부: bool = False, 개인응답: bool = False) : 
        await interaction.response.defer(ephemeral=개인응답)

        status, until, reason = is_blocked(interaction.user)

        if not define.railblue_onoff : 
            embed = discord.Embed(
                title = "기능 비활성화됨", 
                description = "해당 기능이 비활성화되어 있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        accept = await railblue_accept_get(interaction.user.id)

        if not accept : 
            embed = discord.Embed(
                title = "오류",
                description = "레일블루에서 가져오는 정보에 대한 정책 동의 후 이용해 주세요. </레일블루정책확인:1391677509111644200> 명령어를 사용해 주세요.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if interaction.user.id in railblue_last_time : 
            time = datetime.datetime.now() - railblue_last_time[interaction.user.id]
            if time.seconds < 45 and interaction.user.id != developer : 
                embed = discord.Embed(
                    title = "오류",
                    description = f"레일블루 사이트 관련 명령어는 45초에 한 번만 사용할 수 있습니다. 시간: {45 - time.seconds}초 후에 다시 시도하세요.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
        
        if 통과열차표시여부 : 
            embed = discord.Embed(
                title = "오류",
                description = "통과 열차 표시 여부 활성화는 현재 지원되지 않습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        기준시각 = await today_to_text2()

        try : 
            train_list = await get_arrival_info_railblue(역명, 노선, 통과열차표시여부, interaction.user.id)
        except Exception as e:
            embed = discord.Embed(
                title = "오류",
                description = f"레일블루 사이트 관련 명령어 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                color = discord.Color.red()
            )
            print(e)
            await interaction.followup.send(embed = embed)
            return

        up_list = train_list[0]
        down_list = train_list[1]
        link = train_list[2]

        des = f"**__중요: 이 정보는 실시간 정보임이 보장되지 않습니다. 모든 정보는 참고용으로만 이용하시기 바랍니다.__**\n\n"

        des += f"정보 출처: [레일블루 전철도착정보]({link})\n\n"

        up_text = ""
        down_text = ""

        if len(up_list) >= 5: 
            for train in up_list[0:5]:
                up_text += f"- **{train['dest']}**: #{train['train']} {train['time']} 후 {train['status']} 예정\n"
        else : 
            for train in up_list:
                up_text += f"- **{train['dest']}**: #{train['train']} {train['time']} 후 {train['status']} 예정\n"
        
        if len(down_list) >= 5: 
            for train in down_list[0:5]:
                down_text += f"- **{train['dest']}**: #{train['train']} {train['time']} 후 {train['status']} 예정\n"
        else : 
            for train in down_list:
                down_text += f"- **{train['dest']}**: #{train['train']} {train['time']} 후 {train['status']} 예정\n"

        embed = discord.Embed(
            title = f"{역명} 도착 정보",
            description = des,
            color = int("a5f0ff", 16),
        )
        embed.add_field(name = "상행", value = up_text, inline = False)
        embed.add_field(name = "하행", value = down_text, inline = False)
        embed.add_field(name = "팁", value = "위 열차들의 운행 시각표를 조회하려면, `/철도 열차정보` 명령어를 사용해 보세요!", inline = False)
        embed.set_footer(text=f"정보 업데이트 시각: {기준시각}")
        await interaction.followup.send(embed = embed)
        return
    
    @app_commands.command(name = "열차정보", description = "열차번호를 입력하고 열차에 대한 정보를 확인합니다.")
    @app_commands.choices(머리글자 = [
        app_commands.Choice(name = "직접 입력", value = "직접 입력"),
        app_commands.Choice(name = "기차 (KTX, SRT, 무궁화, 새마을, ITX 등)", value = "기차"),
        app_commands.Choice(name = "수도권 1, 3, 4호선", value = "line1,3,4"),
        app_commands.Choice(name = "수도권 2호선", value = "line2"),
        app_commands.Choice(name = "수도권 5~8호선", value = "line5~8"),
        app_commands.Choice(name = "수도권 9호선 (일반)", value = "line9_allstop"),
        app_commands.Choice(name = "수도권 9호선 (급행)", value = "line9_express"),
        app_commands.Choice(name = "공항철도", value = "arex"),
        app_commands.Choice(name = "수인분당선, 경의중앙선, 경춘선, 경강선, 서해선", value = "korail_line"),
        app_commands.Choice(name = "신분당선", value = "신분당선"),
        app_commands.Choice(name = "우이신설선", value = "우이신설선"),
        app_commands.Choice(name = "김포 골드라인", value = "김포 골드라인"),
        app_commands.Choice(name = "김포 골병라인", value = "김포 골드라인"),
        app_commands.Choice(name = "의정부 경전철", value = "의정부 경전철"),
        app_commands.Choice(name = "용인 경전철", value = "용인 경전철"),
        app_commands.Choice(name = "신림선", value = "신림선"),
        app_commands.Choice(name = "GTX-A", value = "GTX-A"),
        app_commands.Choice(name = "부산 1~4호선", value = "부산 1~4호선"),
        app_commands.Choice(name = "부산김해경전철 (사상 방면)", value = "부산김해경전철 (사상 방면)"),
        app_commands.Choice(name = "부산김해경전철 (가야대 방면)", value = "부산김해경전철 (가야대 방면)"),
        app_commands.Choice(name = "동해선", value = "동해선"),
        app_commands.Choice(name = "대구 1~3호선", value = "대구 1~3호선"),
        app_commands.Choice(name = "대경선", value = "대경선"),
        app_commands.Choice(name = "대전 1호선", value = "대전 1호선"),
        app_commands.Choice(name = "광주 1호선", value = "광주 1호선"),
    ])
    @app_commands.describe(열차번호 = "열차 번호", 머리글자 = "열차 머리글자", 날짜 = "해당 열차의 날짜 (입력 형식: YYYYMMDD)", 개인응답 = "개인응답 사용 여부")
    async def train_info(self, interaction: discord.Interaction, 열차번호: str, 머리글자: str, 날짜: str = None, 개인응답: bool = False) : 
        await interaction.response.defer(ephemeral=개인응답)

        if not define.railblue_onoff : 
            embed = discord.Embed(
                title = "기능 비활성화됨", 
                description = "해당 기능이 비활성화되어 있습니다.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return

        status, until, reason = is_blocked(interaction.user)
        
        if status:
            msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
            await interaction.followup.send(msg)
            return
        
        accept = await railblue_accept_get(interaction.user.id)

        if not accept : 
            embed = discord.Embed(
                title = "오류",
                description = "레일블루에서 가져오는 정보에 대한 정책 동의 후 이용해 주세요. </레일블루정책확인:1391677509111644200> 명령어를 사용해 주세요.",
                color = discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        
        if interaction.user.id in railblue_last_time : 
            time = datetime.datetime.now() - railblue_last_time[interaction.user.id]
            if time.seconds < 45 and interaction.user.id != developer : 
                embed = discord.Embed(
                    title = "오류",
                    description = f"레일블루 사이트 관련 명령어는 45초에 한 번만 사용할 수 있습니다. 시간: {45 - time.seconds}초 후에 다시 시도하세요.",
                    color = discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return
        
        열차번호 = await train_number_line(열차번호, 머리글자)
        
        today_text = await today_to_text()
        
        if 날짜 is None : 
            날짜 = today_text

        # try : 
        if True : 
            기준시각 = await today_to_text2()
            위치, 지연, 지연업데이트시각 = await get_train_info_railblue(열차번호, 날짜, interaction.user.id)
            timetable, delay = await get_train_timetable_railblue(열차번호, 날짜, interaction.user.id)
            try : 
                if delay is not None : 
                    timetable_delay_input_type = delay[1]
                    timetable_delay_update_before = delay[3]
                    timetable_delay_update = datetime.datetime.today()
                    timetable_delay_update = timetable_delay_update.replace(
                        hour=timetable_delay_update_before[0],
                        minute=timetable_delay_update_before[1],
                        second=timetable_delay_update_before[2],
                        microsecond=0 # 마이크로초는 0으로 초기화
                    )
                    timetable_delay_time = [delay[2], delay[4]]
                if 지연업데이트시각 is not None : 
                    default_delay_input_type = 지연업데이트시각[0]
                    default_delay_update = datetime.datetime.now() - timedelta(seconds=지연업데이트시각[1])
                    if default_delay_update >= timetable_delay_update + timedelta(seconds = 20) : 
                        지연 = 지연
                        ago = datetime.datetime.now() - default_delay_update
                        total_minutes = ago.total_seconds() // 60
                        if total_minutes < 60 : 
                            정보출처 = f"레일블루 - {default_delay_input_type} (약 {str(total_minutes)}분 전 업데이트됨)"
                        else : 
                            정보출처 = f"레일블루 - {default_delay_input_type} (약 {str(total_minutes // 60)}시간 전 업데이트됨)"
                    else : 
                        if timetable_delay_time[1][0] == 0 and timetable_delay_time[1][1] == 0 and timetable_delay_time[1][2] == 0 : 
                            지연 = f"정시 운행 중"
                        elif timetable_delay_time[0] : 
                            지연 = f"{str(delay[4][0] * 60 + delay[4][1])}분 {str(delay[4][2])}초 지연 운행 중"
                        else : 
                            지연 = f"{str(delay[4][0] * 60 + delay[4][1])}분 {str(delay[4][2])}초 조기 운행 중"
                        
                        ago = datetime.datetime.now() - timetable_delay_update
                        total_minutes = ago.total_seconds() // 60
                        if total_minutes < 60 : 
                            정보출처 = f"레일블루 - {timetable_delay_input_type} (약 {str(int(total_minutes))}분 전 업데이트됨)"
                        else : 
                            정보출처 = f"레일블루 - {timetable_delay_input_type} (약 {str(int(total_minutes // 60))}시간 전 업데이트됨)"
                elif delay is not None : 
                    if timetable_delay_time[1][0] == 0 and timetable_delay_time[1][1] == 0 and timetable_delay_time[1][2] == 0 : 
                        지연 = f"정시 운행 중"
                    elif timetable_delay_time[0] : 
                        지연 = f"{str(delay[4][0] * 60 + delay[4][1])}분 {str(delay[4][2])}초 지연 운행 중"
                    else : 
                        지연 = f"{str(delay[4][0] * 60 + delay[4][1])}분 {str(delay[4][2])}초 조기 운행 중"
                    
                    ago = datetime.datetime.now() - timetable_delay_update
                    total_minutes = ago.total_seconds() // 60
                    if total_minutes < 60 : 
                        정보출처 = f"레일블루 - {timetable_delay_input_type} (약 {str(int(total_minutes))}분 전 업데이트됨)"
                    else : 
                        정보출처 = f"레일블루 - {timetable_delay_input_type} (약 {str(int(total_minutes // 60))}시간 전 업데이트됨)"
                else : 
                    정보출처 = "레일블루 - *(알 수 없음)*"
            except Exception:
                embed2 = discord.Embed(
                    title = f"열차 #{열차번호} 정보",
                    description = f"오류: 새로 업데이트된 열차 정보 표시 방식대로 열차 정보를 표시하는 도중 문제가 발생하여 레거시 방식으로 표시합니다.\n\n**__중요: 이 정보는 실시간 정보임이 보장되지 않습니다. 모든 정보는 참고용으로만 이용하시기 바랍니다.__**\n\n정보 출처: [레일블루 들머리 운행정보](https://rail.blue/railroad/logis/Default.aspx?company=&train={열차번호}&date={날짜}#!)\n\n- 위치: {위치}\n- 지연: {지연}",
                    color = discord.Color.yellow(),
                )
                embed2.set_footer(text=f"정보 업데이트 시각: {기준시각}")
                pages = generate_pages(열차번호, timetable)
                view = Paginator(pages, embed2)
                await interaction.followup.send(embeds=[pages[0], embed2], view=view)
                return
            embed2 = discord.Embed(
                title = f"열차 #{열차번호} 정보",
                description = f"**__중요: 이 정보는 실시간 정보임이 보장되지 않습니다. 모든 정보는 참고용으로만 이용하시기 바랍니다.__**\n\n정보 출처: [레일블루 들머리 운행정보](https://rail.blue/railroad/logis/Default.aspx?company=&train={열차번호}&date={날짜}#!), [레일블루 열차 시각표 정보](https://rail.blue/railroad/logis/scheduleinfo.aspx?date={날짜}&train={열차번호}#!)\n\n- 위치: {위치}\n- 지연: {지연}\n- 정보 출처: {정보출처}",
                color = int("a5f0ff", 16),
            )
            embed2.set_footer(text=f"정보 업데이트 시각: {기준시각}")
            pages = generate_pages(열차번호, timetable)
            view = Paginator(pages, embed2)
            await interaction.followup.send(embeds=[pages[0], embed2], view=view)
        '''except Exception as e : 
            global error
            print(f"오류 #{error}: {e}")
            embed = discord.Embed(
                title="오류",
                description=f"오류 #{error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            error += 1
            return'''

ITEMS_PER_PAGE = 5

def generate_pages(train, data):
    pages = []

    page_num = 1

    # 데이터 쪼개기
    for j in range(0, len(data), ITEMS_PER_PAGE):
        chunk = data[j:j+ITEMS_PER_PAGE]

        embed = discord.Embed(
            title=f"열차 #{train} 시각표 정보",
            description=f"**[주의!]** 이 정보는 시각표를 기준으로 한 정보입니다. 실제 도착 시각과 차이가 있을 수 있으며 가급적 아래의 지연 시간 정보를 함께 참고하시기 바랍니다.",
            color=int("a5f0ff", 16)
        )
        for i in chunk:
            역명 = i["역명"]
            정차유형 = i["정차유형"]
            예정도착시간 = i['도착예정']
            예정출발시간 = i['출발예정']
            if i["도착시각"] != '' : 
                실제도착시간 = i['도착시각']
                도착지연 = i["도착지연"]
                if 도착지연 == "00:00:00" : 
                    도착지연 = "0"
                elif "+" in 도착지연 : 
                    temp = 도착지연[1:].split(":")
                    for j in range(len(temp)) : 
                        temp[j] = int(temp[j])
                    도착지연 = "+" + str(temp[0] * 60 + temp[1])
                elif "-" in 도착지연 : 
                    temp = 도착지연[1:].split(":")
                    for j in range(len(temp)) : 
                        temp[j] = int(temp[j])
                    도착지연 = "-" + str(temp[0] * 60 + temp[1])
            else : 
                실제도착시간 = None
                도착지연 = None
            if i["출발시각"] != '' : 
                실제출발시간 = i['출발시각']
                출발지연 = i["출발지연"]
                if 출발지연 == "00:00:00" : 
                    출발지연 = "0"
                elif "+" in 출발지연 : 
                    temp = 출발지연[1:].split(":")
                    for j in range(len(temp)) : 
                        temp[j] = int(temp[j])
                    출발지연 = "+" + str(temp[0] * 60 + temp[1])
                elif "-" in 출발지연 : 
                    temp = 출발지연[1:].split(":")
                    for j in range(len(temp)) : 
                        temp[j] = int(temp[j])
                    출발지연 = "-" + str(temp[0] * 60 + temp[1])
            else : 
                실제출발시간 = None
                출발지연 = None

            title = f"{역명} ({정차유형})"
            if 정차유형 == "정차" : 
                if 실제도착시간 is None : 
                    des = f"- 도착 시각: {예정도착시간}"
                else : 
                    des = f"- 도착 시각: ~~{예정도착시간}~~ {실제도착시간} ({도착지연})"
                if 실제출발시간 is None : 
                    des += f"\n- 출발 시각: {예정출발시간}"
                else : 
                    des += f"\n- 출발 시각: ~~{예정출발시간}~~ {실제출발시간} ({출발지연})"
            elif 정차유형 == "통과" : 
                if 실제출발시간 is None : 
                    des = f"- 통과 시각: {예정출발시간}"
                else : 
                    des = f"- 통과 시각: ~~{예정출발시간}~~ {실제출발시간} ({출발지연})"
            elif 정차유형 == "출발" : 
                if 실제출발시간 is None : 
                    des = f"- 출발 시각: {예정출발시간}"
                else : 
                    des = f"- 출발 시각: ~~{예정출발시간}~~ {실제출발시간} ({출발지연})"
            elif 정차유형 == "종착" : 
                if 실제도착시간 is None : 
                    des = f"- 도착 시각: {예정도착시간}"
                else : 
                    des = f"- 도착 시각: ~~{예정도착시간}~~ {실제도착시간} ({도착지연})"
            else : 
                if 실제도착시간 is None : 
                    des = f"- 도착 시각: {예정도착시간}"
                else : 
                    des = f"- 도착 시각: ~~{예정도착시간}~~ {실제도착시간} ({도착지연})"
                if 실제출발시간 is None : 
                    des += f"\n- 출발 시각: {예정출발시간}"
                else : 
                    des += f"\n- 출발 시각: ~~{예정출발시간}~~ {실제출발시간} ({출발지연})"
            embed.add_field(name=title, value=des, inline=False)
        
        page_count = len(data)//ITEMS_PER_PAGE
        if len(data) % ITEMS_PER_PAGE != 0 : 
            page_count += 1

        embed.set_footer(text=f"페이지 {page_num} / {page_count}")

        pages.append(embed)
        page_num += 1

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

async def get_train_timetable_railblue(train, date, user_id) : 
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    railblue_last_time[user_id] = datetime.datetime.now()
    driver.get(f"https://rail.blue/railroad/logis/magiainfo.aspx?train={train}&date={date}#!")
    await asyncio.sleep(2.5)

    # 1. 전체 테이블 찾기
    table = driver.find_element(By.ID, "tblResult")

    # 2. 데이터 행 가져오기 (헤더 제외)
    rows = table.find_elements(By.CSS_SELECTOR, "tr.trResult_Time_Magia_H")

    data_list = []

    first_station = True
    current = 1
    row_cnt = len(rows) // 2

    # 2줄씩 묶어서 처리 (i: 윗줄 / i+1: 아랫줄)
    for i in range(0, len(rows), 2):
        top_row = rows[i]       # 윗줄 (도착 정보 포함)
        bottom_row = rows[i+1]  # 아랫줄 (출발 정보 포함)
        
        top_tds = top_row.find_elements(By.TAG_NAME, "td")
        bottom_tds = bottom_row.find_elements(By.TAG_NAME, "td")

        # --- [데이터 추출 및 공백 제거] ---
        
        # 1. 역명 (Top Row -> class="station_text_d")
        try:
            station_name = top_row.find_element(By.CSS_SELECTOR, ".station_text_d").text.strip()
        except:
            station_name = ""

        # 2. 도착예정 (Top Row -> index 1)
        # 값이 없으면 "&nbsp;" -> .text시 " " -> strip() 후 "" 가 됨
        arrival_sched = top_tds[1].text.strip()

        # 3. 출발예정 (Bottom Row -> index 0)
        # 주의: 아랫줄은 앞쪽 셀(역명 등)이 rowspan으로 밀려서 0번이 출발예정임
        dept_sched = bottom_tds[0].text.strip()

        # 4. 입력구분 (Top Row -> index 2)
        input_type = top_tds[2].text.strip()
        input_type = input_type.replace("\n", ": ")
        if input_type == "수기" : 
            input_type = "수동: 수기"

        # 5. 도착시각 (Top Row -> index 3)
        arrival_real = top_tds[3].text.strip()

        # 6. 출발시각 (Bottom Row -> index 1)
        # 아랫줄 0번이 출발예정이므로, 1번이 출발시각(실제)
        dept_real = bottom_tds[1].text.strip()

        # 7. 도착지연 (Top Row -> index 4)
        arrival_delay = top_tds[4].text.strip()

        # 8. 출발지연 (Bottom Row -> index 2)
        dept_delay = bottom_tds[2].text.strip()

        if first_station : 
            data_list.append({
                "역명": station_name,
                "도착예정": arrival_sched,
                "출발예정": dept_sched,
                "입력구분": input_type,
                "도착시각": arrival_real,
                "출발시각": dept_real,
                "도착지연": arrival_delay,
                "출발지연": dept_delay,
                "정차유형": "출발",
            })
            first_station = False
        else : 
            if current == row_cnt : 
                data_list.append({
                    "역명": station_name,
                    "도착예정": arrival_sched,
                    "출발예정": dept_sched,
                    "입력구분": input_type,
                    "도착시각": arrival_real,
                    "출발시각": dept_real,
                    "도착지연": arrival_delay,
                    "출발지연": dept_delay,
                    "정차유형": "종착",
                })
            elif arrival_sched == "" or arrival_sched is None or arrival_sched == " " : 
                data_list.append({
                    "역명": station_name,
                    "도착예정": arrival_sched,
                    "출발예정": dept_sched,
                    "입력구분": input_type,
                    "도착시각": arrival_real,
                    "출발시각": dept_real,
                    "도착지연": arrival_delay,
                    "출발지연": dept_delay,
                    "정차유형": "통과",
                })
            else : 
                data_list.append({
                    "역명": station_name,
                    "도착예정": arrival_sched,
                    "출발예정": dept_sched,
                    "입력구분": input_type,
                    "도착시각": arrival_real,
                    "출발시각": dept_real,
                    "도착지연": arrival_delay,
                    "출발지연": dept_delay,
                    "정차유형": "정차",
                })

        current += 1
    
    delay = None
    
    for i in reversed(data_list) : 
        # delay = [지연정보존재여부, 입력방식, 지연인지 조착인지(지연이 True), 지연시분[시, 분, 초], 입력시각[시, 분, 초]]
        if i["출발지연"] != "" : 
            if i["출발지연"] == "00:00:00" : 
                temp = i["출발시각"].split(":")
                for j in range(len(temp)) : 
                    temp[j] = int(temp[j])
                delay = [True, i["입력구분"], True, temp, [0, 0, 0]]
                break
            elif "+" in i["출발지연"] : 
                temp = i["출발시각"].split(":")
                for j in range(len(temp)) : 
                    temp[j] = int(temp[j])
                temp2 = i["출발지연"][1:].split(":")
                for j in range(len(temp2)) : 
                    temp2[j] = int(temp2[j])
                delay = [True, i["입력구분"], True, temp, temp2]
                break
            elif "-" in i["출발지연"] : 
                temp = i["출발시각"].split(":")
                for j in range(len(temp)) : 
                    temp[j] = int(temp[j])
                temp2 = i["출발지연"][1:].split(":")
                for j in range(len(temp2)) : 
                    temp2[j] = int(temp2[j])
                delay = [True, i["입력구분"], False, temp, temp2]
                break
        elif i["도착지연"] != "" : 
            if i["도착지연"] == "00:00:00" : 
                temp = i["도착시각"].split(":")
                for j in range(len(temp)) : 
                    temp[j] = int(temp[j])
                delay = [True, i["입력구분"], True, temp, [0, 0, 0]]
                break
            elif "+" in i["도착지연"] : 
                temp = i["도착시각"].split(":")
                for j in range(len(temp)) : 
                    temp[j] = int(temp[j])
                temp2 = i["도착지연"][1:].split(":")
                for j in range(len(temp2)) : 
                    temp2[j] = int(temp2[j])
                delay = [True, i["입력구분"], True, temp, temp2]
                break
            elif "-" in i["도착지연"] : 
                temp = i["도착시각"].split(":")
                for j in range(len(temp)) : 
                    temp[j] = int(temp[j])
                temp2 = i["도착지연"][1:].split(":")
                for j in range(len(temp2)) : 
                    temp2[j] = int(temp2[j])
                delay = [True, i["입력구분"], False, temp, temp2]
                break
    
    return data_list, delay   

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

async def get_train_info_railblue(train, date, user_id):
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    railblue_last_time[user_id] = datetime.datetime.now()
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
    
    default_page_delay = driver.find_element(by = By.ID, value = "spDelayUpdated")
    default_page_delay = default_page_delay.text
    if "수동으로" in default_page_delay : 
        if "방금" in default_page_delay : 
            default_page_delay = ["수동", 20]
        else : 
            pattern = r'(\d+)(분|시간)'
            match = re.search(pattern, default_page_delay)
            amount = match.group(1)
            unit = match.group(2)

            amount = int(amount)

            if unit == '분':
                seconds = amount * 60
            elif unit == '시간':
                seconds = amount * 60 * 60
            
            default_page_delay = ["수동: 직접 입력", seconds]
    else : 
        default_page_delay = None            
    
    driver.quit()
    
    return loc_msg, delay_msg, default_page_delay

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

async def get_seoul_route(출발, 도착, 옵션, 시각):
    url = f"https://apis.data.go.kr/B553766/path/getShtrmPath?serviceKey={seoul_subway_find_route_api}&dataType=JSON&dptreStnNm={출발}&arvlStnNm={도착}&searchDt={시각}&searchType={옵션}&schInclYn=Y"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        
        return data  # Returning JSON response for further processing
    
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

async def lookup_seoul_route(출발, 도착, 옵션, 시각):
    json_data = await get_seoul_route(출발, 도착, 옵션, 시각)

    # print(json_data) # 디버깅용

    total_time = json_data["body"]["totalreqHr"] # 총 소요시간 (초)
    transfer_time = json_data["body"]["trsitNmtm"] # 환승 횟수

    json_paths = json_data["body"]["paths"]

    paths = json_data.get("body", {}).get("paths", [])
    if not paths:
        paths_result = []
    else : 
        paths_result = []
        
        for train_no, group in groupby(paths, key=lambda x: x["trainno"]):
            group_list = list(group)
            
            first_segment = group_list[0] # 이 열차의 첫 구간
            last_segment = group_list[-1] # 이 열차의 마지막 구간

            if first_segment["dptreStn"]["stnNm"] != last_segment["arvlStn"]["stnNm"] : 
                segment_duration = sum(item["reqHr"] + item["wtngHr"] for item in group_list)
            else : 
                segment_duration = first_segment["reqHr"]
            
            paths_result.append({
                "열차번호": train_no,
                "행선지": first_segment["tmnlStnNm"],
                "노선명": first_segment["dptreStn"]["lineNm"],
                "출발역": first_segment["dptreStn"]["stnNm"],
                "도착역": last_segment["arvlStn"]["stnNm"],
                "출발시각": first_segment["trainDptreTm"],
                "도착시각": last_segment["trainArvlTm"],
                "소요시간": segment_duration,
                "대기시간": first_segment["wtngHr"]
            })
    
    # print(paths_result) # 디버깅용
    
    text = ""
    num = 1

    wait_time = None
    transfer_walk_time = None

    arrive_time = None

    for i in range(len(paths_result)) : 
        current_path = paths_result[i]
        if i > 0 : 
            previous_path = paths_result[i-1]
        if not (i+1 == len(paths_result)) : 
            next_path = paths_result[i+1]

        current_path["소요+대기시간"] = await format_seconds(current_path["소요시간"] + current_path["대기시간"])
        
        current_path["소요시간"] = await format_seconds(current_path["소요시간"])
        current_path["대기시간"] = await format_seconds(current_path["대기시간"])
        
        if current_path["출발역"] == current_path["도착역"] : 
            text += f"**{num}. {arrive_time} - {current_path["출발역"]}역 도착 후 {next_path["노선명"]} 승강장으로 이동**\n- 환승 도보 소요 시간: {current_path["소요시간"]}\n- 환승 시간: {current_path["소요+대기시간"]}\n\n"
        else : 
            text += f"**{num}. {current_path["출발시각"]} - {current_path["노선명"]} {current_path["출발역"]} → {current_path["도착역"]} 이동**\n- 노선/행선지: {current_path["노선명"]} {current_path["행선지"]}행\n- 소요시간: {current_path["소요시간"]}\n- 열차번호: #{current_path["열차번호"]}\n\n"
            arrive_time = current_path["도착시각"]
            
        num += 1
    
    text += f"**{num}. {arrive_time} - {paths_result[len(paths_result) - 1]["도착역"]} 도착**"

    print(text) # 디버깅용

    total_time = await format_seconds(total_time)

    return {
        "transfer_time": transfer_time,
        "total_time": total_time,
        "path": text,
    }

async def format_seconds(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours == 0 : 
        return f"{minutes}분 {seconds}초"
    else : 
        return f"{hours}시간 {minutes}분 {seconds}초"


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

async def train_number_line(train_num, line) : 
    if line == "직접 입력" : return train_num
    elif line == "기차" : return train_num
    elif line == "line1,3,4" : return "K" + train_num
    elif line == "line2" : return "S" + train_num
    elif line == "line5~8" : return "SMRT" + train_num
    elif line == "line9_allstop" : return "SNC" + train_num
    elif line == "line9_express" : return "SNE" + train_num
    elif line == "korail_line" : return "K" + train_num
    elif line == "arex" : return "A" + train_num
    elif line == "신분당선" : return "DX" + train_num
    elif line == "우이신설선" : return "UI" + train_num
    elif line == "김포 골드라인" : return "GMP" + train_num
    elif line == "의정부 경전철" : return "ULRT" + train_num
    elif line == "용인 경전철" : return "EVER" + train_num
    elif line == "신림선" : return "SL" + train_num
    elif line == "GTX" : return "X" + train_num
    elif line == "부산 1~4호선" : return "BTC" + train_num
    elif line == "부산김해경전철 (사상 방면)" : return "BGLU" + train_num
    elif line == "부산김해경전철 (가야대 방면)" : return "BGLD" + train_num
    elif line == "동해선" : return "K" + train_num
    elif line == "대구 1~3호선" : return "DTRO" + train_num
    elif line == "대경선" : return "K" + train_num
    elif line == "대전 1호선" : return "DJET" + train_num
    elif line == "광주 1호선" : return "GWJ" + train_num

async def encode_railblue_station(station_name: str) -> str:
    # 1. 한글 -> UTF-8 바이트 -> Base64 문자열
    standard_b64 = base64.b64encode(station_name.encode("utf-8")).decode("ascii")
    
    # 2. 레일블루 전용 치환 테이블
    # + -> _
    # / -> -
    # = -> (제거)
    table = str.maketrans({
        '+': '_',
        '/': '-',
        '=': None
    })
    
    return standard_b64.translate(table)

async def parse_arrival_info_railblue(arrival_info): 
    trains = []
    # 1. 'tdTrainNo' 클래스를 포함하는 모든 td 요소를 찾습니다.
    # CSS 선택자 [class*='...']는 해당 문자열이 포함만 되어도 찾습니다.
    train_cells = arrival_info.find_elements(By.CSS_SELECTOR, "td[class*='tdTrainNo']")

    for cell in train_cells:
        try:
            # 부모 tr로 올라가서 해당 행의 전체 정보를 가져옵니다.
            row = cell.find_element(By.XPATH, "./..")
            
            # 열차 번호 추출 (a 태그의 href 활용)
            link = cell.find_element(By.TAG_NAME, "a")
            href = link.get_attribute("href")
            train_no = href.split("train=")[1].split("&")[0]

            # 목적지 (textContent를 사용해 숨겨진 '급행' 텍스트까지 확보)
            dest_elem = row.find_element(By.CLASS_NAME, "spMetroTrainDestination")
            dest = dest_elem.get_attribute("textContent").strip().replace('\n', ' ')

            # 상태 (도착, 출발, 통과 등)
            status_elem = row.find_element(By.CLASS_NAME, "spMAStatus")
            status = status_elem.get_attribute("textContent").strip()

            # 시간 (지연 또는 도착 예정 시간)
            time_elem = row.find_element(By.CSS_SELECTOR, "[class*='spMetroArriveDelay']")
            time = time_elem.get_attribute("textContent").strip()

            if "특별급행" in dest:
                dest = dest.replace("특별급행", "특급")
            
            # 2. '급행'이나 '특급'이라는 글자가 아예 없으면 뒤에 '행'을 붙임
            # (이미 '인천행'처럼 되어 있을 수도 있으니 '행'이 없을 때만 붙이는 로직 추천)
            elif "급행" not in dest and "특급" not in dest and "내선순환" not in dest and "외선순환" not in dest:
                if not dest.endswith("행"):
                    dest += "행"

            trains.append({
                "train": train_no,
                "dest": dest,
                "status": status,
                "time": time
            })
        except Exception:
            continue
            
    return trains

async def get_arrival_info_railblue(station_name, line, pass_train: bool, user_id) : 
    station_name_base64 = await encode_railblue_station(station_name)
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    railblue_last_time[user_id] = datetime.datetime.now()
    link = f"https://rail.blue/railroad/logis/metroarriveinfo.aspx?q={station_name_base64}&c={line}&base=1#!"
    driver.get(link)
    await asyncio.sleep(2.5)
    arrival_info_up = driver.find_element(by = By.ID, value = "tblTrainListU")
    arrival_info_down = driver.find_element(by = By.ID, value = "tblTrainListD")
    arrival_info_up = await parse_arrival_info_railblue(arrival_info_up)
    arrival_info_down = await parse_arrival_info_railblue(arrival_info_down)
    arrival_info = [arrival_info_up, arrival_info_down, link]
    driver.quit()
    return arrival_info