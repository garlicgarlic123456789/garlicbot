model = genai.GenerativeModel('gemini-1.5-flash')
two_model = genai.GenerativeModel('gemini-2.0-flash')
two_lite_model = genai.GenerativeModel('gemini-2.0-flash-lite')

ai_cooldowns = {} # gpt-4o 쿨타임
o3_cooldowns = {} # o3-mini 쿨타임
gpt_4_1_cooldowns = {}

# 쿨타임 (초 단위)
COOLDOWN_DURATION = 60 
o3_cooldowns_d = 60 * 60 * 24
gpt_4_1_cooldowns_d = 60 * 30

# /생성형인공지능 명령어 등록
@bot.tree.command(name="생성형인공지능", description="생성형 AI와 대화합니다.")
@app_commands.choices(
    모델 = [
        app_commands.Choice(name = "Gemini 1.5 Flash (Google에서 개발한 빠르게 답변하는 이전 모델의 경량화 버전)", value = "Gemini 1.5 Flash"),
        app_commands.Choice(name = "Gemini 2.0 Flash (Google에서 개발한 빠르게 답변하는 최신 모델의 경량화 버전)", value = "Gemini 2.0 Flash"),
        app_commands.Choice(name = "Gemini 2.0 Flash Lite (Google에서 개발한 빠르게 답변하는 최신 모델의 빠른 버전)", value = "Gemini 2.0 Flash Lite"),
        app_commands.Choice(name = "GPT-4.1 (OpenAI에서 개발한 대부분의 질문에 가장 탁월한 모델)", value = "GPT-4.1"),
        app_commands.Choice(name = "GPT-4.1 mini (OpenAI에서 개발한 대부분의 질문에 더 탁월한 모델)", value = "GPT-4.1 mini"),
        app_commands.Choice(name = "GPT-4.1 nano (OpenAI에서 개발한 대부분의 질문에 더 빠르고 탁월한 모델)", value = "GPT-4.1 nano"),
        app_commands.Choice(name = "GPT-4o mini (OpenAI에서 개발한 대부분의 질문에 더 빠른 모델)", value = "GPT-4o mini"),
        app_commands.Choice(name = "GPT-3.5 (OpenAI에서 개발한 ChatGPT에서 가장 처음에 사용되었던 레거시 모델)", value = "GPT-3.5"),
        app_commands.Choice(name = "o4-mini (OpenAI에서 개발한 고급 추론 모델)", value = "o4-mini"),
        app_commands.Choice(name = "o3-mini (OpenAI에서 개발한 추론 모델)", value = "o3-mini"),
    ]
)
async def generative_ai(interaction: discord.Interaction, 프롬프트: str, 모델: str = "Gemini 2.0 Flash"):
    # API 요청 보내기
    await interaction.response.defer()

    if "discord.gg/" in 프롬프트 or "discord.com/invite/" in 프롬프트 :
        embed = discord.Embed(
            title="오류",
            description=f"이 모델을 사용할 수 없는 환경입니다.\n\n입력이 올바르지 않습니다.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed = embed)
        return
    
    if 모델 == "Gemini 1.5 Flash" :
        response = await asyncio.to_thread(model.generate_content, 프롬프트)
        result = response.text
    elif 모델 == "Gemini 2.0 Flash" :
        response = await asyncio.to_thread(two_model.generate_content, 프롬프트)
        result = response.text
    elif 모델 == "Gemini 2.0 Flash Lite" :
        response = await asyncio.to_thread(two_lite_model.generate_content, 프롬프트)
        result = response.text
    elif 모델 == "GPT-4o mini" :
        if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in ai_cooldowns:
                elapsed = (now - ai_cooldowns[user_id]).total_seconds()
                if elapsed < COOLDOWN_DURATION:
                    remaining = int(COOLDOWN_DURATION - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            ai_cooldowns[user_id] = now
        # 객체 생성
        llm = ChatOpenAI(
            temperature=1.0,  # 창의성 (0.0 ~ 2.0)
            model_name="gpt-4o-mini",  # 모델명
        )

        # 질의내용
        question = 프롬프트
        result = llm.invoke(question)
        result = result.content
    elif 모델 == "GPT-4o" :
        if interaction.user.id != developer : 
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다.\n\n대신 다른 모델(GPT-4.1 nano)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return
        # 객체 생성
        llm = ChatOpenAI(
            temperature=1.0,  # 창의성 (0.0 ~ 2.0)
            model_name="gpt-4o",  # 모델명
        )

        # 질의내용
        question = 프롬프트
        result = await llm.invoke(question)
        result = result.content
    elif 모델 == "GPT-4.1 nano":
        if False : 
        # if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in ai_cooldowns:
                elapsed = (now - ai_cooldowns[user_id]).total_seconds()
                if elapsed < COOLDOWN_DURATION:
                    remaining = int(COOLDOWN_DURATION - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            ai_cooldowns[user_id] = now
        # 객체 생성
        llm = ChatOpenAI(
            temperature=1.0,  # 창의성 (0.0 ~ 2.0)
            model_name="gpt-4.1-nano",  # 모델명
        )

        # 질의내용
        question = 프롬프트
        result = llm.invoke(question)
        result = result.content
    elif 모델 == "GPT-3.5":
        if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in ai_cooldowns:
                elapsed = (now - ai_cooldowns[user_id]).total_seconds()
                if elapsed < COOLDOWN_DURATION:
                    remaining = int(COOLDOWN_DURATION - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            ai_cooldowns[user_id] = now
        # 객체 생성
        llm = ChatOpenAI(
            temperature=1.0,  # 창의성 (0.0 ~ 2.0)
            model_name="gpt-3.5-turbo-0125",  # 모델명
        )

        # 질의내용
        question = 프롬프트
        result = llm.invoke(question)
        result = result.content
    elif 모델 == "GPT-4.1":
        if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in gpt_4_1_cooldowns:
                elapsed = (now - gpt_4_1_cooldowns[user_id]).total_seconds()
                if elapsed < gpt_4_1_cooldowns_d:
                    remaining = int(gpt_4_1_cooldowns_d - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(GPT-4.1 mini)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            ai_cooldowns[user_id] = now
        # 객체 생성
        llm = ChatOpenAI(
            temperature=1.0,  # 창의성 (0.0 ~ 2.0)
            model_name="gpt-4.1",  # 모델명
        )

        # 질의내용
        question = 프롬프트
        result = llm.invoke(question)
        result = result.content
    elif 모델 == "GPT-4.1 mini":
        if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in ai_cooldowns:
                elapsed = (now - ai_cooldowns[user_id]).total_seconds()
                if elapsed < COOLDOWN_DURATION:
                    remaining = int(COOLDOWN_DURATION - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            ai_cooldowns[user_id] = now
        # 객체 생성
        llm = ChatOpenAI(
            temperature=1.0,  # 창의성 (0.0 ~ 2.0)
            model_name="gpt-4.1-mini",  # 모델명
        )

        # 질의내용
        question = 프롬프트
        result = llm.invoke(question)
        result = result.content
    elif 모델 == "o4-mini" :
        if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in o3_cooldowns:
                elapsed = (now - o3_cooldowns[user_id]).total_seconds()
                if elapsed < o3_cooldowns_d:
                    remaining = int(o3_cooldowns_d - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(GPT-4.1)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            o3_cooldowns[user_id] = now
        response = gpt_client.responses.create(
            model="o4-mini",
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "user", 
                    "content": 프롬프트
                }
            ]
        )

        result = response.output_text
    elif 모델 == "o3-mini" :
        if interaction.guild.id != using_server :
            embed = discord.Embed(
                title="오류",
                description="이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 서버로 설정되어 있지 않습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if interaction.user.id != developer :
            if len(프롬프트) > 1000:
                embed = discord.Embed(
                    title="오류",
                    description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=False)
                return
            user_id = interaction.user.id
            now = datetime.utcnow()

            # 마지막 사용 시간이 존재하면 남은 쿨타임 계산
            if user_id in o3_cooldowns:
                elapsed = (now - o3_cooldowns[user_id]).total_seconds()
                if elapsed < o3_cooldowns_d:
                    remaining = int(o3_cooldowns_d - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    embed = discord.Embed(
                        title="오류",
                        description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {minutes * 60 + seconds}초\n\n대신 다른 모델(GPT-4.1)을 사용해 볼 수 있습니다.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)
                    return

            # 쿨타임 없음 → 명령어 실행
            o3_cooldowns[user_id] = now
        response = gpt_client.responses.create(
            model="o3-mini",
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "user", 
                    "content": 프롬프트
                }
            ]
        )

        result = response.output_text
    else :
        embed = discord.Embed(
            title="오류",
            description="모델 이름이 올바르지 않습니다. 지원되지 않는 모델일 수 있습니다.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=False)
        return
    embed = discord.Embed(
        title = f"성공",
        # description = f"Gemini 1.5 Flash의 답변은 다음과 같습니다: \n\n{to_markdown(response.text)}",
        description = f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n모델: {모델}\n입력: {프롬프트}\n출력: {result}",
        color = int("a5f0ff", 16)
    )
    await interaction.followup.send(embed = embed)