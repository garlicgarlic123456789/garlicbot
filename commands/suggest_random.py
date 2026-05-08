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
    "성공은 최종적인 것이 아니며, 실패는 치명적인 것이 아니다. 중요한 것은 계속하려는 용기이다.",
    "인생은 용감한 모험이거나 아무것도 아니다.",
    "미래는 현재 우리가 무엇을 하는가에 달려 있다.",
    "꿈을 꾸는 자만이 그 꿈을 이룰 수 있다.",
    "가장 큰 위험은 위험 없는 삶이다.",
    "행복은 습관이다. 그것을 연습하라.",
    "모든 어려움 뒤에는 기회가 숨어 있다.",
    "당신이 할 수 있다고 믿든, 할 수 없다고 믿든, 당신이 옳다.",
    "흔들리지 않고 피는 꽃이 어디 있으랴",
]
exam_handwriting_texts = [ # 수능/모의고사 필적확인란 문구
    "누구의 삶인들 향기롭지 않으랴",
    "가장 빛나는 별은 지금 너에게로",
    "삶이란 가꿀수록 아름다운 것이라고",
    "가장 넓은 길은 언제나 내 마음속에",
    "꿈을 지닌 넌 누구보다 밝게 빛나",
    "따스한 강물에 흔들리는 노을",
    "나의 꿈은 맑은 바람이 되어서",
    "너의 값진 말들로 희망을 노래하라",
    "넓은 하늘로의 비상을 꿈꾸며","흙에서 자란 내 마음 파란 하늘빛",
    "넓은 벌 동쪽 끝으로 옛이야기",
    "손금에 맑은 강물이 흐르고",
    "이 많은 별빛이 내린 언덕 위에",
    "맑은 강물처럼 조용하고 은근하며",
    "날마다 새로우며, 깊어지며, 넓어진다",
    "진실로 내가 그대를 사랑하는 까닭은",
    "맑은 햇빛으로 반짝반짝 물들으며",
    "꽃초롱 불 밝히듯 눈을 밝힐까",
    "햇살도 둥글둥글하게 뭉치는 맑은 날",
    "넓음과 깊음을 가슴에 채우며",
    "흙에서 자란 내 마음 파아란 하늘빛",
    "큰 바다 넓은 하늘을 우리는 가졌노라",
    "그대만큼 사랑스러운 사람을 본 일이 없다",
    "너무 맑고 초롱한 그 중 하나 별이여",
    "많고 많은 사람 중에 그대 한 사람",
    "넓은 하늘로의 비상을 꿈꾸며",
    "나의 꿈은 맑은 바람이 되어서",
    "가장 넓은 길은 언제나 내 마음속에",
    "저 넓은 세상에서 큰 꿈을 펼쳐라",
    "초록 물결이 톡톡 튀는 젊음처럼",
    "하늘을 우러러 한 점 부끄럼이 없기를",
    "산에는 꽃 피네 꽃이 피네 갈 봄 여름 없이",
    "산은 시들지 않는 영원한 품 속이다",
    "파랑새는 항상 자기 마음속에 있다",
    "세상의 중심엔 내 꿈이 있다",
    "언제나 점잖은 편 말이 없구나",
    "맑은 기운 서린 푸른 산봉우리",
    "사뿐히 즈려 밟고 가시옵소서",
    "해맑은 밤 바람이 이마에 내리는 여울가 모래밭",
    "그 곳이 차마 꿈엔들 잊힐리야",
    "붉은 파밭의 푸른 새싹을 보아라",
    "그대 가슴 속에 꿈이 없다면 슬퍼하라",
    "여유를 가지고 마음을 열어라",
    "태양이 빛나면 먼지도 빛난다",
    "오늘 아침엔 장미꽃이 유난히 붉었습니다",
    "빈 대에 황촉불이 말없이 녹는 밤에",
    "진정 겸손해야만 삶이 빛날 수 있음을 알아야 한다",
    "모든 일에 정성을, 주어진 일에 최선을",
    "햇빛도 그늘이 있어야 맑고 눈이 부시다",
    "끈기는 자기가 가지고 있는 최고의 무기이다",
    "지금 있는 이곳에서 너의 최선을 다하라!",
    "엷은 졸음에 겨운 늙으신 아버지가",
    "갈망하는 삶에 샘물은 찾아온다",
    "격의 없이 터놓은 관계여도 기본 예는 갖춤이 옳거니",
    "기슭에는 채송화가 무더기로 피어서",
    "인류의 위대한 사상은 때묻지 않은 자연의 숲속에서 움텄다",
    "흔들리지 않고 피는 꽃이 어디 있으랴",
    "자연은 우리에게 많은 것을 아낌없이 베풀어주고 있다",
    "꽃피는 나무는 자기 몸으로 꽃피는 나무이다",
    "젊을 때 배움을 소홀히 하면 미래가 없다",
    "실어 나르지 않는 깨끗한 마음으로",
    "연잎은 진흙에서 나왔으나 더러움에 물들지 않는다",
    "불빛인 듯 덮어주고는",
    "그 맑은 눈빛으로 나를 씻어",
    "역경보다 나은 교육은 없다",
    "서로 배려하는 마음으로 친구와 우정 쌓기",
    "사람은 나이로 늙는 것이 아니라 기분으로 늙는다",
    "장닭 꼬리 날리는 하얀 바람 봄길",
    "세상이 조금씩 더 밝아지게 하소서",
    "푸른 노래 푸른 울음 울어 예으리",
    "포도빛 향기에 취해만 가는데",
    "별이 총총한 맑은 새암을 들여다본다",
    "푸른 하늘을 향하는 희망처럼",
    "얼음장을 뚫고 바다에 당도한",
    "일상에 얽매이지 않고 자유로운 삶을 살다",
    "생명의 꽃을 피우는 미나리 빛깔의 봄",
    "산 넘어 또 오를 산이 없다면 삶은 얼마나 밋밋할까",
    "맑은 이슬은 달빛 아래 흰 구슬을 이루고",
    "희망의 빛을 품고 꿈을 향해 나아가는",
    "꿈은 힘든 생활을 헤쳐나가는 힘",
    "세월이 흘러도 어머니의 마음은 늙지 않습니다",
    "햇살과 바람은 한쪽 편만 들지 않아",
    "진정 오늘밖엔 없는 것처럼 시간을 아껴 쓰고",
    "시냇물에 잠긴 하얀 조각돌처럼",
    "꽃은 젖어도 향기는 젖지 않는다",
    "언젠가 먼 훗날에 저 넓고 거칠은 세상 끝 바다로 갈거라고",
    "많이 사랑하고 더 나중까지 지켜주는 이 됩시다",
    "풀섶 이슬에 함초롬 휘적시던 곳",
    "밝고 맑게 살아가는 희망의 사람이 되게",
    "장미꽃 한 다발보다 더 행복한 하루",
    "하루가 힘들어도 미래를 위해 꿈을 꾼다",
    "삶의 울타리 안에 평안함이 가득하다는 것이다",
    "썰물이 훑고 간 갯바닥의 나문재들은 더욱 붉었다",
    "달은 하늘 깊은 곳에 이르러 새벽을 달리는데",
    "밝고 환한 빛으로 들꽃처럼 웃었지요",
    "봄비가 초록잎에 생명을 불어 넣듯이",
    "햇빛이 선명하게 나뭇잎을 핥고 있었다",
    "꽃씨들은 흙을 뚫고 얼음을 뚫고",
    "희망의 샘 하나 출렁이고 있을 것만 같았다",
    "신선한 물고기가 튀는 빛의 꼬리를 물고 쏟아진다",
    "연꽃 같은 팔꿈치로 가이없는 바다를 밟고",
    "푸르른 보리밭길 엷은 하늘에",
    "달빛이 밀물처럼 밀려왔구나",
    "광활한 들녁에 씨알 하나",
    "청노루 맑은 눈에 도는 구름",
    "거친 돌이 다듬어져 조각이 되듯",
    "별을 보고 걸어가는 사람이 되라",
    "내려갈 때 보았네 올라갈 때 못 본 그 꽃",
    "눈 맑은 사람아 마음 맑은 사람아",
    "눈꽃의 화음에 귀를 적신다",
    "나중 난 뿔이 우뚝하다",
    "티 없이 맑은 영원의 하늘",
    "깊고 넓은 감정의 바다가 있다",
    "들판을 가르는 푸른 바람처럼",
    "깊은 숲 속에서 나오니 유월의 햇빛이 밝다",
    "제 삶의 길을 묵묵히 가는 마음 하나 곱게 간직하고 싶다",
    "꽃이 진다고 그대를 잊은 적 없다",
    "뭉툭하게 닳은 연필심으로 만들어 가는 내 꿈",
    "제 몫의 삶 지켜가는 청단풍 한 그루",
    "단풍 곱게 물든 햇살 맑은 가을날",
    "울림이 있어야 삶이 신선하고 활기차다",
    "마음속에 찰랑이는 맑고 고운 말 한마디",
    "너에게 잊혀지지 않는 하나의 눈짓",
    "눈부신 초록의 노래처럼 향기처럼",
    "등불을 밝혀 어둠을 조금 내몰고",
    "그대, 참 괜찮은 사람. 함께라 더 좋은 사람",
    "희망은 삶을 견고하게 지탱해주는 굵은 동아줄이다.",
    "하염없는 빛 하염없는 기쁨",
    "한 알의 작은 꽃씨 속에 모여 앉은 가을",
    "눈 맑고 가슴 맑은 보고 싶은 사람아",
    "넌 머지않아 예쁜 꽃이 될 테니까",
    "내 안의 두 눈과 마음 문을 활짝 열고",
    "맑은 풍금 소리 미루나무 잎이 되다",
    "바람은 자도 마음은 자지 않는다",
    "아름다운 네 모습 잃지 않았으면",
    "행복하다 말하면 맑아지는 마음",
    "달이 밝고 구름이 흐르고 하늘이 펼치고",
    "당당하게, 겸손 잃지 않은 채 피어나는 꽃",
    "아, 생각만 해도 참 좋은 당신",
    "어제도 가고 오늘도 갈 나의 길 새로운 길",
    "하늘빛을 닮은 그 들판 곁에 서서",
    "세상을 지켜 낸 태양보다 값진 오늘",
    "너 앉은 그 자리가 바로 희망 꽃자리",
    "그대 맑은 눈을 들어 나를 보느니",
    "밝고 환한 빛으로 들꽃처럼 환히 웃는 너",
    "그대가 가는 길이 아름다운 꽃길이다",
    "두꺼운 땅껍질 뚫고 나오는 아주 작은 힘",
    "고마움의 꽃망울이 터지는 봄",
    "꿈이 그대를 춤추게 하라",
    "넓은 하늘의 수만 별을 그대로 총총",
    "삶의 힘이 끝없이 자라는 우리들",
    "우리의 삶 자체가 하나의 꽃밭이다",
    "맑고 아름다운 하늘을 받들어",
    "내 삶의 나날들을 기쁨으로 아름답게",
    "가장 아름다운 열매를 위한 시간",
    "얼음 뚫고 봄의 빗장 열어 마주하는 희망",
    "바람들은 맑은 햇살을 뿌리며 돌아간다",
    "모두가 이름이 붙어 있지 않은 보석들",
    "내게 오는 모든 것은 다 축복이었다",
    "많이 사랑할수록 더 맑게 흐르는",
    "흙덩이의 무게를 이기고 올라오는 싹",
    "환한 빛으로 반짝이는 삶의 굽이에서",
    "바위는 제자리에 옴찍 않노니",
    "어둠이 없으면 별의 반짝임도 없으리",
    "굽은 나무의 그림자가 사랑스럽다",
    "해맑은 숨결 네 웃음만으로 가득해",
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
        app_commands.Choice(name = "수능/모의고사 필적확인란 문구", value = "수능/모의고사 필적확인란 문구"),
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
        elif 종류 == "수능/모의고사 필적확인란 문구" :
            global exam_handwriting_texts
            quote = random.choice(exam_handwriting_texts)
            embed = discord.Embed(
                title="수능/모의고사 필적확인란 문구",
                description=f"\"{quote}\"",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
            return