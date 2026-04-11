from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


MiningHelpStatus = Literal["ready", "blocked", "unsupported_server"]


@dataclass(frozen=True, slots=True)
class MiningHelpResponse:
    status: MiningHelpStatus
    reason_code: str
    message_text: str | None = None
    embed_description: str | None = None

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
