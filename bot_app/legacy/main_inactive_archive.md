# main.py 비활성 legacy 아카이브

이 문서는 `Phase 7` 정리 과정에서 `main.py`에서 제거한 대형 비활성 legacy 블록을 보관한다.

- 목적: 실행 경로에서는 제거하되, 구현 참고 가치는 남기기
- 기준: 삼중따옴표로 비활성화되어 있었고 현재 runtime AST에는 포함되지 않던 코드

## 1. 구형 AI 제재 판정 분기 (`elif 버전 == "v2"`)

원본 위치: `main.py` 중 `/판사` 명령 내부의 비활성 분기

```python
    elif 버전 == "v2" : 
        프롬프트 = """
아래 디스코드 서버 대화에서 제시된 메시지들에서 유저별로 규정 위반 행위를 한 메시지를 찾고, 아래 양식에 맞게 정리하세요. (단, 규정 위반 메시지가 하나도 없을시 문자열 답변에 'None'만 딱 작성하세요) 양식에 없는 말은 만들어내지 마세요.

1. 저희 디스코드 서버는 욕설/비속어/반말은 상대방이 불쾌하지만 않다면 허용입니다. 단, 성적인 대화, 정치 드립, 민감한 주제에 대한 대화 등은 금지됩니다. 또한 위키 관련 대화도 금지입니다.
2. 분위기를 흐리는 행위도 금지입니다.

유저 ID, 위반 메시지 내용, 위반 사유
유저 ID, 위반 메시지 내용, 위반 사유
유저 ID, 위반 메시지 내용, 위반 사유
... (쭉 나열)
        """
        status, until, reason = is_blocked(interaction.user)
        
        # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
        if status:
            embed = discord.Embed(
                title="오류",
                description=f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다. {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed = embed)
            return
        user_id = interaction.user.id
        current_time = time.time()

        # 쿨다운 확인
        if user_id not in bot.cooldowns:
            bot.cooldowns[user_id] = 0

        if current_time - bot.cooldowns[user_id] < 1 * 60:  # 60초 = 1분
            embed = discord.Embed(
                title=f"오류", # name
                description=f"이 명령어는 1분마다 한 번 사용 가능합니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return

        # owner_id 역할 확인
        if user_id == developer:
            bot.cooldowns[user_id] = current_time

        try:
            # 메시지 링크에서 채널 ID와 메시지 ID 추출
            start_channel_id, start_message_id = map(int, 시작.split("/")[-2:])
            end_channel_id = None
            end_message_id = None

            if 끝:
                end_channel_id, end_message_id = map(int, 끝.split("/")[-2:])

            # 채널 가져오기
            channel = bot.get_channel(start_channel_id)
            if not channel:
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"channel의 값이 올바르지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            if channel.id != interaction.channel.id:
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"channel의 값이 올바르지 않습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 불러오기
            messages = await fetch_messages(channel, start_message_id, end_message_id)
            if not messages:
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"messages의 값이 올바르지 않습니다. 이 오류는 지정된 범위의 메시지들의 개수가 0개일 때 표시됩니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # 메시지 내용을 합치기
            text_to_summarize = "\n\n".join(f"{msg.author.id}: {msg.content}" for msg in reversed(messages))
            text_to_summarize = f"{프롬프트}\n\n{text_to_summarize}"

            # Gemini API 호출
            response = two_model.generate_content(text_to_summarize)

            response = response.text

            print(response)

            if response == "None" :
                embed = discord.Embed(
                    title="완료",
                    description="AI 판단 결과, 규정 위반 메시지가 없습니다.",
                    color=int("a5f0ff", 16)
                )
                await interaction.followup.send(embed=embed)
                return

            user_id_list = []

            ai_list = response.split("\n")
            for i in range(len(response)) :
                ai_list[i] = ai_list[i].split(", ")
                user_id_list.append(ai_list[i][0])

            blockhistory = {}

            for i in ai_list : 
                c.execute(
                    "SELECT type, reason, addinfo FROM blockhistory WHERE user_id = ? AND server_id = ? ORDER BY id DESC", 
                    (i, interaction.guild.id)
                )

                # 모든 결과 가져오기
                results = c.fetchall()

                # 마지막 7개 행 추출 (최신순 정렬이므로 앞에서부터 7개)
                last_7 = results[:7]
                if len(last_7) == 0 :
                    blockhistory[i] = "차단 기록 없음"
                    continue
                
                blockhistory[i] = ""
                for j in last_7 : 
                    if j[0] == "timeout" : 
                        blockhistory[i] += f"- {j[2]}초 동안 타임아웃 (사유: {j[1]})\n"
                    elif j[0] == "untimeout" : 
                        blockhistory[i] += f"- 타임아웃 해제 (사유: {j[1]})\n"
                    elif j[0] == "ban" : 
                        blockhistory[i] += f"- 차단 (사유: {j[1]})\n"
                    elif j[0] == "unban" :
                        blockhistory[i] += f"- 차단 해제 (사유: {j[1]})\n"
                    elif j[0] == "kick" : 
                        blockhistory[i] += f"- 추방 (사유: {j[1]})\n"
                    elif j[0] == "warn" :
                        blockhistory[i] += f"- 경고 {j[2]}개 부여 (사유: {j[1]})\n"
                    elif j[0] == "unwarn" :
                        blockhistory[i] += f"- 경고 {j[2]}개 차감 (사유: {j[1]})\n"
            
            프롬프트2 = """
아래는 어느 디스코드 서버 대화에서 규정 위반으로 판단된 메시지들입니다. 각 메시지들을 보고 어느 유저를 얼마큼 제재해야 하는지 이전 제재 기록을 보고, 답변 양식에 맞춰 적어주세요. 답변 양식에 없는 쓸데없는 말 추가 금지.

제재 수위는 다음 중 하나입니다: 제재하지 아니함, 주의, 경고, 타임아웃(이 경우 1초 ~ 120시간 사이의 시간으로 기간도 작성), 차단. (차단은 행위가 매우매우 지속적일 때만)

1. 저희 디스코드 서버는 욕설/비속어/반말은 상대방이 불쾌하지만 않다면 허용입니다. 단, 성적인 대화, 정치 드립, 민감한 주제에 대한 대화 등은 금지됩니다. 또한 위키 관련 대화도 금지입니다.
2. 대화 주제를 고려하지 않고 자기 할말만 하는 등 분위기를 흐리는 행위도 금지입니다.

답변 양식: 
유저id, 제재 수위 (사유)
유저id, 제재 수위 (사유)
유저id, 제재 수위 (사유)
... (더 있으면 쭉 작성.)

규정 위반 메시지들: 
            """

            프롬프트2 += response

            blockhistory_text = ""

            for i, j in blockhistory.items() :
                blockhistory_text += f"유저 {i}의 이전 제재 내역\n{j}\n\n"

            프롬프트2 +="\n\n이전 제재 내역: \n\n" + blockhistory_text

            response = two_model.generate_content(text_to_summarize)

            response = response.text

            response = response.split("\n")

            for i in len(response) : 
                response[i] = response[i].split(", ")
                temp = await bot.get_user(response[i][0])
                response[i][0] = "- " + temp.display_name
            
            for i in response : 
                i = ", ".join(i)
            
            response = "\n".join(response)

            # 응답 전송
            embed = discord.Embed(
                title="성공",
                description=f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\nGemini 2.0 Flash의 답변은 다음과 같습니다: \n\n{response.text}",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title=f"오류", # name
                description=f"오류가 발생했습니다.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
```

## 2. 구형 관리/익명채팅/호감도 명령 묶음

원본 위치: `main.py` 중 `유입경로확인` 뒤의 비활성 명령 블록

```python
# /권한회수 명령어 정의
@bot.tree.command(name="권한회수", description="권한 남용 사태가 발생한 경우 특정 사용자의 관리자 권한을 회수합니다.")
@app_commands.describe(member = "권한을 회수할 사용자")
async def revoke_permissions(interaction: discord.Interaction, member: discord.User):
    
    if interaction.guild.id != using_server :
        embed = discord.Embed(
            title="오류",
            description="이 기능은 아직 여러 서버들에서 지원되지 않습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return
    status, until, reason = is_blocked(interaction.user)
    
    # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
    if status:
        msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
        await interaction.response.send_message(msg)
        return
    # 명령어 호출자의 권한 확인
    if interaction.user.id != 1305492487137267722 : 
        if interaction.user.id not in admin:
            embed = discord.Embed(
                title=f"오류", # name
                description=f"권한이 부족합니다. 다음 권한이 필요합니다: `관리자`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed = embed, ephemeral=False)
            return
        if interaction.user.id not in super_admin and member.id in super_admin :
            embed = discord.Embed(
                title=f"오류", # name
                description=f"관리자가 최고 관리자에게 이 명령어를 사용할 수 없습니다.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed = embed, ephemeral=False)
            return
    await interaction.response.defer()

    # 역할 제거
    roles_to_remove = []
    guild = bot.get_guild(1320303102703702037)
    member = await guild.fetch_member(member.id)
    for role_id in [super_admin_id, admin_id]:
        role = guild.get_role(role_id)
        if role in member.roles:
            roles_to_remove.append(role)
    try : 
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason=f"사용자 {interaction.user.name} ({interaction.user.id}) 의 /권한회수 명령어 사용")
            embed = discord.Embed(
                title=f"성공", # name
                description=f"{member.mention} 사용자의 관리자 및 최고 관리자 역할을 성공적으로 회수했습니다.",
                color=int("a5f0ff", 16)
            )
            await interaction.followup.send(embed = embed)
    except Exception as e :
        embed = discord.Embed(
            title=f"오류", # name
            description=f"오류",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed = embed)

@bot.tree.command(name = "익명채팅설정", description = "익명 채팅을 사용 여부와 로그 채널을 설정합니다.")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(사용여부 = "기능을 사용할지 여부", 로그채널 = "익명 채팅 로그 채널 (로그 채널을 비활성화하려는 경우 비워두기)")
@app_commands.choices(
    사용여부 = [
        app_commands.Choice(name = "활성화", value = "True"),
        app_commands.Choice(name = "비활성화", value = "False"),
    ]
)
async def update_anonymous_setting_command(interaction: discord.Interaction, 사용여부: str, 로그채널: discord.TextChannel = None) : 
    await interaction.response.defer()

    status, until, reason = is_blocked(interaction.user)
    
    # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
    if status:
        msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
        await interaction.followup.send(msg)
        return
    
    if 사용여부 == "True" : 
        사용여부 = True
    else : 
        사용여부 = False
    
    if 로그채널 is not None : 
        로그채널 = 로그채널.id
    
    update_anonymous_setting(interaction.guild.id, 사용여부, 로그채널)

    embed = discord.Embed(
        title = "완료",
        description = "익명 채팅 옵션이 성공적으로 저장되었습니다.",
        color = int("a5f0ff", 16),
    )
    await interaction.followup.send(embed = embed)

@bot.tree.command(name = "익명채팅", description = "익명으로 메시지를 보냅니다. (단, 비공개 로그 채널에 로그가 전송됩니다.)")
@app_commands.describe(내용 = "익명으로 보낼 채팅의 내용")
async def chat1(interaction: discord.Interaction, 내용: str):
    channel = interaction.channel_id
    user = interaction.user.id
    await interaction.response.defer(ephemeral = True)

    onoff, log_channel = get_anonymous_setting(interaction.guild.id)

    if not onoff : 
        embed = discord.Embed(
            title = "오류",
            description = "이 서버에서는 익명 채팅 기능이 비활성화되어 있습니다.",
            color = discord.Color.red()
        )
        await interaction.followup.send(embed = embed)
        return

    status, until, reason = is_blocked(interaction.user)
    
    # 차단중이면 차단 사유와 종료 날짜를, 아니면 차단 상태가 아님을 알려줌
    if status:
        msg = f"**[오류!]** {interaction.user.id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
        await interaction.followup.send(msg)
        return

    spam = False

    if "<@" in 내용 or "@here" in 내용 or "@everyone" in 내용 or "discord.gg/" in 내용 or "discord.com/invite/" in 내용 :
        await interaction.followup.send("**[오류!]** 익명채팅에서 특정 사용자 또는 역할을 멘션하거나 서버 링크를 첨부할 수 없습니다.")
        return
    
    if interaction.guild.id == using_server : 
        global automod_keyword
        global automod_keyword2
        global automod_keyword3
        global automod_keyword4
        global automod_keyword5
        global automod_keyword6
        global automod_keyword7
        global automod_keyword8
        global automod_keyword9
        global automod_keyword10
        global raid_keyword1
        
        message_content = re.sub(r"[^가-힣a-zA-Z]", "", 내용)

        for i in automod_keyword + automod_keyword2 + automod_keyword3 + automod_keyword4 + automod_keyword5 + automod_keyword6 + automod_keyword7 + automod_keyword8 + automod_keyword9 + automod_keyword10 :
            if i in message_content :
                embed = discord.Embed(
                    title=f"오류", # name
                    description=f"automod_keyword",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed = embed)
                return

    content = 내용.split("\\n")
    content = "\n".join(content)

    embed = discord.Embed(
        title=f"익명 채팅", # name
        description=f"누군가가 다음과 같은 내용의 메시지를 익명으로 보냈습니다: \n\n{content}\n-# 이 메시지는 /익명채팅 명령어를 통해 전송되었습니다.",
        color=int("a5f0ff", 16)
    )
    await interaction.channel.send(embed = embed)

    if log_channel is not None : 
        log = bot.get_channel(log_channel)

        embed = discord.Embed(
            title=f"익명 채팅", # name
            description=f"<@{user}> 사용자가 <#{channel}>에 다음과 같은 내용의 메시지를 익명으로 보냈습니다: \n\n{content}",
            color=int("a5f0ff", 16)
        )
        await log.send(embed = embed)
    embed = discord.Embed(
        title=f"성공", # name
        description=f"작업이 성공적으로 처리되었습니다.",
        color=int("a5f0ff", 16)
    )
    await interaction.followup.send(embed = embed)

@bot.tree.command(name = "호감도확인", description = "특정 사용자의 호감도를 확인합니다.")
@app_commands.describe(사용자 = "호감도를 확인할 사용자")
async def check_likeability_command(interaction: discord.Interaction, 사용자: discord.User = None) :
    await run_check_likeability_slash_command(
        interaction,
        target_user=사용자,
    )

@bot.tree.command(name = "호감도추가", description = "특정 사용자의 호감도를 수정합니다.")
@app_commands.describe(사용자 = "호감도를 확인할 사용자", 호감도 = "값")
async def add_likeability_command(interaction: discord.Interaction, 사용자: discord.User, 호감도: int) :
    await run_add_likeability_slash_command(
        interaction,
        target_user=사용자,
        amount=호감도,
        context={
            "developer": developer,
        },
    )

@bot.tree.command(name = "임베드출력", description = "임베드 출력")
@app_commands.describe(색상 = "임베드 색상 HEX 코드 (# 제외하고 입력)")
async def embed(interaction: discord.Interaction, 제목: str, 내용: str, 색상: str = "a5f0ff") :
    await run_embed_output_slash_command(
        interaction,
        title_text=제목,
        body_text=내용,
        color_hex=색상,
        context={
            "is_blocked": is_blocked,
            "using_server": using_server,
            "spam_whitelist_role_ids": tuple(spamming_filter_whitelist),
            "raid_keywords": tuple(raid_keyword1),
            "automod_keywords": tuple(
                automod_keyword
                + automod_keyword2
                + automod_keyword3
                + automod_keyword4
                + automod_keyword5
                + automod_keyword6
                + automod_keyword7
                + automod_keyword8
                + automod_keyword9
                + automod_keyword10
            ),
        },
    )

@bot.tree.command(name = "링크검사", description = "특정 링크가 악성 링크인지 여부를 검사합니다.")
@app_commands.describe(링크 = "검사할 링크", 세부정보 = "검사 결과 출력 방식")
@app_commands.choices(세부정보 = [app_commands.Choice(name = "간단", value = "simple"), app_commands.Choice(name = "상세", value = "detail")])
async def link_check(interaction: discord.Interaction, 링크: str, 세부정보: str = "detail"):
    await run_link_check_slash_command(
        interaction,
        link=링크,
        detail_level=세부정보,
        context={
            "is_blocked": is_blocked,
            "scan_url": scan_url,
        },
    )

@bot.tree.command(name="제재내역수동삭제", description = "개발 명령")
async def 제재내역수동삭제(interaction: discord.Interaction, id: int):
    await run_delete_blockhistory_entry_slash_command(
        interaction,
        entry_id=id,
        context={
            "developer": developer,
        },
    )

# add_blockhistory(user_id, admin_id, reason, blocktype, addinfo)
@bot.tree.command(name="제재내역수동추가", description="개발 명령")
@app_commands.describe(추가정보="경고의 경우, 경고 개수. 타임아웃의 경우 타임아웃 기간 (초)")
async def 제재내역수동추가(interaction: discord.Interaction, 유저: discord.User, 관리자: discord.User, 사유: str, 종류: str, 추가정보: int) :
    await run_add_blockhistory_entry_slash_command(
        interaction,
        target_user=유저,
        admin_user=관리자,
        reason_text=사유,
        type_label=종류,
        extra_value=추가정보,
        context={
            "developer": developer,
        },
    )
```
