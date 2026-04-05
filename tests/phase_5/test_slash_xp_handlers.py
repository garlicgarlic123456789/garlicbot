from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import bot_app.commands.slash_xp_handlers as slash_xp_handlers_module
from bot_app.commands.slash_xp_handlers import run_attendance_slash_command
from bot_app.types.readability_contracts import AttendanceRewardResult, SlashCommandResult


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id


class FakeUser:
    def __init__(self, user_id: int, *, mention: str | None = None, roles=None):
        self.id = user_id
        self.mention = mention or f"<@{user_id}>"
        self.roles = list(roles or [])


class FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id


class FakeResponse:
    def __init__(self):
        self.deferred = []

    async def defer(self, *, ephemeral=False):
        self.deferred.append({"ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.response = FakeResponse()
        self.followup = FakeFollowup()


@pytest.mark.asyncio
async def test_attendance_helper_rejects_blocked_user_before_service_call(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(1))
    service_called = False

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_effective_xp_setting",
        lambda **kwargs: SimpleNamespace(enabled=True),
    )

    async def fake_process_attendance_reward(**kwargs):
        nonlocal service_called
        service_called = True
        return AttendanceRewardResult(status="success", total_xp=100, unit="XP")

    monkeypatch.setattr(slash_xp_handlers_module, "process_attendance_reward", fake_process_attendance_reward)

    result = await run_attendance_slash_command(
        interaction,
        context={
            "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단"),
            "xp_setting": {},
            "using_server": 999,
            "server_booster_role_id": 1,
            "kst": ZoneInfo("Asia/Seoul"),
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert service_called is False
    assert interaction.followup.sent[0]["content"] == "**[오류!]** 10님은 `테스트 차단` 사유로 2099-01-01까지 차단 중입니다."


@pytest.mark.asyncio
async def test_attendance_helper_rejects_when_xp_disabled(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_effective_xp_setting",
        lambda **kwargs: SimpleNamespace(enabled=False),
    )

    result = await run_attendance_slash_command(
        interaction,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
            "using_server": 999,
            "server_booster_role_id": 1,
            "kst": ZoneInfo("Asia/Seoul"),
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="xp_disabled")
    assert interaction.response.deferred == [{"ephemeral": False}]
    assert interaction.followup.sent[0]["embed"].description == "경험치 기능이 사용 중지되어 있는 서버입니다."


@pytest.mark.asyncio
async def test_attendance_helper_rejects_when_attendance_disabled(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_effective_xp_setting",
        lambda **kwargs: SimpleNamespace(enabled=True),
    )

    async def fake_process_attendance_reward(**kwargs):
        return AttendanceRewardResult(status="attendance_disabled")

    monkeypatch.setattr(slash_xp_handlers_module, "process_attendance_reward", fake_process_attendance_reward)

    result = await run_attendance_slash_command(
        interaction,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
            "using_server": 999,
            "server_booster_role_id": 1,
            "kst": ZoneInfo("Asia/Seoul"),
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="attendance_disabled")
    assert interaction.followup.sent[0]["embed"].description == "출석체크 기능이 사용 중지되어 있는 서버입니다."


@pytest.mark.asyncio
async def test_attendance_helper_rejects_when_already_checked(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(1))

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_effective_xp_setting",
        lambda **kwargs: SimpleNamespace(enabled=True),
    )

    async def fake_process_attendance_reward(**kwargs):
        return AttendanceRewardResult(status="already_checked", streak=3)

    monkeypatch.setattr(slash_xp_handlers_module, "process_attendance_reward", fake_process_attendance_reward)

    result = await run_attendance_slash_command(
        interaction,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
            "using_server": 999,
            "server_booster_role_id": 1,
            "kst": ZoneInfo("Asia/Seoul"),
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="already_checked")
    assert "오늘 이미 출석체크를 완료하였습니다" in interaction.followup.sent[0]["content"]


@pytest.mark.asyncio
async def test_attendance_helper_sends_booster_and_streak_success_message(monkeypatch):
    interaction = FakeInteraction(
        user=FakeUser(10, mention="<@10>", roles=[FakeRole(500)]),
        guild=FakeGuild(1),
    )

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_effective_xp_setting",
        lambda **kwargs: SimpleNamespace(enabled=True),
    )

    async def fake_process_attendance_reward(**kwargs):
        return AttendanceRewardResult(
            status="success",
            streak=3,
            boost_check_xp=700,
            streak_bonus=100,
            total_xp=1200,
            unit="XP",
        )

    monkeypatch.setattr(slash_xp_handlers_module, "process_attendance_reward", fake_process_attendance_reward)

    result = await run_attendance_slash_command(
        interaction,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
            "using_server": 1,
            "server_booster_role_id": 500,
            "kst": ZoneInfo("Asia/Seoul"),
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="attendance_processed")
    message = interaction.followup.sent[0]["content"]
    assert "연속 3일차" in message
    assert "서버 부스터 보너스 `700` XP 포함" in message
    assert "연속 출석 보너스 `100` XP 포함" in message


@pytest.mark.asyncio
async def test_attendance_helper_forwards_expected_arguments_to_service(monkeypatch):
    forwarded = {}
    interaction = FakeInteraction(
        user=FakeUser(10, mention="<@10>", roles=[FakeRole(500), FakeRole(501)]),
        guild=FakeGuild(777),
    )

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_effective_xp_setting",
        lambda **kwargs: SimpleNamespace(enabled=True),
    )

    async def fake_process_attendance_reward(**kwargs):
        forwarded.update(kwargs)
        return AttendanceRewardResult(status="success", total_xp=100, unit="XP")

    monkeypatch.setattr(slash_xp_handlers_module, "process_attendance_reward", fake_process_attendance_reward)

    result = await run_attendance_slash_command(
        interaction,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "using_server": 777,
            "server_booster_role_id": 500,
            "kst": ZoneInfo("Asia/Seoul"),
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="attendance_processed")
    assert forwarded == {
        "server_id": 777,
        "user_id": 10,
        "user_role_ids": {500, 501},
        "xp_settings": {777: [True, 15, 30, None, None, "XP"]},
        "using_server": 777,
        "server_booster_role_id": 500,
    }


def test_main_routes_attendance_through_xp_helper():
    source = Path("main.py").read_text(encoding="utf-8")
    attendance_start = source.index('@bot.tree.command(name="출석체크", description="출석체크하고 경험치를 받습니다.")')
    attendance_end = source.index('@bot.tree.command(name="경험치확인"', attendance_start)
    attendance_source = source[attendance_start:attendance_end]

    assert "from bot_app.commands.slash_xp_handlers import run_attendance_slash_command" in source
    assert "await run_attendance_slash_command(" in attendance_source
    assert "process_attendance_reward(" not in attendance_source
    assert "get_effective_xp_setting(" not in attendance_source
    assert "status, until, reason = is_blocked(interaction.user)" not in attendance_source
