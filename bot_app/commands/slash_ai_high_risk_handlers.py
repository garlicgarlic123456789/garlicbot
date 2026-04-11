from __future__ import annotations

import ast
import asyncio
import json
import re
import sqlite3
import time
from datetime import datetime
from typing import Any, Mapping

import discord
from langchain_openai import ChatOpenAI

from bot_app.services.ai_high_risk_service import build_mining_help_response
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, SlashCommandResult


def _build_error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="오류", description=description, color=discord.Color.red())


def _tracked_result(
    context: Mapping[str, Any],
    *,
    status: str,
    reason_code: str | None = None,
) -> ErrorTrackedSlashCommandResult:
    return ErrorTrackedSlashCommandResult(
        status=status,
        error_count=_get_error_count(context),
        reason_code=reason_code,
    )


def _get_error_state(context: Mapping[str, Any]) -> dict[str, int]:
    if isinstance(context, dict):
        error_state = context.get("error_state")
        if isinstance(error_state, dict) and "count" in error_state:
            return error_state
        context["error_state"] = {"count": 0}
        return context["error_state"]

    error_state = context.get("error_state")
    if isinstance(error_state, dict) and "count" in error_state:
        return error_state
    return {"count": 0}


def _get_error_count(context: Mapping[str, Any]) -> int:
    return int(_get_error_state(context).get("count", 0))


def _increment_error_count(context: Mapping[str, Any]) -> int:
    error_state = _get_error_state(context)
    error_state["count"] = int(error_state.get("count", 0)) + 1
    return error_state["count"]


async def _send_internal_error(
    interaction: discord.Interaction,
    *,
    context: Mapping[str, Any],
    reason_code: str,
    exc: Exception,
) -> ErrorTrackedSlashCommandResult:
    current_error = _get_error_count(context)
    print(f"오류 #{current_error}: {exc}")
    embed = _build_error_embed(f"오류 #{current_error}\n\n마늘봇 서포트 서버에 문의하시기 바랍니다.")
    await interaction.followup.send(embed=embed)
    _increment_error_count(context)
    return _tracked_result(context, status="failed", reason_code=reason_code)


def _build_ai_blocked_embed(user_id: int, *, reason: str, until: str | None) -> discord.Embed:
    return _build_error_embed(
        f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다. {user_id}님은 `{reason}` 사유로 {until}까지 차단 중입니다."
    )


async def run_same_person_check_slash_command(
    interaction: discord.Interaction,
    *,
    first_user: discord.User,
    second_user: discord.User,
    context: Mapping[str, Any],
) -> ErrorTrackedSlashCommandResult:
    """Execute `/동일인여부확인` from bot_app instead of delegating back into main.py."""
    if interaction.user.id != context["developer"]:
        await interaction.response.send_message("권한이 부족합니다. 다음 권한이 필요합니다: `개발자`")
        return _tracked_result(context, status="rejected", reason_code="same_person_missing_developer_permission")

    await interaction.response.send_message("처리 중입니다.")
    message = await interaction.original_response()
    user1_message, user2_message = await context["load_user_messages"](
        context["bot"],
        first_user.id,
        second_user.id,
        interaction.guild.id,
    )

    print(user1_message, user2_message)

    if len(user1_message) < 15 or len(user2_message) < 15:
        embed = discord.Embed(
            title="오류",
            description="두 유저의 말투를 비교하여 동일인 여부를 판단하기 위한 메시지가 충분하지 않습니다.",
            color=discord.Color.red(),
        )
        await message.reply(embed=embed, mention_author=False)
        return _tracked_result(context, status="rejected", reason_code="same_person_not_enough_messages")

    prompt = (
        f"다음은 유저 '{first_user.display_name}'와(과) 유저 '{second_user.display_name}'의 메시지입니다.\n\n"
        "대화를 기반으로 두 유저가 동일인일 가능성을 0~100까지의 수 중 하나(높은 숫자는 높은 확률을 의미)로 표현"
        "(관심 분야, 말투, 종결어미, 말하는 특징이나 방식 등등)하고, 그 근거를 글머리 기호 목록으로 작성하시오.\n\n"
        "답변 양식은 다음과 같으며, 근거는 글머리 기호 목록으로 동일인일 가능성을 뒷받침하는 근거, 동일인이 아닐 가능성을 뒷받침하는 근거, 최종 결론을 작성합니다. "
        "답변 길이는 2000자 이내여야 합니다: \n\n동일인 가능성: \n근거: \n\n"
        f"유저 {first_user.display_name}의 메시지: \n\n{user1_message}\n\n"
        f"유저 {second_user.display_name}의 메시지: \n\n{user2_message}"
    )

    try:
        response = context["two_five_lite_model"].generate_content(prompt)
        embed = discord.Embed(
            title="성공",
            description=f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\nGemini 2.0 Flash의 답변은 다음과 같습니다: \n\n{response.text}",
            color=int("a5f0ff", 16),
        )
        await message.reply(embed=embed, mention_author=False)
        return _tracked_result(context, status="completed", reason_code="same_person_completed")
    except Exception as exc:
        return await _send_internal_error(
            interaction,
            context=context,
            reason_code="same_person_error",
            exc=exc,
        )


async def _load_judge_messages(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    context: Mapping[str, Any],
) -> tuple[list[Any] | None, ErrorTrackedSlashCommandResult | None]:
    try:
        start_channel_id, start_message_id = map(int, start_message_link.split("/")[-2:])
        end_message_id = None
        if end_message_link:
            _, end_message_id = map(int, end_message_link.split("/")[-2:])

        channel = context["bot"].get_channel(start_channel_id)
        if not channel:
            await interaction.followup.send(embed=_build_error_embed("channel의 값이 올바르지 않습니다."))
            return None, _tracked_result(context, status="rejected", reason_code="judge_invalid_channel")

        if channel.id != interaction.channel.id:
            await interaction.followup.send(embed=_build_error_embed("channel의 값이 올바르지 않습니다."))
            return None, _tracked_result(context, status="rejected", reason_code="judge_invalid_channel")

        try:
            messages = await context["fetch_messages"](channel, start_message_id, end_message_id)
        except discord.Forbidden:
            await interaction.followup.send(
                embed=_build_error_embed(
                    "봇에게 권한이 부족합니다. 아래 사항을 확인해 주세요.\n\n- 봇에게 `채널 보기` 권한이 있는지 확인해 주세요.\n- 봇에게 `메시지 기록 보기` 권한이 있는지 확인해 주세요.\n- 봇이 해당 채널을 볼 수 있는지 확인해 주세요."
                )
            )
            return None, _tracked_result(context, status="rejected", reason_code="judge_missing_channel_permission")
        except Exception as exc:
            return None, await _send_internal_error(
                interaction,
                context=context,
                reason_code="judge_fetch_messages_error",
                exc=exc,
            )

        if not messages:
            await interaction.followup.send(
                embed=_build_error_embed(
                    "messages의 값이 올바르지 않습니다. 이 오류는 지정된 범위의 메시지들의 개수가 0개일 때 표시됩니다."
                )
            )
            return None, _tracked_result(context, status="rejected", reason_code="judge_empty_messages")

        return messages, None
    except Exception as exc:
        return None, await _send_internal_error(
            interaction,
            context=context,
            reason_code="judge_prepare_messages_error",
            exc=exc,
        )


def _resolve_rule_context(rule_lookup_result) -> tuple[bool, str, str]:
    rule_exists = True
    if rule_lookup_result[0]:
        rule = rule_lookup_result[1]
        rule_guide = rule_lookup_result[2]
    else:
        rule = None
        rule_guide = None
        rule_exists = False

    if rule is None:
        rule = "None"
        rule_exists = False
    if rule_guide is None:
        rule_guide = "None"
        rule_exists = False
    return rule_exists, rule, rule_guide


def _parse_first_stage_output(output: Any):
    if isinstance(output, str):
        try:
            parsed_output = json.loads(output)
        except json.JSONDecodeError:
            parsed_output = ast.literal_eval(output)
    else:
        parsed_output = output

    if isinstance(parsed_output, list) and parsed_output and isinstance(parsed_output[0], list):
        parsed_output = parsed_output[0]
    return parsed_output


def _parse_second_stage_output(output: str):
    cleaned_output = output.strip()
    cleaned_output = re.sub(r",(\s*[}\]])", r"\1", cleaned_output)

    if cleaned_output.startswith("{") and cleaned_output.endswith("}"):
        objects = re.findall(r"\{[^{}]*\}", cleaned_output)
        cleaned_output = "[" + ",".join(objects) + "]"
    elif not cleaned_output.startswith("["):
        cleaned_output = "[" + cleaned_output + "]"

    return json.loads(cleaned_output)


def _load_recent_blockhistory(*, server_id: int, user_ids: list[int]) -> dict[int, str]:
    blockhistory: dict[int, str] = {}
    for user_id in user_ids:
        conn = sqlite3.connect("garlicbot.db", isolation_level=None)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT type, reason, addinfo FROM blockhistory WHERE user_id = ? AND server_id = ? ORDER BY id DESC",
            (user_id, server_id),
        )
        results = cursor.fetchall()
        recent_block = results[:15]
        if not recent_block:
            blockhistory[user_id] = "최근 제재 내역 없음"
            conn.close()
            continue

        parts: list[str] = []
        for block_type, reason, addinfo in recent_block:
            if block_type == "timeout":
                parts.append(f"{addinfo}초 동안 타임아웃. 사유: {reason}")
            elif block_type == "untimeout":
                parts.append(f"타임아웃 해제. 사유: {reason}")
            elif block_type == "warn":
                parts.append(f"경고 {addinfo}개 부여. 사유: {reason}")
            elif block_type == "unwarn":
                parts.append(f"경고 {addinfo}개 차감. 사유: {reason}")
            elif block_type == "kick":
                parts.append(f"서버에서 추방. 사유: {reason}")
            elif block_type == "ban":
                parts.append(f"서버에서 차단. 사유: {reason}")
            elif block_type == "unban":
                parts.append(f"서버에서 차단 해제. 사유: {reason}")

        blockhistory[user_id] = "\n".join(parts) + ("\n" if parts else "")
        conn.close()
    return blockhistory


async def _run_judge_v4(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    context: Mapping[str, Any],
) -> ErrorTrackedSlashCommandResult:
    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(embed=_build_ai_blocked_embed(interaction.user.id, reason=reason, until=until))
        return _tracked_result(context, status="rejected", reason_code="judge_blocked_user")

    rule_exists, rule, rule_guide = _resolve_rule_context(await context["get_server_rules"](interaction.guild.id))

    user_id = interaction.user.id
    current_time = time.time()
    if user_id not in context["bot"].cooldowns:
        context["bot"].cooldowns[user_id] = 0
    if current_time - context["bot"].cooldowns[user_id] < 60 and interaction.user.id != context["developer"]:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 1분마다 한 번 사용 가능합니다."))
        return _tracked_result(context, status="rejected", reason_code="judge_cooldown")
    if user_id == context["developer"]:
        context["bot"].cooldowns[user_id] = current_time

    messages, rejected_result = await _load_judge_messages(
        interaction,
        start_message_link=start_message_link,
        end_message_link=end_message_link,
        context=context,
    )
    if rejected_result is not None:
        return rejected_result
    assert messages is not None

    if len(messages) > 1000 and interaction.user.id != context["developer"]:
        await interaction.followup.send(embed=_build_error_embed("판단할 메시지 개수가 너무 많습니다."))
        return _tracked_result(context, status="rejected", reason_code="judge_too_many_messages")

    messages_list = [
        {
            "message_author_id": message.author.id,
            "message_id": message.id,
            "message_content": message.content,
        }
        for message in reversed(messages)
    ]

    chain = context["create_judge4_chain1"](messages_list, rule, rule_guide)
    output = await asyncio.to_thread(chain.invoke, {"messages": messages_list, "rule": rule, "rule_guide": rule_guide})
    print(output)
    if not output or output.strip() == "":
        await interaction.followup.send(embed=discord.Embed(title="완료", description="규정 위반 메시지가 없습니다.", color=int("a5f0ff", 16)))
        return _tracked_result(context, status="completed", reason_code="judge_no_violation")

    try:
        output_dict = _parse_first_stage_output(output)
    except Exception as exc:
        return await _send_internal_error(interaction, context=context, reason_code="judge_first_parse_error", exc=exc)

    if not output_dict:
        if not rule_exists:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[주의!]** `/서버규정설정`을 이용하여 설정된 규정이 없습니다. 규정이 설정되어 있지 않아 정확한 판단이 어렵습니다. 아래 판결은 일반적으로 디스코드 서버에 적용되는 규정을 바탕으로 합니다.\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=discord.Color.yellow(),
                )
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=int("a5f0ff", 16),
                )
            )
        return _tracked_result(context, status="completed", reason_code="judge_no_violation")

    user_ids = [int(item["message_author_id"]) for item in output_dict]
    blockhistory = _load_recent_blockhistory(server_id=interaction.guild.id, user_ids=user_ids)
    print(blockhistory)

    chain = context["create_judge4_chain2"](messages_list, rule, rule_guide)
    output = await asyncio.to_thread(
        chain.invoke,
        {"messages": output_dict, "before_blockhistory": blockhistory, "rule": rule, "rule_guide": rule_guide},
    )
    print(output)
    if not output or output.strip() == "":
        if not rule_exists:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[주의!]** `/서버규정설정`을 이용하여 설정된 규정이 없습니다. 규정이 설정되어 있지 않아 정확한 판단이 어렵습니다. 아래 판결은 일반적으로 디스코드 서버에 적용되는 규정을 바탕으로 합니다.\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=discord.Color.yellow(),
                )
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=int("a5f0ff", 16),
                )
            )
        return _tracked_result(context, status="completed", reason_code="judge_no_violation")

    try:
        output_dict = _parse_second_stage_output(output)
    except json.JSONDecodeError as exc:
        print(f"JSON 파싱 오류: {exc}")
        print(f"원본 출력: {output}")
        return await _send_internal_error(interaction, context=context, reason_code="judge_second_parse_error", exc=exc)

    description = ""
    for item in output_dict:
        description += (
            f"- <@{item['message_author_id']}>: {item['punish']} "
            f"(사유: {item['reason']} | https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/{item['message_id']})\n"
        )
    print(description)

    if not rule_exists:
        await interaction.followup.send(
            embed=discord.Embed(
                title="완료",
                description=f"AI 판사의 판결은 다음과 같습니다. \n\n**[주의!]** `/서버규정설정`을 이용하여 설정된 규정이 없습니다. 규정이 설정되어 있지 않아 정확한 판단이 어렵습니다. 아래 판결은 일반적으로 디스코드 서버에 적용되는 규정을 바탕으로 합니다.\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n{description}",
                color=discord.Color.yellow(),
            )
        )
    else:
        await interaction.followup.send(
            embed=discord.Embed(
                title="성공",
                description=f"AI 판사의 판결은 다음과 같습니다. \n\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n{description}",
                color=int("a5f0ff", 16),
            )
        )
    return _tracked_result(context, status="completed", reason_code="judge_completed")


async def _run_judge_v3(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    context: Mapping[str, Any],
) -> ErrorTrackedSlashCommandResult:
    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(embed=_build_ai_blocked_embed(interaction.user.id, reason=reason, until=until))
        return _tracked_result(context, status="rejected", reason_code="judge_blocked_user")

    rule_exists, rule, rule_guide = _resolve_rule_context(await context["get_server_rules"](interaction.guild.id))
    user_id = interaction.user.id
    current_time = time.time()
    if user_id not in context["bot"].cooldowns:
        context["bot"].cooldowns[user_id] = 0
    if current_time - context["bot"].cooldowns[user_id] < 60:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 1분마다 한 번 사용 가능합니다."))
        return _tracked_result(context, status="rejected", reason_code="judge_cooldown")
    if user_id == context["developer"]:
        context["bot"].cooldowns[user_id] = current_time

    messages, rejected_result = await _load_judge_messages(
        interaction,
        start_message_link=start_message_link,
        end_message_link=end_message_link,
        context=context,
    )
    if rejected_result is not None:
        return rejected_result
    assert messages is not None

    if len(messages) > 1000 and interaction.user.id != context["developer"]:
        await interaction.followup.send(embed=_build_error_embed("판단할 메시지 개수가 너무 많습니다."))
        return _tracked_result(context, status="rejected", reason_code="judge_too_many_messages")

    messages_text = "\n\n".join(f"{message.author.id}: {message.content}" for message in reversed(messages))
    chain = context["create_chain1"](messages_text, rule, rule_guide)
    output = await asyncio.to_thread(chain.invoke, {"messages": messages_text, "rule": rule, "rule_guide": rule_guide})
    print(output)
    if not output or output.strip() == "":
        await interaction.followup.send(embed=discord.Embed(title="완료", description="규정 위반 메시지가 없습니다.", color=int("a5f0ff", 16)))
        return _tracked_result(context, status="completed", reason_code="judge_no_violation")

    try:
        output_dict = _parse_first_stage_output(output)
    except Exception as exc:
        return await _send_internal_error(interaction, context=context, reason_code="judge_first_parse_error", exc=exc)

    if not output_dict:
        if not rule_exists:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[주의!]** `/서버규정설정`을 이용하여 설정된 규정이 없습니다. 규정이 설정되어 있지 않아 정확한 판단이 어렵습니다. 아래 판결은 일반적으로 디스코드 서버에 적용되는 규정을 바탕으로 합니다.\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=discord.Color.yellow(),
                )
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=int("a5f0ff", 16),
                )
            )
        return _tracked_result(context, status="completed", reason_code="judge_no_violation")

    user_ids = [int(item["user_id"]) for item in output_dict]
    blockhistory = _load_recent_blockhistory(server_id=interaction.guild.id, user_ids=user_ids)
    print(blockhistory)

    chain = context["create_chain2"](messages_text, rule, rule_guide)
    output = await asyncio.to_thread(
        chain.invoke,
        {"messages": output_dict, "before_blockhistory": blockhistory, "rule": rule, "rule_guide": rule_guide},
    )
    print(output)
    if not output or output.strip() == "":
        if not rule_exists:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[주의!]** `/서버규정설정`을 이용하여 설정된 규정이 없습니다. 규정이 설정되어 있지 않아 정확한 판단이 어렵습니다. 아래 판결은 일반적으로 디스코드 서버에 적용되는 규정을 바탕으로 합니다.\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=discord.Color.yellow(),
                )
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="완료",
                    description="AI 판사의 판결은 다음과 같습니다. \n\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n- 규정 위반 메시지가 없습니다.",
                    color=int("a5f0ff", 16),
                )
            )
        return _tracked_result(context, status="completed", reason_code="judge_no_violation")

    try:
        output_dict = _parse_second_stage_output(output)
    except json.JSONDecodeError as exc:
        print(f"JSON 파싱 오류: {exc}")
        print(f"원본 출력: {output}")
        return await _send_internal_error(interaction, context=context, reason_code="judge_second_parse_error", exc=exc)

    description = ""
    for item in output_dict:
        description += f"- <@{item['user_id']}>: {item['punish']} (관련 메시지: {item['message_content']})\n"
    print(description)

    if not rule_exists:
        await interaction.followup.send(
            embed=discord.Embed(
                title="완료",
                description=f"AI 판사의 판결은 다음과 같습니다. \n\n**[주의!]** `/서버규정설정`을 이용하여 설정된 규정이 없습니다. 규정이 설정되어 있지 않아 정확한 판단이 어렵습니다. 아래 판결은 일반적으로 디스코드 서버에 적용되는 규정을 바탕으로 합니다.\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n{description}",
                color=discord.Color.yellow(),
            )
        )
    else:
        await interaction.followup.send(
            embed=discord.Embed(
                title="성공",
                description=f"AI 판사의 판결은 다음과 같습니다. \n\n**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n{description}",
                color=int("a5f0ff", 16),
            )
        )
    return _tracked_result(context, status="completed", reason_code="judge_completed")


async def _run_judge_v1(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    context: Mapping[str, Any],
) -> ErrorTrackedSlashCommandResult:
    prompt_prefix = """
아래 디스코드 서버 대화에서 제시된 메시지들에서 유저별로 규정 위반 행위를 한 부분을 찾고, 유저별 제재 수위를 작성해 주세요.

1. 저희 디스코드 서버는 욕설/비속어/반말은 상대방이 불쾌하지만 않다면 허용입니다. 단, 성적인 대화, 정치 드립, 민감한 주제에 대한 대화 등은 금지됩니다. 또한 위키 관련 대화도 금지입니다.
2. 대화 주제를 고려하지 않고 자기 할말만 하는 등 분위기를 흐리는 행위도 금지입니다.

제재 수위 다음 중 하나입니다: 제재하지 아니함, 주의, 경고, 타임아웃(이 경우 1분 ~ 72시간 사이의 시간으로 기간도 작성), 차단. (차단은 행위가 매우매우 지속적일 때만)

답변 양식: 
- {유저명}: {제재 수위} ({사유})
- {유저명}: {제재 수위} ({사유})
- {유저명}: {제재 수위} ({사유})
- ...

----------"""

    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(embed=_build_ai_blocked_embed(interaction.user.id, reason=reason, until=until))
        return _tracked_result(context, status="rejected", reason_code="judge_blocked_user")

    user_id = interaction.user.id
    current_time = time.time()
    if user_id not in context["bot"].cooldowns:
        context["bot"].cooldowns[user_id] = 0
    if current_time - context["bot"].cooldowns[user_id] < 60:
        await interaction.followup.send(embed=_build_error_embed("이 명령어는 1분마다 한 번 사용 가능합니다."))
        return _tracked_result(context, status="rejected", reason_code="judge_cooldown")
    if user_id == context["developer"]:
        context["bot"].cooldowns[user_id] = current_time

    messages, rejected_result = await _load_judge_messages(
        interaction,
        start_message_link=start_message_link,
        end_message_link=end_message_link,
        context=context,
    )
    if rejected_result is not None:
        return rejected_result
    assert messages is not None

    try:
        text_to_summarize = "\n\n".join(f"{msg.author.display_name}: {msg.content}" for msg in reversed(messages))
        response = context["two_five_lite_model"].generate_content(f"{prompt_prefix}\n\n{text_to_summarize}")
        embed = discord.Embed(
            title="성공",
            description=f"**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\nGemini 2.0 Flash의 답변은 다음과 같습니다: \n\n{response.text}",
            color=int("a5f0ff", 16),
        )
        await interaction.followup.send(embed=embed)
        return _tracked_result(context, status="completed", reason_code="judge_completed")
    except Exception as exc:
        return await _send_internal_error(interaction, context=context, reason_code="judge_v1_error", exc=exc)


async def run_judge_slash_command(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    private_reply: str,
    version: str,
    context: Mapping[str, Any],
) -> ErrorTrackedSlashCommandResult:
    """Execute `/판사` inside bot_app so the active runtime no longer re-enters main.py legacy bodies."""
    if private_reply == "False":
        await interaction.response.defer()
    else:
        await interaction.response.defer(ephemeral=True)

    if version == "v4":
        return await _run_judge_v4(
            interaction,
            start_message_link=start_message_link,
            end_message_link=end_message_link,
            context=context,
        )
    if version == "v3":
        return await _run_judge_v3(
            interaction,
            start_message_link=start_message_link,
            end_message_link=end_message_link,
            context=context,
        )
    return await _run_judge_v1(
        interaction,
        start_message_link=start_message_link,
        end_message_link=end_message_link,
        context=context,
    )


async def run_generative_ai_slash_command(
    interaction: discord.Interaction,
    *,
    prompt_text: str,
    model_name: str,
    attachment,
    reasoning_effort: str,
    context: Mapping[str, Any],
) -> ErrorTrackedSlashCommandResult:
    """Execute `/생성형인공지능` from bot_app without bouncing through main.py callbacks."""
    await interaction.response.defer()
    status, until, reason = context["is_blocked"](interaction.user)
    if status:
        await interaction.followup.send(embed=_build_ai_blocked_embed(interaction.user.id, reason=reason, until=until))
        return _tracked_result(context, status="rejected", reason_code="generative_ai_blocked_user")

    effort = reasoning_effort
    if "discord.gg/" in prompt_text or "discord.com/invite/" in prompt_text:
        await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n입력이 올바르지 않습니다."))
        return _tracked_result(context, status="rejected", reason_code="generative_ai_invalid_prompt")

    attachment_url = None
    if attachment is not None:
        max_file_size = 3 * 1024 * 1024
        allowed_extensions = ["jpg", "jpeg", "png", "pdf", "m4a", "mp3"]
        file_extension = attachment.filename.split(".")[-1].lower()
        if attachment.size > max_file_size:
            await interaction.followup.send(
                embed=_build_error_embed(
                    f"이 모델을 사용할 수 없는 환경입니다.\n\n파일의 크기가 너무 큽니다. 최대 {max_file_size} 바이트까지만 업로드할 수 있습니다."
                )
            )
            return _tracked_result(context, status="rejected", reason_code="generative_ai_file_too_large")
        if file_extension not in allowed_extensions:
            await interaction.followup.send(
                embed=_build_error_embed(
                    "이 모델을 사용할 수 없는 환경입니다.\n\n파일의 확장자가 올바르지 않습니다. jpg, jpeg, png, pdf, m4a, mp3 중 하나만 사용하세요."
                )
            )
            return _tracked_result(context, status="rejected", reason_code="generative_ai_invalid_file_extension")
        attachment_url = attachment.url

    result = None
    try:
        if model_name == "Gemini 1.5 Flash":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["model"].generate_content, prompt_text)
            result = response.text
        elif model_name == "Gemini 2.0 Flash":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["two_model"].generate_content, prompt_text)
            result = response.text
        elif model_name == "Gemini 2.0 Flash Lite":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["two_lite_model"].generate_content, prompt_text)
            result = response.text
        elif model_name == "Gemini 2.5 Flash Lite":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["two_five_lite_model"].generate_content, prompt_text)
            result = response.text
        elif model_name == "Gemini 3.0 Pro":
            if reasoning_effort == "minimal":
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 사고깊이 값 'minimal'을 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_invalid_effort")
            response = await asyncio.to_thread(
                context["gemini_client"].models.generate_content,
                model="gemini-3-pro-preview",
                contents=prompt_text,
            )
            result = response.text
        elif model_name == "귀여운 마늘이":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["cute_model"].generate_content, prompt_text)
            result = response.text
        elif model_name == "판사":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["judge_model"].generate_content, prompt_text)
            result = response.text
        elif model_name == "마느리":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            response = await asyncio.to_thread(context["cute_model3"].generate_content, prompt_text)
            result = response.text
        elif model_name in {"GPT-5.2", "GPT-5.1", "GPT-5", "GPT-5 mini", "GPT-5 nano"}:
            if context["get_premium"](interaction.user.id) is False:
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["ai_cooldowns"]:
                    elapsed = (now - context["ai_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["COOLDOWN_DURATION"]:
                        remaining = int(context["COOLDOWN_DURATION"] - elapsed)
                        await interaction.followup.send(
                            embed=_build_error_embed(
                                f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."
                            )
                        )
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["ai_cooldowns"][user_id] = now

            model_label = model_name.lower().replace(" ", "-")
            user_id = interaction.user.id
            message_content = [{"type": "input_text", "text": prompt_text}]
            if attachment_url is not None:
                message_content.append({"type": "input_image", "image_url": attachment_url})
            if user_id not in context["gpt_chat_threads"]:
                context["gpt_chat_threads"][user_id] = await asyncio.to_thread(context["get_gpt_chat_thread"], user_id)
                if context["gpt_chat_threads"][user_id] is None:
                    response = await context["client"].responses.create(
                        model=model_label,
                        input=[{"role": "user", "content": message_content}],
                        reasoning={"effort": effort},
                    )
                else:
                    response = await context["client"].responses.create(
                        model=model_label,
                        previous_response_id=context["gpt_chat_threads"][user_id],
                        input=[{"role": "user", "content": message_content}],
                        reasoning={"effort": effort},
                    )
            else:
                response = await context["client"].responses.create(
                    model=model_label,
                    previous_response_id=context["gpt_chat_threads"][user_id],
                    input=[{"role": "user", "content": message_content}],
                    reasoning={"effort": effort},
                )
            result = response.output_text
            context["gpt_chat_threads"][user_id] = response.id
            await asyncio.to_thread(context["update_gpt_chat_thread"], user_id, response.id)
        elif model_name == "GPT-4o mini":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            if interaction.user.id != context["developer"] and context["get_premium"](interaction.user.id) is False:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["ai_cooldowns"]:
                    elapsed = (now - context["ai_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["COOLDOWN_DURATION"]:
                        remaining = int(context["COOLDOWN_DURATION"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["ai_cooldowns"][user_id] = now
            llm = ChatOpenAI(temperature=1.0, model_name="gpt-4o-mini")
            result = llm.invoke(prompt_text).content
        elif model_name == "GPT-4o":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            if interaction.user.id != context["developer"]:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 수 있는 사용자로 설정되어 있지 않습니다.\n\n대신 다른 모델(GPT-4.1 nano)을 사용해 볼 수 있습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_model_restricted")
            llm = ChatOpenAI(temperature=1.0, model_name="gpt-4o")
            result = (await llm.invoke(prompt_text)).content
        elif model_name == "GPT-4.1 nano":
            if interaction.user.id != context["developer"] and context["get_premium"](interaction.user.id) is False:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["ai_cooldowns"]:
                    elapsed = (now - context["ai_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["COOLDOWN_DURATION"]:
                        remaining = int(context["COOLDOWN_DURATION"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["ai_cooldowns"][user_id] = now
            if attachment_url is None:
                llm = ChatOpenAI(temperature=1.0, model_name="gpt-4.1-nano")
                result = llm.invoke(prompt_text).content
            else:
                response = await context["client"].responses.create(
                    model="gpt-4.1-nano",
                    input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}, {"type": "input_image", "image_url": attachment_url}]}],
                )
                result = response.output_text
        elif model_name == "GPT-3.5":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            if interaction.user.id != context["developer"] and context["get_premium"](interaction.user.id) is False:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["ai_cooldowns"]:
                    elapsed = (now - context["ai_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["COOLDOWN_DURATION"]:
                        remaining = int(context["COOLDOWN_DURATION"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["ai_cooldowns"][user_id] = now
            llm = ChatOpenAI(temperature=1.0, model_name="gpt-3.5-turbo-0125")
            result = llm.invoke(prompt_text).content
        elif model_name == "GPT-4.1":
            if interaction.user.id != context["developer"] and context["get_premium"](interaction.user.id) is False:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["gpt_4_1_cooldowns"]:
                    elapsed = (now - context["gpt_4_1_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["gpt_4_1_cooldowns_d"]:
                        remaining = int(context["gpt_4_1_cooldowns_d"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(GPT-4.1 mini)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["ai_cooldowns"][user_id] = now
            if attachment_url is None:
                llm = ChatOpenAI(temperature=1.0, model_name="gpt-4.1")
                result = llm.invoke(prompt_text).content
            else:
                response = await context["client"].responses.create(
                    model="gpt-4.1",
                    input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}, {"type": "input_image", "image_url": attachment_url}]}],
                )
                result = response.output_text
        elif model_name == "GPT-4.1 mini":
            if interaction.user.id != context["developer"] and context["get_premium"](interaction.user.id) is False:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["ai_cooldowns"]:
                    elapsed = (now - context["ai_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["COOLDOWN_DURATION"]:
                        remaining = int(context["COOLDOWN_DURATION"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["ai_cooldowns"][user_id] = now
            if attachment_url is None:
                llm = ChatOpenAI(temperature=1.0, model_name="gpt-4.1-mini")
                result = llm.invoke(prompt_text).content
            else:
                response = await context["client"].responses.create(
                    model="gpt-4.1-mini",
                    input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}, {"type": "input_image", "image_url": attachment_url}]}],
                )
                result = response.output_text
        elif model_name == "o4-mini":
            if interaction.user.id != context["developer"]:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["o3_cooldowns"]:
                    elapsed = (now - context["o3_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["o3_cooldowns_d"]:
                        remaining = int(context["o3_cooldowns_d"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(GPT-4.1)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["o3_cooldowns"][user_id] = now
            if effort == "minimal":
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 effort 값 'minimal'을 지원하지 않습니다.\n\n대신 다른 모델(GPT-5 mini)을 사용해 볼 수 있습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_invalid_effort")
            if attachment_url is None:
                response = await context["gpt_client"].responses.create(
                    model="o4-mini",
                    reasoning={"effort": effort},
                    input=[{"role": "user", "content": prompt_text}],
                )
            else:
                response = await context["gpt_client"].responses.create(
                    model="o4-mini",
                    reasoning={"effort": effort},
                    input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}, {"type": "input_image", "image_url": attachment_url}]}],
                )
            result = response.output_text
        elif model_name == "o3-mini":
            if attachment_url is not None:
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 파일 첨부를 지원하지 않습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_attachment_not_supported")
            if interaction.user.id != context["developer"]:
                if len(prompt_text) > 1000:
                    await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델을 사용할 때는 너무 긴 입력을 할 수 없습니다.\n\n대신 다른 모델(Gemini 2.0 Flash)을 사용해 볼 수 있습니다."))
                    return _tracked_result(context, status="rejected", reason_code="generative_ai_prompt_too_long")
                user_id = interaction.user.id
                now = datetime.utcnow()
                if user_id in context["o3_cooldowns"]:
                    elapsed = (now - context["o3_cooldowns"][user_id]).total_seconds()
                    if elapsed < context["o3_cooldowns_d"]:
                        remaining = int(context["o3_cooldowns_d"] - elapsed)
                        await interaction.followup.send(embed=_build_error_embed(f"이 모델을 사용할 수 없는 환경입니다.\n\n이 모델 사용에 대해 쿨타임 중입니다. 다음 시간 후에 다시 사용 가능합니다: {remaining}초\n\n대신 다른 모델(GPT-4.1)을 사용해 볼 수 있습니다."))
                        return _tracked_result(context, status="rejected", reason_code="generative_ai_cooldown")
                context["o3_cooldowns"][user_id] = now
            if effort == "minimal":
                await interaction.followup.send(embed=_build_error_embed("이 모델을 사용할 수 없는 환경입니다.\n\n이 모델은 effort 값 'minimal'을 지원하지 않습니다.\n\n대신 다른 모델(GPT-5 mini)을 사용해 볼 수 있습니다."))
                return _tracked_result(context, status="rejected", reason_code="generative_ai_invalid_effort")
            response = await context["gpt_client"].responses.create(
                model="o3-mini",
                reasoning={"effort": effort},
                input=[{"role": "user", "content": prompt_text}],
            )
            result = response.output_text
        else:
            await interaction.followup.send(embed=_build_error_embed("모델 이름이 올바르지 않습니다. 지원되지 않는 모델일 수 있습니다."))
            return _tracked_result(context, status="rejected", reason_code="generative_ai_invalid_model")
    except Exception as exc:
        return await _send_internal_error(interaction, context=context, reason_code="generative_ai_error", exc=exc)

    file_label = "*(파일 첨부됨)*" if attachment_url is not None else "*(파일 첨부되지 않음)*"
    print(
        "생성형 인공지능 사용:\n"
        f"유저: {interaction.user.display_name} ({interaction.user.id})\n"
        f"모델: {model_name}\n"
        f"입력: {prompt_text}\n"
        f"출력: {result}\n"
        "----------"
    )
    if len(result) > 3000:
        result = result[:3000] + "\n\n(AI 답변이 3000자를 초과하여 이하 생략)"
    embed = discord.Embed(
        title="성공",
        description=(
            "**[경고!]** 인공지능은 실수를 할 수 있습니다. 중요한 정보는 확인하세요.\n\n"
            f"모델: {model_name}\n"
            f"텍스트 입력: {prompt_text}\n"
            f"파일 입력: {file_label}\n"
            f"effort 값(추론 모델에만 적용됨): {effort}\n"
            f"출력: {result}"
        ),
        color=int("a5f0ff", 16),
    )
    await interaction.followup.send(embed=embed)
    return _tracked_result(context, status="completed", reason_code="generative_ai_completed")


async def run_mining_help_slash_command(
    interaction: discord.Interaction,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    mining_help_response = build_mining_help_response(
        actor=interaction.user,
        guild_id=interaction.guild.id,
        context=context,
    )
    if mining_help_response.status == "unsupported_server":
        await interaction.response.send_message(embed=_build_error_embed(mining_help_response.embed_description or "오류"))
        return SlashCommandResult(status="rejected", reason_code=mining_help_response.reason_code)

    await interaction.response.defer()
    await interaction.followup.send(mining_help_response.message_text)
    if mining_help_response.status == "blocked":
        return SlashCommandResult(status="rejected", reason_code=mining_help_response.reason_code)
    return SlashCommandResult(status="completed", reason_code=mining_help_response.reason_code)
