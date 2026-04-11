from pathlib import Path

import discord
import pytest

from bot_app.events.ready_events import (
    build_ticket_embed,
    initialize_invite_cache,
    register_ready_events,
    restore_ticket_message_view,
    run_ready_initialization,
    start_loop_if_needed,
)
from bot_app.types.readability_contracts import LoopStartResult
from tests.helpers.fakes import FakeBot


class FakeLoop:
    def __init__(self, *, running: bool):
        self._running = running
        self.start_calls = 0

    def is_running(self):
        return self._running

    def start(self):
        self.start_calls += 1
        self._running = True


class FakeMessage:
    def __init__(self, message_id: int):
        self.id = message_id
        self.edited_view = None

    async def edit(self, *, view=None):
        self.edited_view = view


class FakeReadyChannel:
    def __init__(self, *, existing_message=None):
        self.existing_message = existing_message
        self.sent_messages = []

    async def fetch_message(self, message_id):
        if self.existing_message is None or self.existing_message.id != message_id:
            raise discord.NotFound(response=None, message="not found")
        return self.existing_message

    async def send(self, *, embed=None, view=None):
        message = FakeMessage(999)
        self.sent_messages.append({"embed": embed, "view": view, "message": message})
        return message


class FakeReadyGuild:
    def __init__(self, guild_id: int, *, name: str, invites_result):
        self.id = guild_id
        self.name = name
        self._invites_result = invites_result
        self.invite_calls = 0

    async def invites(self):
        self.invite_calls += 1
        if isinstance(self._invites_result, Exception):
            raise self._invites_result
        return self._invites_result


class FakeDiscordResponse:
    status = 403
    reason = "Forbidden"
    text = "forbidden"


def _ticket_view_factory():
    return {"view": "ticket"}


def test_start_loop_if_needed_only_starts_once():
    stopped = FakeLoop(running=False)
    running = FakeLoop(running=True)

    assert start_loop_if_needed(stopped) == LoopStartResult(status="started", started=True)
    assert stopped.start_calls == 1
    assert start_loop_if_needed(running) == LoopStartResult(status="already_running", started=False)
    assert running.start_calls == 0


def test_build_ticket_embed_keeps_expected_title():
    embed = build_ticket_embed()

    assert embed.title == "문의 및 신고 게시판"
    assert "긴급 티켓" in embed.description


@pytest.mark.asyncio
async def test_restore_ticket_message_view_reuses_existing_message(tmp_path):
    ticket_file = tmp_path / "ticket_message_id.txt"
    ticket_file.write_text("123", encoding="utf-8")
    existing_message = FakeMessage(123)
    channel = FakeReadyChannel(existing_message=existing_message)

    result = await restore_ticket_message_view(
        channel,
        ticket_message_file=str(ticket_file),
        view_factory=_ticket_view_factory,
    )

    assert result == "restored"
    assert existing_message.edited_view == {"view": "ticket"}


@pytest.mark.asyncio
async def test_restore_ticket_message_view_creates_message_when_missing(tmp_path):
    ticket_file = tmp_path / "ticket_message_id.txt"
    channel = FakeReadyChannel(existing_message=None)

    result = await restore_ticket_message_view(
        channel,
        ticket_message_file=str(ticket_file),
        view_factory=_ticket_view_factory,
    )

    assert result == "created"
    assert channel.sent_messages[0]["embed"].title == "문의 및 신고 게시판"
    assert ticket_file.read_text(encoding="utf-8") == "999"


@pytest.mark.asyncio
async def test_initialize_invite_cache_handles_success_and_failures():
    forbidden_error = discord.Forbidden(response=FakeDiscordResponse(), message="forbidden")
    bot = type(
        "Bot",
        (),
        {
            "guilds": [
                FakeReadyGuild(1, name="메인", invites_result=["a"]),
                FakeReadyGuild(2, name="금지", invites_result=forbidden_error),
                FakeReadyGuild(3, name="오류", invites_result=RuntimeError("boom")),
            ],
            "get_guild": lambda self, guild_id: self.guilds[0] if guild_id == 1 else None,
        },
    )()
    invite_cache = {}

    await initialize_invite_cache(bot, invite_cache=invite_cache, using_server=1)

    assert invite_cache[1] == ["a"]
    assert invite_cache[2] == []
    assert invite_cache[3] == []


def test_register_ready_events_registers_on_ready():
    bot = FakeBot()

    register_ready_events(
        bot,
        {
            "schedule_chat_analyze": lambda func: None,
            "chat_analyze_save_to_db": object(),
            "status_loop": FakeLoop(running=False),
            "exp_event": FakeLoop(running=False),
            "legacy_disable": FakeLoop(running=False),
            "ticket_view_factory": _ticket_view_factory,
            "ticket_channel_id": 0,
            "ticket_message_file": "ticket_message_id.txt",
            "invite_cache": {},
            "using_server": 0,
        },
    )

    assert "on_ready" in bot.registered_events


@pytest.mark.asyncio
async def test_run_ready_initialization_executes_full_orchestration(tmp_path):
    events = []
    ticket_file = tmp_path / "ticket_message_id.txt"
    ticket_file.write_text("123", encoding="utf-8")
    existing_message = FakeMessage(123)
    channel = FakeReadyChannel(existing_message=existing_message)
    main_guild = FakeReadyGuild(1, name="메인", invites_result=["invite"])
    extra_guild = FakeReadyGuild(2, name="추가", invites_result=["other"])

    class RecordingLoop(FakeLoop):
        def __init__(self, name: str):
            super().__init__(running=False)
            self.name = name

        def start(self):
            events.append(f"loop:{self.name}")
            super().start()

    class RecordingTree:
        async def sync(self):
            events.append("sync")

    class ReadyBot:
        def __init__(self):
            self.tree = RecordingTree()
            self.user = "garlicbot"
            self.guilds = [main_guild, extra_guild]
            self.views = []

        def add_view(self, view):
            self.views.append(view)
            events.append("add_view")

        def get_channel(self, channel_id):
            return channel

        def get_guild(self, guild_id):
            return main_guild if guild_id == 1 else None

    bot = ReadyBot()

    await run_ready_initialization(
        bot,
        {
            "schedule_chat_analyze": lambda func: events.append("schedule"),
            "chat_analyze_save_to_db": object(),
            "status_loop": RecordingLoop("status"),
            "exp_event": RecordingLoop("exp"),
            "legacy_disable": RecordingLoop("legacy"),
            "ticket_view_factory": _ticket_view_factory,
            "ticket_channel_id": 777,
            "ticket_message_file": str(ticket_file),
            "invite_cache": {},
            "using_server": 1,
        },
    )

    assert events[:5] == ["schedule", "sync", "loop:status", "loop:exp", "loop:legacy"]
    assert "add_view" in events
    assert existing_message.edited_view == {"view": "ticket"}
    assert main_guild.invite_calls >= 1
    assert extra_guild.invite_calls == 1


def test_main_keeps_ready_event_registration_boundary():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "register_ready_events(" in source
    assert '"ticket_view_factory": TicketView' in source
    assert '"ticket_message_file": TICKET_MESSAGE_FILE' in source
    assert "async def on_ready" not in source
