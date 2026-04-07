from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from bot_app.types.readability_contracts import SlashCommandResult


MiningHelpStatus = Literal["ready", "blocked", "unsupported_server"]


@dataclass(frozen=True, slots=True)
class MiningHelpResponse:
    status: MiningHelpStatus
    reason_code: str
    message_text: str | None = None
    embed_description: str | None = None


async def delegate_same_person_check(
    *,
    interaction,
    first_user,
    second_user,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    """Delegate `/동일인여부확인` to an injected legacy executor."""

    await context["same_person_handler"](interaction, first_user, second_user)
    return SlashCommandResult(status="completed", reason_code="same_person_delegated")


async def delegate_judge_command(
    *,
    interaction,
    start_message_link: str,
    end_message_link: str | None,
    private_reply: str,
    version: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    """Delegate `/판사` to an injected legacy executor."""

    await context["judge_handler"](interaction, start_message_link, end_message_link, private_reply, version)
    return SlashCommandResult(status="completed", reason_code="judge_delegated")


async def delegate_generative_ai_command(
    *,
    interaction,
    prompt_text: str,
    model_name: str,
    attachment,
    reasoning_effort: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    """Delegate `/생성형인공지능` to an injected legacy executor."""

    await context["generative_ai_handler"](interaction, prompt_text, model_name, attachment, reasoning_effort)
    return SlashCommandResult(status="completed", reason_code="generative_ai_delegated")


def build_mining_help_response(
    *,
    actor,
    guild_id: int,
    context: Mapping[str, Any],
) -> MiningHelpResponse:
    """Resolve `/도움말광질` output without exposing legacy globals to helpers."""

    if guild_id != context["using_server"]:
        return MiningHelpResponse(
            status="unsupported_server",
            reason_code="unsupported_server",
            embed_description="이 기능은 아직 여러 서버들에서 지원되지 않습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)",
        )

    blocked, blocked_until, reason = context["is_blocked"](actor)
    if blocked:
        return MiningHelpResponse(
            status="blocked",
            reason_code="blocked_user",
            message_text=f"**[오류!]** {actor.id}님은 `{reason}` 사유로 {blocked_until}까지 차단 중입니다.",
        )

    return MiningHelpResponse(
        status="ready",
        reason_code="mine_help_shown",
        message_text=(
            "광질 확률: 다이아몬드 1%, 에메랄드 2%, 금 47%, 철 49%, 용암 1%\n"
            "광질 시 소모 경험치: 일자굴 1블록 당 20 XP\n"
            "광질 시 지급 경험치: 다이아몬드 500 XP, 에메랄드 200 XP, 철 10 XP, 금 30 XP. 단, 용암 발견 시 지급하지 아니함."
        ),
    )
