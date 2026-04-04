import discord
from datetime import datetime, timedelta
import json
import os
import re
import copy

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
import pytz

import asyncio

from bot_app.config.constants import (
    BLOCKED_USERS_FILE,
    TRANSFER_WARN,
    WARN_LAW,
    WARN_SECRET,
    build_allowed_mentions,
)
from bot_app.config.env import (
    get_gemini_api_key,
    get_train_arrivals_api_key,
    get_train_timetable_api_key,
    load_environment,
)
from bot_app.config.ids import (
    DEVELOPER_USER_ID,
    MESSAGE_LOG_CHANNEL_ID,
    RECORD_CHANNEL_ID,
    USING_SERVER_ID,
)

# API KEY 정보로드
load_environment()

class ObsoleteFunctionError(Exception): # 오래되었고, 더 이상 현재 버전에서 사용되지 않는 기능
    pass

KST = pytz.timezone('Asia/Seoul')

warn_law = WARN_LAW
warn_secret = WARN_SECRET

# Legacy-compatible scalar state that still relies on module-level rebinding.
railblue_onoff = False

train_timetable_api_key = get_train_timetable_api_key()
train_arrivals_api_key = get_train_arrivals_api_key()

from bot_app.ai.gemini_runtime import (
    API_URL,
    Client,
    cute_model,
    cute_model2,
    cute_model3,
    cute_model4,
    cute_model5,
    cute_model6,
    cute_model7,
    cute_model8,
    cute_model9,
    gemini_api_key,
    gemini_client,
    genai,
    judge_model,
    model,
    two_five_lite_model,
    two_lite_model,
    two_model,
    types,
)
from bot_app.core.bot_factory import build_bot, build_intents
from bot_app.core.runtime_state import (
    anti_raid_settings_cache,
    chat_analyze_count,
    chat_analyze_count_channel,
    chat_analyze_onoff_cache,
    gpt_chat_threads,
    last_auto_respond_time,
    railblue_accept_ready,
    railblue_last_time,
    ticket_last_time,
    xp_setting,
)

developer = DEVELOPER_USER_ID

intents = build_intents()

mention_setting = build_allowed_mentions()

bot = build_bot(
    intents=intents,
    allowed_mentions=mention_setting,
)

import pytz

status_id = 0

kst = pytz.timezone('Asia/Seoul')

using_server = USING_SERVER_ID
record_channel = RECORD_CHANNEL_ID  # 제재 내역 채널 ID
message_log = MESSAGE_LOG_CHANNEL_ID  # 여기에 기록할 채널의 ID를 입력하세요

transfer_warn = TRANSFER_WARN

fast_transfer = {
    "1호선": {
        "회룡역": "1호선 (연천 방면) → 의정부 경전철: 5-3\n1호선 (인천 방면) → 의정부 경전철: 6-2",
        "도봉산역": "1호선 (연천 방면) → 7호선: 2-1\n1호선 (인천 방면) → 7호선: 9-3",
        "창동역": "1호선 (연천 방면) → 4호선: 8-1\n1호선 (인천 방면) → 4호선: 10-3",
        "광운대역": "1호선 (연천 방면) → 경춘선: 1-3\n1호선 (인천 방면) → 경춘선: 10-2",
        "석계역": "1호선 (연천 방면) → 6호선: 10-4\n1호선 (인천 방면) → 6호선: 1-1",
        "회기역": "1호선 (연천 방면) → 경의중앙선, 경춘선: 4-3\n1호선 (인천 방면) → 경의중앙선, 경춘선: 7-2",
        "청량리역": transfer_warn + "1호선 (연천 방면) → 경의중앙선, 경춘선, 수인분당선: 1-1\n1호선 (인천/신창 방면) → 경의중앙선, 경춘선, 수인분당선: 10-4",
        "신설동역": "1호선 (연천 방면) → 2호선, 우이신설선: 9-4\n1호선 (인천/신창 방면) → 2호선, 우이신설선: 2-1",
        "동묘앞역": "1호선 (연천 방면) → 6호선: 9-2\n1호선 (인천/신창 방면) → 6호선: 2-3",
        "동대문역": transfer_warn + "1호선 (연천 방면) → 4호선: 9-3\n1호선 (인천/신창 방면) → 4호선: 1-3",
        "종로3가역": transfer_warn + "1호선 (연천 방면) → 3호선, 5호선: 6-1\n1호선 (인천/신창 방면) → 3호선: 6-2\n1호선 (인천/신창 방면) → 5호선: 4-2, 7-3\n\n혼잡 시 1호선 양방향 → 3호선, 5호선 환승에 4-2, 7-3를 이용할 수 있습니다.",
        "시청역": "1호선 (연천 방면) → 2호선: 10-4\n1호선 (인천/신창 방면) → 2호선: 1-1",
        "서울역": transfer_warn + "1호선 (연천 방면) → 4호선, 공항철도, GTX-A: 10-4\n1호선 (연천 방면) → 경의중앙선: 4-3\n1호선 (인천/신창 방면) → 4호선, 공항철도, GTX-A: 1-2\n1호선 (인천/신창 방면) → 경의중앙선: 8-2\n\n혼잡 시 1호선에서 다른 모든 노선으로의 환승에 1호선 연천 방면 10-4, 1호선 인천/신창 방면 1-2를 이용할 수 있습니다.",
        "용산역": "1호선 (연천 방면) → 경의중앙선: 10-1\n1호선 (인천/신창 방면) → 경의중앙선: 1-1",
        "노량진역": "1호선 (연천 방면) → 9호선: 8-4\n1호선 (용산 방면 급행) → 9호선: 5-2\n1호선 (인천/신창 방면) → 9호선: 3-1\n1호선 (동인천 방면 급행) → 9호선: 6-3",
        "대방역": "1호선 (연천 방면) → 신림선: 4-3\n1호선 (용산 방면 급행) → 신림선: 4-2\n1호선 (인천/신창 방면) → 신림선: 4-1, 7-3\n1호선 (동인천 방면 급행) → 신림선: 5-1",
        "신길역": "1호선 (연천 방면) → 5호선: 9-1\n1호선 (인천/신창 방면) → 5호선: 2-3",
        "신도림역": "1호선 (연천 방면) → 2호선: 5-1\n1호선 (인천/신창 방면) → 2호선: 2-3, 6-2\n경인선 특급/급행 (용산 방면) → 2호선: 8-3\n경인선 특급/급행 (동인천 방면) → 2호선: 3-2, 6-1\n광명셔틀 (양방향) → 2호선: 4-4",
        "구로역": "1호선 (경부선 광운대 방면) → 1호선 (인천 방면): 3-4, 6-1, 10-4\n1호선 (경인선 연천 방면) → 1호선 (신창 방면): 4-1, 4-2, 5-3, 5-4를 제외한 모든 출입문\n1호선 (경인선 연천 방면) → 1호선 광명셔틀: 3-4, 6-1, 10-4\n1호선 (경부선 신창 방면) → 1호선 인천 방면 또는 1호선 (경인선 인천 방면) → 1호선 (신창 방면): 1-1, 5-4, 8-1\n1호선 (광명발 영등포행) → 1호선 인천 방면: 4-1, 4-2, 5-3, 5-4를 제외한 모든 출입문\n1호선 광명발 영등포행 → 1호선 (동인천 방면 급행) 또는 1호선 (동인천발 용산행 급행) → 1호선 신창 방면: 3-4, 6-1, 10-4",
        "온수역": "1호선 (연천 방면) → 7호선: 10-4\n1호선 (인천 방면) → 7호선: 1-1",
        "소사역": "1호선 (연천 방면) → 서해선: 6-2\n1호선 (인천 방면) → 서해선: 5-3",
        "부평역": "1호선 (연천 방면) → 인천 1호선: 9-2\n1호선 (인천 방면) → 인천 1호선: 2-3",
        "주안역": "1호선 (연천 방면) → 인천 2호선: 9-4\n1호선 (인천 방면) → 인천 2호선: 1-4",
        "인천역": "1호선 → 수인분당선: 4-1",
        "가산디지털단지역": "1호선 (청량리 방면) → 7호선: 10-3\n1호선 (신창 방면) → 7호선: 1-2",
        "금천구청역": "1호선 (신창 방면) → 광명셔틀 (광명 방면): 1-1 ~ 4-4\n1호선 (청량리 방면) → 광명셔틀 (광명 방면): 4-4\n광명셔틀 (영등포 방면) → 1호선 (신창 방면): 4-4\n광명셔틀 (영등포 방면) → 1호선 (청량리 방면): 모든 출입문",
        "금정역": "1호선 (신창 방면) → 4호선 (오이도 방면): 모든 출입문\n1호선 (청량리 방면) → 4호선 (당고개 방면): 모든 출입문\n1호선 (청량리 방면) → 4호선 (오이도 방면): 2-3\n1호선 (신창 방면) → 4호선 (당고개 방면): 9-2",
        "수원역": "1호선 (청량리 방면) → 수인분당선: 8-2\n1호선 (신창 방면) → 수인분당선: 1-3",
        "병점역": "1호선 (청량리 방면) → 1호선 (서동탄/천안/신창 방면): 6-1"
    },
    "2호선": {
        "시청역": "2호선 (내선순환) → 1호선: 1-1\n2호선 (외선순환) → 1호선: 10-4",
        "을지로3가역": "2호선 (내선순환) → 3호선: 1-1\n2호선 (외선순환) → 3호선: 10-4",
        "을지로4가역": "2호선 (내선순환) → 5호선: 4-3\n2호선 (외선순환) → 5호선: 7-2",
        "동대문역사문화공원역": transfer_warn + "2호선 (내선순환) → 4호선: 9-2\n2호선 (내선순환) → 5호선: 6-2, 8-2\n2호선 (외선순환) → 4호선: 2-4\n2호선 (외선순환) → 5호선: 3-3, 5-3",
        "신당역": transfer_warn + "2호선 (내선순환) → 6호선: 10-4\n2호선 (외선순환) → 6호선: 1-1",
        "왕십리역": "2호선 (내선순환) → 5호선: 6-1\n2호선 (내선순환) → 경의중앙선, 수인분당선: 3-1\n2호선 (외선순환) → 5호선: 5-4\n2호선 (외선순환) → 경의중앙선, 수인분당선: 8-2",
        "성수역": "2호선 (내선순환) → 성수지선: 10-4\n2호선 (외선순환) → 성수지선: 4-1 ~ 7-4\n성수지선 → 2호선 (내선순환): 4-4\n성수지선 → 2호선 (외선순환): 모든 출입문",
        "건대입구역": "2호선 (내선순환) → 7호선: 3-2\n2호선 (외선순환) → 7호선: 8-3",
        "잠실역": "2호선 (내선순환) → 8호선: 10-4\n2호선 (외선순환) → 8호선: 1-1",
        "종합운동장역": transfer_warn + "2호선 (내선순환) → 9호선: 9-1\n2호선 (외선순환) → 9호선: 3-1",
        "선릉역": "2호선 (내선순환) → 수인분당선 (인천 방면): 6-2\n2호선 (내선순환) → 수인분당선 (인천 방면): 5-2\n2호선 (외선순환) → 수인분당선 (인천 방면): 5-2\n2호선 (외선순환) → 수인분당선 (청량리 방면): 6-3",
        "강남역": "2호선 (내선순환) → 신분당선: 6-3\n2호선 (외선순환) → 신분당선: 5-1",
        "교대역": transfer_warn + "2호선 (내선순환) → 3호선: 1-1\n2호선 (외선순환) → 3호선: 10-4",
        "사당역": "2호선 (내선순환) → 4호선: 6-1\n2호선 (외선순환) → 4호선: 5-3",
        "신림역": "2호선 (내선순환) → 신림선: 6-2\n2호선 (외선순환) → 신림선: 5-2",
        "대림역": "2호선 (내선순환) → 7호선: 2-1\n2호선 (외선순환) → 7호선: 9-3",
        "신도림역": transfer_warn + "2호선 양방향 → 1호선: 2-2, 4-2, 6-4, 7-3, 9-2\n2호선 양방향 → 2호선 신정지선: 2-2, 4-2, 6-1, 6-4, 7-3, 9-2\n2호선 신정지선 (당역 종착) → 1호선: 3-1, 3-4, 6-4\n2호선 내선순환 (당역 종착) → 1호선: 2-2, 6-1, 6-4\n2호선 내선순환 (당역 종착) → 2호선 신정지선 (까치산 방면): 3-1 ~ 8-4\n2호선 외선순환 (당역 종착) → 1호선: 2-2, 4-2, 7-3, 9-3\n2호선 외선순환 (당역 종착) → 2호선 신정지선 (까치산 방면): 2-2, 4-2, 7-3, 9-3",
        "영등포구청역": "2호선 (내선순환) → 5호선: 7-4\n2호선 (외선순환) → 5호선: 2-3",
        "당산역": "2호선 (내선순환) → 9호선: 7-4\n2호선 (외선순환) → 9호선: 4-1",
        "합정역": "2호선 (내선순환) → 6호선: 9-2\n2호선 (외선순환) → 6호선: 2-2",
        "홍대입구역": transfer_warn + "2호선 (내선순환) → 다른 노선: 3-3\n2호선 (외선순환) → 다른 노선: 8-2",
        "충정로역": "2호선 (내선순환) → 5호선: 7-3\n2호선 (외선순환) → 5호선: 4-2",
        "까치산역": "2호선 신정지선 → 5호선: 1-1",
        "신설동역": "2호선 성수지선 → 1호선, 우이신설선: 1-1",
    },
    "3호선": {
        "대곡역": "3호선 (대화 방면) → 다른 노선: 4-1, 9-1\n3호선 (오금 방면) → 다른 노선: 2-4, 7-4",
        "연신내역": "3호선 (대화 방면) → 6호선, GTX-A: 5-1\n3호선 (오금 방면) → 6호선, GTX-A: 6-3",
        "불광역": "3호선 (대화 방면) → 6호선: 1-1\n3호선 (오금 방면) → 6호선: 10-4",
        "종로3가역": transfer_warn + "3호선 (대화 방면) → 1호선 (연천 방면): 9-2\n3호선 (대화 방면) → 1호선 (인천 방면): 10-4\n3호선 (대화 방면) → 5호선: 2-2, 4-3\n3호선 (오금 방면) → 1호선 (연천 방면): 2-3\n3호선 (오금 방면) → 1호선 (인천 방면): 1-1\n3호선 (오금 방면) → 5호선: 7-2, 9-3",
        "을지로3가역": "3호선 (대화 방면) → 2호선 (내선순환): 7-1\n3호선 (대화 방면) → 2호선 (외선순환): 2-2\n3호선 (오금 방면) → 2호선 (내선순환): 4-4\n3호선 (오금 방면) → 2호선 (외선순환): 9-3",
        "충무로역": "3호선 (대화 방면) → 4호선 (진접 방면): 4-4\n3호선 (대화 방면) → 4호선 (오이도 방면): 4-1\n3호선 (오금 방면) → 4호선 (진접 방면): 8-1\n3호선 (오금 방면) → 4호선 (오이도 방면): 8-4\n혼잡 시 3호선 대화 방면 → 4호선 환승에 6-3을, 3호선 오금 방면 → 4호선 환승에 5-2를 이용할 수 있습니다.",
        "약수역": "3호선 (대화 방면) → 6호선: 4-3\n3호선 (오금 방면) → 6호선: 7-1",
        "옥수역": "3호선 (대화 방면) → 경의중앙선/ITX-청춘: 9-4\n3호선 (오금 방면) → 경의중앙선/ITX-청춘: 1-4",
        "신사역": "3호선 (대화 방면) → 신분당선: 9-2\n3호선 (오금 방면) → 신분당선: 2-2",
        "고속터미널역": "3호선 (대화 방면) → 7호선: 9-2\n3호선 (대화 방면) → 9호선: 2-3\n3호선 (오금 방면) → 7호선: 2-3\n3호선 (오금 방면) → 9호선: 9-2",
        "교대역": transfer_warn + "3호선 (대화 방면) → 2호선 (내선순환): 3-3 (공식적인 빠른 환승 정보대로 갈 시 이동동선이 펜스로 막혀있음에 주의)\n3호선 (대화 방면) → 2호선 (외선순환): 7-4\n3호선 (오금 방면) → 2호선 (내선순환): 8-2 (공식적인 빠른 환승 정보대로 갈 시 이동동선이 펜스로 막혀있음에 주의)\n3호선 (오금 방면) → 2호선 (외선순환): 4-1",
        "양재역": "3호선 (대화 방면) → 신분당선: 5-3\n3호선 (오금 방면) → 신분당선: 6-1",
        "도곡역": "3호선 (대화 방면) → 수인분당선: 6-3\n3호선 (오금 방면) → 수인분당선: 6-2",
        "수서역": "3호선 (대화 방면) → 다른 노선: 3-1, 5-3\n3호선 (오금 방면) → 다른 노선: 6-3, 8-4",
        "가락시장역": "3호선 (대화 방면) → 8호선: 9-4\n3호선 (오금 방면) → 8호선: 2-1",
        "오금역": "3호선 → 5호선: 9-3"
    },
    "4호선": {
        "노원역": "4호선 (진접 방면) → 7호선: 10-4\n4호선 (오이도 방면) → 7호선: 1-1",
        "창동역": "4호선 (진접 방면) → 1호선: 3-4, 9-2\n4호선 (오이도 방면) → 1호선: 2-2, 8-1",
        "성신여대입구역": "4호선 (진접 방면) → 우이신설선: 5-4\n4호선 (오이도 방면) → 우이신설선: 5-2",
        "동대문역": transfer_warn + "4호선 (진접 방면) → 1호선: 3-4\n4호선 (오이도 방면) → 1호선: 7-4",
        "동대문역사문화공원역": "4호선 (진접 방면) → 2호선: 1-1\n4호선 (오이도 방면) → 2호선: 10-4\n4호선 (진접 방면) → 5호선: 9-2\n4호선 (오이도방면) → 5호선: 2-3",
        "충무로역": "4호선 (진접 방면) → 3호선: 5-1\n4호선 (오이도 방면) → 3호선: 7-1",
        "서울역": transfer_warn + "4호선 (진접 방면) → 1호선, GTX-A, 경의중앙선: 1-1\n4호선 (진접 방면) → 공항철도: 3-4\n4호선 (오이도 방면) → 1호선, GTX-A, 경의중앙선: 10-4\n4호선 (오이도 방면) → 공항철도: 8-1",
        "삼각지역": "4호선 (진접 방면) → 6호선: 1-1\n4호선 (오이도 방면) → 6호선: 10-4",
        "이촌역": transfer_warn + "4호선 (진접 방면) → 경의중앙선: 4-2\n4호선 (오이도 방면) → 경의중앙선: 7-2",
        "동작역": transfer_warn + "4호선 (진접 방면) → 9호선: 6-3, 8-4\n4호선 (오이도 방면) → 9호선: 3-1, 5-3",
        "이수역": "4호선 (진접 방면) → 7호선: 10-4\n4호선 (오이도 방면) → 7호선: 1-1",
        "사당역": "4호선 (진접 방면) → 2호선 (내선순환): 4-1\n4호선 (진접 방면) → 2호선 (외선순환): 10-4\n4호선 (오이도 방면) → 2호선 (내선순환): 7-3\n2호선 (오이도 방면) → 2호선 (외선순환): 1-1\n\n혼잡 시 NH 시간대 한정으로 4호선 진접 방면 → 2호선 내선순환은 6-2를, 4호선 오이도 방면 → 2호선 내선순환은 5-3을 이용할 수 있습니다.",
        "금정역": "4호선 (진접 방면) → 1호선 (청량리 방면): 모든 출입문 (평면환승)\n4호선 (진접 방면) → 1호선 (신창 방면): 2-3\n4호선 (오이도 방면) → 1호선 (청량리 방면): 7-1\n4호선 (오이도 방면) → 1호선 (신창 방면): 모든 출입문 (평면환승)",
        "한대앞역": "4호선 (진접 방면) → 수인분당선 (청량리 방면): 1-1 ~ 6-4 (평면환승)\n4호선 (오이도 방면) → 수인분당선 (인천 방면): 5-1 ~ 10-4 (평면환승)",
        "초지역": "4호선 (진접 방면) → 수인분당선 (청량리 방면): 1-1 ~ 6-4 (평면환승)\n4호선 (오이도 방면) → 수인분당선 (인천 방면): 5-1 ~ 10-4 (평면환승)\n4호선 (진접 방면) → 서해선: 1-1\n4호선 (오이도 방면) → 서해선: 10-4",
        "오이도역": "4호선 (당역 종착) → 수인분당선 (인천 방면): 5-1 ~ 10-4 (평면환승)",
    },
    "5호선": {
        "김포공항역": "5호선 (하남검단산, 마천 방면) → 다른 노선: 1-4\n5호선 (방화 방면) → 다른 노선: 7-1",
        "까치산역": "5호선 (하남검단산/마천 방면) → 2호선 신정지선: 4-4\n5호선 (방화 방면) → 2호선 신정지선: 1-1",
        "영등포구청역": "5호선 (하남검단산/마천 방면) → 2호선: 2-3\n5호선 (방화 방면) → 2호선: 7-2",
        "신길역": transfer_warn + "5호선 (하남검단산/마천 방면) → 1호선: 2-2\n5호선 (방화 방면) → 1호선: 7-3",
        "여의도역": "5호선 (하남검단산/마천 방면) → 9호선: 4-1\n5호선 (방화 방면) → 9호선: 5-4",
        "공덕역": transfer_warn + "5호선 (하남검단산/마천 방면) → 다른 노선: 8-4\n5호선 (방화 방면) → 다른 노선: 1-1",
        "충정로역": "5호선 (하남건단산/마천 방면) → 2호선: 5-3\n5호선 (방화 방면) → 2호선: 4-1",
        "종로3가역": transfer_warn + "5호선 (하남검단산/마천 방면) → 1호선, 3호선: 1-1\n5호선 (방화 방면) → 1호선, 3호선: 8-4",
        "을지로4가역": "5호선 (하남검단산/마천 방면) → 2호선: 내선순환 1-1, 외선순환 1-4\n5호선 (방화 방면) → 2호선: 내선순환 8-4, 외선순환 8-1",
        "동대문역사문화공원역": transfer_warn + "5호선 (하남검단산/마천 방면) → 다른 노선: 1-1\n5호선 (방화 방면) → 다른 노선: 8-4",
        "청구역": "5호선 (하남검단산/마천 방면) → 6호선: 6-4\n5호선 (방화 방면) → 6호선: 5-1",
        "왕십리역": "5호선 (하남검단산/마천 방면) → 다른 노선: 5-2, 7-2\n5호선 (방화 방면) → 다른 노선: 2-3, 4-3",
        "군자역": "5호선 (하남검단산/마천 방면) → 7호선: 장암 방면 1-1, 석남 방면 8-4\n5호선 (방화 방면) → 7호선: 장암 방면 8-4, 석남 방면 1-1",
        "천호역": "5호선 (하남검단산/마천 방면) → 8호선: 별내 방면 8-1, 모란 방면 8-2\n5호선 (방화 방면) → 8호선: 별내 방면 1-3, 모란 방면 1-2",
        "강동역": "5호선 (방화 방면) → 5호선 (하남검단산/마천 방면): 1-1, 8-4\n5호선 (마천 방면) ↔ 5호선 (하남검단산 방면): 모든 출입문 (평면환승)",
        "올림픽공원역": "5호선 (마천 방면) → 9호선: 4-4\n5호선 (방화 방면) → 9호선: 6-1",
        "오금역": "5호선 (마천 방면) → 3호선: 1-3\n5호선 (방화 방면) → 3호선: 8-2"
    },
    "6호선" : {
        "불광역": "6호선 → 3호선 (대화 방면): 2-3\n6호선 → 3호선 (오금 방면): 7-2",
        "연신내역": "6호선 → 다른 노선: 6-2",
        "디지털미디어시티역": "6호선 (신내 방면) → 경의중앙선: 7-2\n6호선 (신내 방면) → 공항철도: 1-1\n6호선 (응암 방면) → 경의중앙선: 2-2\n6호선 (응암 방면) → 공항철도: 8-4",
        "합정역": "6호선 (신내 방면) → 2호선: 6-2\n6호선 (응암 방면) → 2호선: 3-2",
        "공덕역": "6호선 (신내 방면) → 다른 노선: 8-4\n6호선 (응암 방면) → 다른 노선: 1-1",
        "효창공원앞역": "6호선 (신내 방면) → 경의중앙선: 3-1\n6호선 (응암 방면) → 경의중앙선: 6-4",
        "삼각지역": "6호선 (신내 방면) → 4호선 (진접 방면) 또는 6호선 (응암 방면) → 4호선 (오이도 방면): 3-1\n6호선 (신내 방면) → 4호선 (오이도 방면) 또는 6호선 (응암 방면) → 4호선 (진접 방면): 6-4",
        "약수역": "6호선 (신내 방면) → 3호선: 1-1\n6호선 (응암 방면) → 3호선: 8-4",
        "청구역": "6호선 (신내 방면) → 5호선: 6-2\n6호선 (응암 방면) → 5호선: 6-1",
        "신당역": "6호선 (신내 방면) → 2호선: 8-4\n6호선 (응암 방면) → 2호선: 1-1",
        "동묘앞역": "6호선 (신내 방면) → 1호선: 2-2\n6호선 (응암 방면) → 1호선: 7-3",
        "보문역": "6호선 → 우이신설선: 3-4",
        "석계역": "6호선 (신내 방면) → 1호선: 5-2\n6호선 (응암 방면) → 1호선: 4-3",
        "태릉입구역": "6호선 (신내 방면) → 7호선: 1-1\n6호선 (응암 방면) → 7호선: 8-4",
        "신내역": "6호선 (신내 방면) → 경춘선: 7-4"
    },
    "7호선" : {
        "도봉산역": "7호선 (장암 방면) → 1호선: 1-1\n7호선 (석남 방면) → 1호선: 8-4",
        "노원역": "7호선 (장암 방면) → 4호선: 1-1\n7호선 (석남 방면) → 4호선: 8-4",
        "태릉입구역": "7호선 (장암 방면) → 6호선: 8-4\n7호선 (석남 방면) → 6호선: 1-1",
        "상봉역": "7호선 (장암 방면) → 경의중앙선, 경춘선 → 5-4\n7호선 (석남 방면) → 경의중앙선, 경춘선: 3-4",
        "군자역": "7호선 (장암 방면) → 5호선: 5-2\n7호선 (석남 방면) → 5호선: 5-1",
        "건대입구역": "7호선 (장암 방면) → 2호선: 8-4\n7호선 (석남 방면) → 2호선: 1-1",
        "강남구청역": "7호선 (장암 방면) → 수인분당선: 4-3\n7호선 (석남 방면) → 수인분당선: 5-1",
        "논현역": "7호선 (장암 방면) → 신분당선: 4-4\n7호선 (석남 방면) → 신분당선: 5-2",
        "고속터미널역": "7호선 (장암 방면) → 3호선, 9호선: 2-3\n7호선 (석남 방면) → 3호선, 9호선: 7-1",
        "이수역": "7호선 (장암 방면) → 4호선: 2-2\n7호선 (석남 방면) → 4호선: 8-4",
        "보라매역": "7호선 (장암 방면) → 신림선: 1-1\n7호선 (석남 방면) → 신림선: 8-4",
        "대림역": "7호선 (장암 방면) → 2호선: 8-4\n7호선 (석남 방면) → 2호선: 1-1",
        "가산디지털단지역": "7호선 (장암 방면) → 1호선: 4-3\n7호선 (석남 방면) → 1호선: 5-1",
        "온수역": "7호선 (장암 방면) → 1호선: 8-4\n7호선 (석남 방면) → 1호선: 1-1",
        "부전종합운동장역": "7호선 (장암 방면) → 서해선: 5-4\n7호선 (석남 방면) → 서해선: 3-1",
        "부평구청역": "7호선 (장암 방면) → 인천 1호선 (계양 방면): 4-3\n7호선 (장암 방면) → 인천 1호선 (송도달빛축제공원 방면): 7-3\n7호선 (석남 방면) → 인천 1호선 (계양 방면): 5-2\n7호선 (석남 방면) → 인천 1호선 (송도달빛축제공원 방면): 2-2",
        "석남역": "7호선 → 인천 2호선: 7-1",
    },
    "8호선": {
        "별내역": "8호선 → 경춘선: 4-4",
        "구리역": "8호선 → 경의중앙선: 2-2, 5-3",
        "천호역": "8호선 (모란 방면) → 5호선 (하남검단산, 마천 방면): 5-2\n8호선 (모란 방면) → 5호선 (방화 방면): 6-1\n8호선 (별내 방면) → 5호선 (하남검단산, 마천 방면): 2-2\n8호선 (별내 방면) → 5호선 (방화 방면): 1-3",
        "잠실역": "8호선 (모란 방면) → 2호선: 1-1\n8호선 (별내 방면) → 2호선: 6-4",
        "석촌역": "8호선 (모란 방면) → 9호선: 1-1\n8호선 (별내 방면) → 9호선: 6-4",
        "가락시장역": "8호선 (모란 방면) → 3호선: 1-1\n8호선 (별내 방면) → 3호선: 6-4",
        "복정역": "8호선 (모란 방면) → 수인분당선: 3-2\n8호선 (별내 방면) → 수인분당선: 4-2",
        "모란역": "8호선 (당역 종착) → 수인분당선: 1-1\n8호선 (별내 방면) → 수인분당선: 6-4",
    },
    "9호선" : {
        "김포공항역": transfer_warn + "9호선 (개화 방면) → 5호선, 공항철도 (서울역 방면): 2-4\n9호선 (개화 방면) → 공항철도 (인천공항2터미널 방면): 모든 출입문 (평면환승)\n9호선 (개화 방면) → 김포 골드라인, 서해선: 6-1\n9호선 (중앙보훈병원 방면) → 5호선 (하남검단산/마천 방면): 6-4\n9호선 (중앙보훈병원 방면) → 5호선 (방화 방면), 김포 골드라인, 서해선: 4-4\n9호선 (중앙보훈병원 방면) → 공항철도 (서울역 방면): 모든 출입문 (평면환승)\n9호선 (중앙보훈병원 방면) → 공항철도 (인천공항2터미널 방면): 3-1",
        "마곡나루역": "9호선 (개화 방면) → 공항철도: 6-2\n9호선 (중앙보훈병원 방면) → 공항철도: 1-3",
        "당산역": "9호선 (개화 방면) → 2호선: 1-1\n9호선 (중앙보훈병원 방면) → 2호선: 4-4",
        "여의도역": "9호선 (개화 방면) → 5호선: 2-4\n9호선 (중앙보훈병원 방면) → 5호선: 4-3",
        "샛강역": "9호선 (개화 방면) → 신림선: 1-3\n9호선 (중앙보훈병원 방면) → 신림선: 6-2",
        "노량진역": "9호선 (개화 방면) → 1호선: 5-1\n9호선 (중앙보훈병원 방면) → 1호선: 2-4",
        "동작역": transfer_warn + "9호선 (개화 방면) → 4호선: 6-4\n9호선 (중앙보훈병원 방면) → 4호선: 1-1",
        "고속터미널역": transfer_warn + "9호선 (개화 방면) → 다른 노선: 4-1\n9호선 (중앙보훈병원 방면) → 다른 노선: 1-4",
        "신논현역": "9호선 (개화 방면) → 신분당선: 1-1\n9호선 (중앙보훈병원 방면) → 신분당선: 6-4",
        "선정릉역": "9호선 (개화 방면) → 수인분당선: 5-4\n9호선 (중앙보훈병원 방면) → 신분당선: 2-1",
        "종합운동장역": "9호선 (개화 방면) → 2호선: 4-1\n9호선 (중앙보훈병원 방면) → 2호선: 6-1",
        "석촌역": "9호선 (개화 방면) → 8호선 (별내 방면): 6-4\n9호선 (개화 방면) → 8호선 (모란 방면): 3-3\n9호선 (중앙보훈병원 방면) → 8호선 (별내 방면): 1-1\n9호선 (중앙보훈병원 방면) → 8호선 (모란 방면): 4-2",
        "올림픽공원역": "9호선 (개화 방면) → 5호선 (마천 방면): 4-2\n9호선 (개화 방면) → 5호선 (방화 방면): 1-2\n9호선 (중앙보훈병원 방면) → 5호선 (마천 방면): 3-3\n9호선 (중앙보훈병원 방면) → 5호선 (방화 방면): 6-3",
    },
    "공항철도": {
        "서울역": transfer_warn + "공항철도 → 다른 노선: 5-1",
        "공덕역": "공항철도 (서울 방면) → 다른 노선: 6-1\n공항철도 (인천공항2터미널 방면) → 다른 노선: 1-4",
        "홍대입구역": "공항철도 (서울 방면) → 다른 노선: 5-3\n공항철도 (인천공항2터미널 방면) → 다른 노선: 2-2",
        "디지털미디어시티역": transfer_warn + "공항철도 (서울 방면) → 다른 노선: 2-4\n공항철도 (인천공항2터미널 방면) → 다른 노선: 6-4",
        "마곡나루역": "공항철도 (서울 방면) → 9호선: 2-1\n공항철도 (인천공항2터미널 방면) → 9호선: 6-3",
        "김포공항역": transfer_warn + "공항철도 (서울 방면) → 5호선 (하남검단산/마천 방면) → 6-4\n공항철도 (서울 방면) → 5호선 (방화 방면): 4-1\n공항철도 (서울 방면) → 9호선 (개화 방면): 2-2\n공항철도 (서울 방면) → 9호선 (중앙보훈병원 방면): 모든 출입문 (평면환승)\n공항철도 (서울 방면) → 김포 골드라인, 서해선: 3-4\n공항철도 (인천공항2터미널 방면) → 5호선, 김포 골드라인, 서해선: 3-4\n공항철도 (인천공항2터미널 방면) → 9호선 (개화 방면): 모든 출입문 (평면환승)\n공항철도 (인천공항2터미널 방면) → 9호선 (중앙보훈병원 방면): 6-4",
        "계양역": "공항철도 (서울 방면) → 인천 1호선: 5-4\n공항철도 (인천공항2터미널 방면) → 인천 1호선: 1-4",
        "검암역": "공항철도 (서울 방면) → 인천 2호선: 2-2\n공항철도 (인천공항2터미널 방면) → 인천 2호선: 6-4",
    },
}
fast_transfer["인천국제공항철도"] = fast_transfer["공항철도"]


# 권한 확인이 필요한 목록
dangerous_permissions = {
    "administrator": "관리자",
    "manage_guild": "서버 관리하기",
    "manage_roles": "역할 관리하기",
    "manage_channels": "채널 관리하기",
    "create_expressions": "표현 생성하기",
    "view_guild_insights": "서버 인사이트 보기",
    "manage_webhooks": "웹후크 관리하기",
    "manage_nicknames": "별명 관리하기",
    "ban_members": "멤버 차단하기",
    "kick_members": "멤버 추방하기",
    "moderate_members": "타임아웃 멤버",
    "mention_everyone": "@everyone, @here, 모든 역할 멘션하기",
    "manage_messages": "메시지 관리",
    "manage_threads": "스레드 관리하기",
    "use_external_apps": "외부 앱 사용",
    "manage_events": "이벤트 관리하기",
    "create_events": "이벤트 생성하기",
}

error = 1

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

async def check_message(message, check_everyone_here_mention: bool = True, check_role_mention: bool = True, check_user_mention: bool = True, check_invite_link: bool = True): # 봇이 특정 str을 출력(send_message 등)하기 전에 이 함수를 통해 취약점을 확인하게 됨.
    '''
    message는 보내려는 메시지의 str 또는 임베드 객체.
    check_everyone_here_mention은 @everyone, @here 멘션을 하는지 아닌지 확인할지 결정.
    check_role_mention은 역할 멘션을 하는지 아닌지 확인할지 결정.
    check_user_mention은 유저 멘션을 하는지 아닌지 확인할지 결정.
    check_invite_link은 디스코드 서버 초대 링크를 하는지 아닌지 확인할지 결정.

    반환값은
    {
        "original_message": 원본 메시지,
        "modified_message": 수정된 메시지,
        "edited": 수정 여부(bool)
    }
    '''

    if isinstance(message, discord.Embed):
        new_message = copy.deepcopy(message)
        if new_message.title : 
            if check_everyone_here_mention:
                new_message.title = new_message.title.replace("@everyone", "@​everyone")
                new_message.title = new_message.title.replace("@here", "@​here")
            if check_role_mention:
                new_message.title = new_message.title.replace("<@&", "<@&​")
            if check_user_mention:
                new_message.title = new_message.title.replace("<@", "<@​")
            if check_invite_link:
                pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
                if re.search(pattern1, new_message.title):
                    new_message.title = new_message.title.replace(pattern1, "*(디스코드 서버 초대 링크)*")
                pattern2 = r"discord://-/invite/\S+"
                if re.search(pattern2, new_message.title):
                    new_message.title = new_message.title.replace(pattern2, "*(디스코드 서버 초대 링크)*")
        if new_message.description : 
            if check_everyone_here_mention:
                new_message.description = new_message.description.replace("@everyone", "@​everyone")
                new_message.description = new_message.description.replace("@here", "@​here")
            if check_role_mention:
                new_message.description = new_message.description.replace("<@&", "<@&​")
            if check_user_mention:
                new_message.description = new_message.description.replace("<@", "<@​")
            if check_invite_link:
                pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
                if re.search(pattern1, new_message.description):
                    new_message.description = new_message.description.replace(pattern1, "*(디스코드 서버 초대 링크)*")
                pattern2 = r"discord://-/invite/\S+"
                if re.search(pattern2, new_message.description):
                    new_message.description = new_message.description.replace(pattern2, "*(디스코드 서버 초대 링크)*")
        if new_message.fields : 
            new_message_field_count = len(new_message.fields)
            for i in range(new_message_field_count) : 
                if new_message.fields[i].name : 
                    if check_everyone_here_mention:
                        new_message.fields[i].name = new_message.fields[i].name.replace("@everyone", "@​everyone")
                        new_message.fields[i].name = new_message.fields[i].name.replace("@here", "@​here")
                    if check_role_mention:
                        new_message.fields[i].name = new_message.fields[i].name.replace("<@&", "<@&​")
                    if check_user_mention:
                        new_message.fields[i].name = new_message.fields[i].name.replace("<@", "<@​")
                    if check_invite_link:
                        pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
                        if re.search(pattern1, new_message.fields[i].name):
                            new_message.fields[i].name = new_message.fields[i].name.replace(pattern1, "*(디스코드 서버 초대 링크)*")
                        pattern2 = r"discord://-/invite/\S+"
                        if re.search(pattern2, new_message.fields[i].name):
                            new_message.fields[i].name = new_message.fields[i].name.replace(pattern2, "*(디스코드 서버 초대 링크)*")
                if new_message.fields[i].value : 
                    if check_everyone_here_mention:
                        new_message.fields[i].value = new_message.fields[i].value.replace("@everyone", "@​everyone")
                        new_message.fields[i].value = new_message.fields[i].value.replace("@here", "@​here")
                    if check_role_mention:
                        new_message.fields[i].value = new_message.fields[i].value.replace("<@&", "<@&​")
                    if check_user_mention:
                        new_message.fields[i].value = new_message.fields[i].value.replace("<@", "<@​")
                    if check_invite_link:
                        pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
                        if re.search(pattern1, new_message.fields[i].value):
                            new_message.fields[i].value = new_message.fields[i].value.replace(pattern1, "*(디스코드 서버 초대 링크)*")
                        pattern2 = r"discord://-/invite/\S+"
                        if re.search(pattern2, new_message.fields[i].value):
                            new_message.fields[i].value = new_message.fields[i].value.replace(pattern2, "*(디스코드 서버 초대 링크)*")
        if new_message.footer : 
            if new_message.footer.text : 
                if check_everyone_here_mention:
                    new_message.footer.text = new_message.footer.text.replace("@everyone", "@​everyone")
                    new_message.footer.text = new_message.footer.text.replace("@here", "@​here")
                if check_role_mention:
                    new_message.footer.text = new_message.footer.text.replace("<@&", "<@&​")
                if check_user_mention:
                    new_message.footer.text = new_message.footer.text.replace("<@", "<@​")
                if check_invite_link:
                    pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
                    if re.search(pattern1, new_message.footer.text):
                        new_message.footer.text = new_message.footer.text.replace(pattern1, "*(디스코드 서버 초대 링크)*")
                    pattern2 = r"discord://-/invite/\S+"
                    if re.search(pattern2, new_message.footer.text):
                        new_message.footer.text = new_message.footer.text.replace(pattern2, "*(디스코드 서버 초대 링크)*")
        
        new_message = discord.Embed.from_dict(new_message.to_dict())

        if new_message != message : 
            changed = True
        else : 
            changed = False
        
        return {
            "original_message": message,
            "modified_message": new_message,
            "edited": changed
        }
    elif isinstance(message, str):
        new_message = message
        if check_everyone_here_mention:
            new_message = new_message.replace("@everyone", "@​everyone")
            new_message = new_message.replace("@here", "@​here")
        if check_role_mention:
            new_message = new_message.replace("<@&", "<@&​")
        if check_user_mention:
            new_message = new_message.replace("<@", "<@​")
        if check_invite_link:
            pattern1 = r"(?:d|%64)(?:i|%69)(?:s|%73)(?:c|%63)(?:o|%6f)(?:r|%72)(?:d|%64)(?:app\.com\/invite|(?:\.|%2e)(?:gg|%67%67|com(?::|%3a)?443(?:\/|%2f)?invite))(?:[\/:0-9A-Za-z%\-]*)?"
            if re.search(pattern1, new_message):
                new_message = new_message.replace(pattern1, "*(디스코드 서버 초대 링크)*")
            pattern2 = r"discord://-/invite/\S+"
            if re.search(pattern2, new_message):
                new_message = new_message.replace(pattern2, "*(디스코드 서버 초대 링크)*")
        
        if message != new_message:
            changed = True
        else : 
            changed = False
        
        return {
            "original_message": message,
            "modified_message": new_message,
            "edited": changed
        }
