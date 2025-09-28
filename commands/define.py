"""
GarlicBot Main Configuration and Utilities

This module contains the main bot configuration, utility functions,
and command definitions for GarlicBot.
"""

import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction, Member, User, TextChannel, PermissionOverwrite, Permissions, Colour, utils
import os
import json
import re
import copy
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

# API KEY 정보 로드
load_dotenv()

# Import AI models from config
from config.models import (
    cute_model, cute_model2, cute_model3, cute_model4, cute_model5,
    cute_model6, cute_model7, cute_model8, cute_model9,
    judge_model, model, two_model, two_lite_model, two_five_lite_model,
    get_model_by_name, get_random_cute_model, gemini_api_key, API_URL
)

# 기본 설정
kst = pytz.timezone('Asia/Seoul')

# API 키들
train_timetable_api_key = os.getenv("train_timetable_api")
train_arrivals_api_key = os.getenv("train_arrivals_api")

# 봇 설정
using_server = 1320303102703702037
record_channel = 1320304892992028785  # 제재 내역 채널 ID
message_log = 1394228444673605754  # 메시지 로그 채널 ID

# 봇 초기화
intents = discord.Intents.all()
intents.presences = False  # Presence Intent 비활성화

bot = commands.Bot(
    command_prefix="마늘아마늘아마늘아 ",
    intents=intents,
    help_command=None
)

# 기본 변수들
xp_setting = {}
gpt_chat_threads = {}

# 경고 메시지
warn_law = "**[경고!]** 본 자료는 법적 조언이 아닌 일반적인 정보 제공 목적만을 가지고 있습니다. " \
           "특정 상황에 대해 결정하시기 전, 반드시 법률 전문가와 상의하시기 바랍니다. " \
           "본 자료를 신뢰하여 생기는 손해나 피해에 대한 책임은 사용자의 판단에 따라 " \
           "전적으로 사용자에게 있습니다."

warn_secret = "**[경고!]** 이 문서에는 기밀 정보가 포함되어 있습니다. " \
              "다른 사람(사용자)에게 유출되지 않도록 주의가 필요합니다."

print("GarlicBot define.py loaded successfully!")
