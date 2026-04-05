from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import discord

from bot_app.types.readability_contracts import LoopStartResult


def start_loop_if_needed(loop) -> LoopStartResult:
    """Start a discord task loop once and return a readable status."""
    if loop.is_running():
        return LoopStartResult(status="already_running", started=False)
    loop.start()
    return LoopStartResult(status="started", started=True)


def build_ticket_embed() -> discord.Embed:
    return discord.Embed(
        title="문의 및 신고 게시판",
        description="""아래 버튼을 눌러 티켓을 생성한 후, 문의나 신고를 접수해 주세요.

**장난성 티켓을 생성할 경우 제재됩니다.**

티켓을 열더라도 운영진이 멘션되지 않고 운영진에게 티켓 보기 권한 부여 및 로그 채널에 로그만 전송되므로, 티켓 처리에는 시간이 소요될 수 있으며, 재촉성 멘션을 할 경우 제재될 수 있습니다.

티켓 유형 안내: 

- 간편 티켓: 관련한 정보 첨부 없이 바로 문의/신고가 가능한 티켓입니다.
- 티켓: 관련 메시지 링크 첨부 후 문의/신고가 가능한 티켓입니다.
- 긴급 티켓: 테러 등 긴급 상황에 모든 운영진은 멘션할 수 있는 티켓입니다. **테러, 레이드 이외에는 사용해서는 안 되며, 사용 시 제재될 수 있습니다.**
- 소유자 티켓: 소유자 (서버 주인) 만 볼 수 있는 티켓입니다. <#1483037563991232549>에 스레드가 생성됩니다.

이 티켓이 제대로 동작하지 않는 경우 직접 스레드를 생성해 주세요.""",
        color=int("a5f0ff", 16),
    )


async def restore_ticket_message_view(channel, *, ticket_message_file: str, view_factory) -> str:
    file_path = Path(ticket_message_file)

    try:
        message_id = int(file_path.read_text(encoding="utf-8").strip())
        message = await channel.fetch_message(message_id)
        await message.edit(view=view_factory())
        print("기존 티켓 메시지에 View를 다시 연결했습니다.")
        return "restored"
    except (FileNotFoundError, ValueError, discord.NotFound):
        message = await channel.send(embed=build_ticket_embed(), view=view_factory())
        file_path.write_text(str(message.id), encoding="utf-8")
        print("새 티켓 메시지를 전송하고 ID를 저장했습니다.")
        return "created"


async def initialize_invite_cache(bot, *, invite_cache: dict[int, Any], using_server: int) -> None:
    guild = bot.get_guild(using_server)
    if guild:
        invite_cache[guild.id] = await guild.invites()
        print(f"{guild.name} 서버의 초대 캐시 초기화 완료")
    else:
        print("사용 중인 서버를 찾을 수 없습니다.")

    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
            print(f"{guild.name} 서버의 초대 캐시 초기화 완료")
        except discord.Forbidden:
            invite_cache[guild.id] = []
            print(f"{guild.name} 서버의 초대 링크에 접근할 수 없습니다.")
        except Exception as error:
            invite_cache[guild.id] = []
            print(f"{guild.name} 서버의 초대 링크 캐싱 중 오류 발생: {error}")


async def run_ready_initialization(bot, context: Mapping[str, Any]) -> None:
    context["schedule_chat_analyze"](context["chat_analyze_save_to_db"])
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    start_loop_if_needed(context["status_loop"])
    start_loop_if_needed(context["exp_event"])
    start_loop_if_needed(context["legacy_disable"])

    view_factory = context["ticket_view_factory"]
    bot.add_view(view_factory())

    channel = bot.get_channel(context["ticket_channel_id"])
    if not channel:
        print("티켓 채널을 찾을 수 없습니다.")
        return

    await restore_ticket_message_view(
        channel,
        ticket_message_file=context["ticket_message_file"],
        view_factory=view_factory,
    )
    await initialize_invite_cache(
        bot,
        invite_cache=context["invite_cache"],
        using_server=context["using_server"],
    )


def register_ready_events(bot, context: Mapping[str, Any]) -> None:
    @bot.event
    async def on_ready():
        await run_ready_initialization(bot, context)
