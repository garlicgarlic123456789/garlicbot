# 주의: 이 파일의 코드들은 정상 작동하는지 테스트되지 않았습니다.

import discord
from discord import app_commands
from datetime import datetime
import pytz

from commands.database import *
from commands.define import *
from main import personal_info_detect_ai

class PromoteServerAddModal(discord.ui.Modal, title="서버 찾기 추가"):
    def __init__(self, interaction: discord.Interaction):
        super().__init__()
        self.interaction = interaction
    
    type_options = [
        discord.SelectOption(label = "친목", value = "친목", description = "다양한 유저들과 친분을 쌓는 서버"),
        discord.SelectOption(label = "게임", value = "게임", description = "다양한 유저들과 게임을 하는 서버 (친목 서버인데 게임 위주로 하는 경우 이 항목을 선택하세요.)"),
        discord.SelectOption(label = "정보", value = "정보", description = "다양한 유저들과 특정 분야에 대한 정보를 주고 받는 서버"),
        discord.SelectOption(label = "스트리머 (공식)", value = "스트리머 (공식)", description = "특정 스트리머에 대해 이야기를 나누는 스트리머의 공식 서버"),
        discord.SelectOption(label = "스트리머 (비공식)", value = "스트리머 (비공식)", description = "특정 스트리머에 대해 이야기를 나누는 서버 (비공식 서버)"),
        discord.SelectOption(label = "개발", value = "개발", description = "개발 관련 이야기를 나누는 서버"),
        discord.SelectOption(label = "홍보", value = "홍보", description = "타 서버를 홍보하기 위한 서버 (배너 서버 등)"),
        discord.SelectOption(label = "기타", value = "기타", description = "기타 다른 디스코드 서버")
    ]

    personal_info_required_option = [
        discord.SelectOption(label = "개인정보 공개가 강제됨", value = True, description = "나이, 성별을 포함한 개인정보를 하나 이상 제공해야 활동이 가능한 서버"),
        discord.SelectOption(label = "개인정보 공개가 강제되지 아니함", value = False, description = "나이, 성별을 포함하여 어떠한 개인정보를 공개하지 않고도 활동이 가능한 서버")
    ]

    allowed_option = [
        discord.SelectOption(label = "허용됨", value = True, description = "해당 행위가 조금이라도 허용된다면 이 항목을 선택해 주세요."),
        discord.SelectOption(label = "금지됨", value = False, description = "해당 행위가 예외없이 완전히 금지되어 있다면 이 항목을 선택해 주세요.")
    ]

    chat_or_voice_option = [
        discord.SelectOption(label = "둘 모두", value = "all", description = "텍스트 채널과 음성 채널 모두 사용 비중이 높은 서버"),
        discord.SelectOption(label = "텍스트 채팅 위주", value = "text", description = "텍스트 채널 사용 비중이 높은 서버"),
        discord.SelectOption(label = "음성 채팅 위주", value = "voice", description = "음성 채널 사용 비중이 높은 서버")
    ]
    
    server_info = discord.ui.TextInput(label="서버 소개", placeholder="서버에 대한 소개", required=False)
    server_type = discord.ui.Select(label = "서버 종류", placeholder = "서버 종류 선택", min_values = 1, max_values = 1, options = type_options, required = True)
    personal_info_required = discord.ui.Select(label = "서버 활동을 위해 개인정보(나이 및 성별 포함) 공개가 의무화되는지 그 여부", placeholder = "중요: 나이 및 성별도 개인정보로 간주하며 서버의 관리자에게만 공개하는 경우에도 공개로 분류합니다. 이 점 유의하여 선택해 주세요.", min_values = 1, max_values = 1, options = personal_info_required_option, required = True)

    bad_words_allowed = discord.ui.Select(label = "서버 내 욕설 및 비속어 사용 허용 여부", placeholder = "조금이라도 허용된다면 \'허용됨\'을 선택해주세요.", min_values = 1, max_values = 1, options = allowed_option, required = True)
    political_content_allowed = discord.ui.Select(label = "서버 내 정치적인 대화 및 정치드립 허용 여부", placeholder = "조금이라도 허용된다면 \'허용됨\'을 선택해주세요.", min_values = 1, max_values = 1, options = allowed_option, required = True)
    sexual_content_allowed = discord.ui.Select(label = "서버 내 성적인 대화 허용 여부", placeholder = "조금이라도 허용된다면 \'허용됨\'을 선택해주세요.", min_values = 1, max_values = 1, options = allowed_option, required = True)
    
    chat_or_voice = discord.ui.Select(label = "서버에서 가장 많이 사용되는 채팅 방식 (텍스트/음성)", placeholder = "서버에서 텍스트 채팅과 음성 채팅 중 어느 것을 더 많이 이용하는지 선택해주세요.", min_values = 1, max_values = 1, options = chat_or_voice_option, required = True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await add_promote_server(interaction.guild, self.server_info.value, self.server_type, self.personal_info_required, self.bad_words_allowed, self.sexual_content_allowed, self.political_content_allowed, self.chat_or_voice)

class promote_server(app_commands.Group) : 
    def __init__(self):
        super().__init__(name="서버찾기", description="서버 찾기 기능 관련 명령어")
    
    @app_commands.command(name="추가", description="현재 서버를 서버 찾기 시스템에 등록합니다.")
    @app_commands.default_permissions(administrator=True)
    async def promote_server_add(self, interaction: discord.Interaction):
        modal = PromoteServerAddModal(interaction)
        raise DevelopingFuctionError("아직 개발 중인 기능입니다. 자세히 알아보려면 https://github.com/garlicfood1234/garlicbot/issues/176 방문하세요.")
        await interaction.response.send_modal(modal)
        

        