import discord
from datetime import datetime, timedelta
import json
import os

from discord.ext import commands
from discord import app_commands
from discord import Interaction
from discord import Member
from discord import Embed
from discord import utils
from discord import TextChannel
from discord import User
from discord import PermissionOverwrite
from discord import Permissions
from discord import Embed
from discord import Colour

developer = 1305492487137267722 # 개발자

import pytz

kst = pytz.timezone('Asia/Seoul')

using_server = 1320303102703702037
record_channel = 1320304892992028785 # 제재 내역 채널 ID
message_log = 1325006023064293417  # 여기에 기록할 채널의 ID를 입력하세요


# 차단 정보를 저장할 JSON 파일 경로
BLOCKED_USERS_FILE = "command_blocked_user.json"




# JSON 파일에서 차단된 사용자 정보를 불러오는 함수
def load_blocked_users2():
    if not os.path.exists(BLOCKED_USERS_FILE):
        return {}
    with open(BLOCKED_USERS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # 파일 내용이 올바르지 않을 경우 빈 딕셔너리 반환
            data = {}
    return data

# JSON 파일에 차단된 사용자 정보를 저장하는 함수
def save_blocked_users2(data):
    with open(BLOCKED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_blocked(user: discord.User):
    data = load_blocked_users2()
    user_id = str(user.id)  # JSON 키로 사용하기 위해 문자열로 변환
    if user_id not in data:
        # 차단 정보가 없는 경우
        return [False, None, None]
    
    blocked_info = data[user_id]
    # "until" 필드의 날짜를 datetime 객체로 변환
    try:
        blocked_until = datetime.strptime(blocked_info.get("until", ""), "%Y-%m-%d").date()
    except ValueError:
        # 날짜 형식이 올바르지 않으면 차단 해제된 것으로 간주
        return [False, None, None]
    
    today = datetime.today().date()
    if today > blocked_until:
        # 차단 기간이 끝난 경우
        return [False, None, None]
    
    # 차단 기간이 아직 남아있는 경우
    return [True, blocked_info.get("until"), blocked_info.get("reason")]

def is_valid_time(time_str):
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False