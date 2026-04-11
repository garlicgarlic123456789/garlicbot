from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import bot_app.commands.slash_xp_handlers as slash_xp_handlers_module
from bot_app.commands.slash_xp_handlers import (
    run_add_xp_slash_command,
    run_attendance_slash_command,
    run_check_xp_slash_command,
    run_gift_xp_slash_command,
    run_xp_ranking_slash_command,
)
from bot_app.types.readability_contracts import (
    AttendanceRewardResult,
    SlashCommandResult,
    XpAdjustmentResult,
    XpRankingEntry,
    XpRankingPage,
    XpSnapshot,
    XpTransferResult,
)


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


class FakeBot:
    def __init__(self):
        self.fetch_user_calls = []

    async def fetch_user(self, user_id: int):
        self.fetch_user_calls.append(user_id)
        return SimpleNamespace(id=user_id, mention=f"<@{user_id}>")


class FakeResponse:
    def __init__(self):
        self.deferred = []
        self.sent = []

    async def defer(self, *, ephemeral=False):
        self.deferred.append({"ephemeral": ephemeral})

    async def send_message(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


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


@pytest.mark.asyncio
async def test_check_xp_helper_uses_snapshot_and_preserves_old_xp_line(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_xp_snapshot",
        lambda **kwargs: XpSnapshot(
            total_xp=1200,
            month_xp=300,
            total_level=12,
            month_level=3,
            unit="XP",
            old_xp=800,
        ),
    )

    result = await run_check_xp_slash_command(
        interaction,
        target_user=None,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "using_server": 777,
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="xp_checked")
    description = interaction.followup.sent[0]["embed"].description
    assert "- 전체 기간: 1200 XP (12 레벨)" in description
    assert "-# [경험치 초기화]" in description


@pytest.mark.asyncio
async def test_check_xp_helper_uses_explicit_target_and_hides_old_xp_outside_using_server(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=20, mention="<@20>")

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_xp_snapshot",
        lambda **kwargs: XpSnapshot(
            total_xp=400,
            month_xp=120,
            total_level=4,
            month_level=1,
            unit="XP",
            old_xp=None,
        ),
    )

    result = await run_check_xp_slash_command(
        interaction,
        target_user=target_user,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "using_server": 999,
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="xp_checked")
    description = interaction.followup.sent[0]["embed"].description
    assert description.startswith("<@20>님의 경험치 보유 현황")
    assert "-# [경험치 초기화]" not in description


@pytest.mark.asyncio
async def test_check_xp_helper_rejects_when_xp_setting_cache_missing():
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))

    result = await run_check_xp_slash_command(
        interaction,
        target_user=None,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
            "using_server": 777,
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="xp_disabled")
    assert interaction.followup.sent[0]["embed"].description == "경험치 기능이 사용 중지되어 있는 서버입니다."


@pytest.mark.asyncio
async def test_check_xp_helper_rejects_blocked_user_before_snapshot(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    snapshot_called = False

    def fake_get_xp_snapshot(**kwargs):
        nonlocal snapshot_called
        snapshot_called = True
        return XpSnapshot(total_xp=0, month_xp=0, total_level=0, month_level=0, unit="XP")

    monkeypatch.setattr(slash_xp_handlers_module, "get_xp_snapshot", fake_get_xp_snapshot)

    result = await run_check_xp_slash_command(
        interaction,
        target_user=None,
        context={
            "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단"),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "using_server": 777,
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert snapshot_called is False


@pytest.mark.asyncio
async def test_gift_xp_helper_rejects_insufficient_balance(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=20, mention="<@20>", bot=False)

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "transfer_xp",
        lambda **kwargs: XpTransferResult(status="insufficient_balance", amount=100, unit="XP"),
    )

    result = await run_gift_xp_slash_command(
        interaction,
        target_user=target_user,
        amount=100,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="gift_insufficient_balance")
    assert interaction.followup.sent[0]["embed"].description == "경험치가 부족합니다."


@pytest.mark.asyncio
async def test_gift_xp_helper_rejects_bot_target():
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=20, mention="<@20>", bot=True)

    result = await run_gift_xp_slash_command(
        interaction,
        target_user=target_user,
        amount=100,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="gift_target_bot")
    assert interaction.followup.sent[0]["embed"].description == "봇은 경험치 선물을 받을 수 없습니다."


@pytest.mark.asyncio
async def test_gift_xp_helper_rejects_self_and_invalid_amount():
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=10, mention="<@10>", bot=False)

    invalid_result = await run_gift_xp_slash_command(
        interaction,
        target_user=SimpleNamespace(id=20, mention="<@20>", bot=False),
        amount=0,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
        },
    )
    self_result = await run_gift_xp_slash_command(
        interaction,
        target_user=target_user,
        amount=100,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
        },
    )

    assert invalid_result == SlashCommandResult(status="rejected", reason_code="gift_amount_invalid")
    assert self_result == SlashCommandResult(status="rejected", reason_code="gift_self")


@pytest.mark.asyncio
async def test_gift_xp_helper_rejects_when_xp_setting_cache_missing():
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))

    result = await run_gift_xp_slash_command(
        interaction,
        target_user=SimpleNamespace(id=20, mention="<@20>", bot=False),
        amount=100,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="xp_disabled")


@pytest.mark.asyncio
async def test_gift_xp_helper_rejects_blocked_user_before_transfer(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    transfer_called = False

    def fake_transfer_xp(**kwargs):
        nonlocal transfer_called
        transfer_called = True
        return XpTransferResult(status="success", amount=100, unit="XP")

    monkeypatch.setattr(slash_xp_handlers_module, "transfer_xp", fake_transfer_xp)

    result = await run_gift_xp_slash_command(
        interaction,
        target_user=SimpleNamespace(id=20, mention="<@20>", bot=False),
        amount=100,
        context={
            "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단"),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert transfer_called is False


@pytest.mark.asyncio
async def test_gift_xp_helper_sends_success_embed(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=20, mention="<@20>", bot=False)

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "transfer_xp",
        lambda **kwargs: XpTransferResult(status="success", amount=150, unit="XP"),
    )

    result = await run_gift_xp_slash_command(
        interaction,
        target_user=target_user,
        amount=150,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="gift_processed")
    assert interaction.followup.sent[0]["embed"].description == "<@10>님이 <@20>님에게 150 XP을(를) 선물하였습니다."


@pytest.mark.asyncio
async def test_add_xp_helper_uses_adjust_result(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=20, mention="<@20>")

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "adjust_xp",
        lambda **kwargs: XpAdjustmentResult(amount=30, total_xp=530, month_xp=130, unit="XP"),
    )

    result = await run_add_xp_slash_command(
        interaction,
        target_user=target_user,
        amount=30,
        context={"xp_setting": {777: [True, 15, 30, None, None, "XP"]}},
    )

    assert result == SlashCommandResult(status="completed", reason_code="xp_adjusted")
    assert "현재 경험치: 530 (월간 경험치: 130)" in interaction.followup.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_add_xp_helper_rejects_when_xp_setting_cache_missing():
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    target_user = SimpleNamespace(id=20, mention="<@20>")

    result = await run_add_xp_slash_command(
        interaction,
        target_user=target_user,
        amount=30,
        context={"xp_setting": {}},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="xp_disabled")
    assert interaction.response.sent[0]["embed"].description == "경험치 기능이 사용 중지되어 있는 서버입니다."


@pytest.mark.asyncio
async def test_xp_ranking_helper_uses_ranking_page_and_fetches_users(monkeypatch):
    bot = FakeBot()
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_xp_ranking_page",
        lambda **kwargs: XpRankingPage(
            title="경험치 순위",
            page=2,
            total_pages=3,
            unit="XP",
            entries=(
                XpRankingEntry(user_id=30, xp=500, level=5, rank=21),
                XpRankingEntry(user_id=40, xp=300, level=3, rank=22),
            ),
        ),
    )

    result = await run_xp_ranking_slash_command(
        interaction,
        scope="all",
        page=2,
        context={
            "bot": bot,
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "page_size": 20,
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="xp_ranking_checked")
    assert bot.fetch_user_calls == [30, 40]
    assert interaction.followup.sent[0]["embed"].description == "21위: <@30> 5 레벨 - 500 XP\n22위: <@40> 3 레벨 - 300 XP"
    assert interaction.followup.sent[0]["embed"].footer.text == "페이지 2 / 3"


@pytest.mark.asyncio
async def test_xp_ranking_helper_handles_month_scope_and_empty_page(monkeypatch):
    bot = FakeBot()
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))

    monkeypatch.setattr(
        slash_xp_handlers_module,
        "get_xp_ranking_page",
        lambda **kwargs: XpRankingPage(
            title="경험치 순위 (월간)",
            page=4,
            total_pages=4,
            unit="XP",
            entries=(),
        ),
    )

    result = await run_xp_ranking_slash_command(
        interaction,
        scope="month",
        page=4,
        context={
            "bot": bot,
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "page_size": 20,
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="xp_ranking_checked")
    assert interaction.followup.sent[0]["embed"].title == "경험치 순위 (월간)"
    assert interaction.followup.sent[0]["embed"].description == "해당 페이지에 데이터가 없습니다."


@pytest.mark.asyncio
async def test_xp_ranking_helper_rejects_when_xp_setting_cache_missing():
    bot = FakeBot()
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))

    result = await run_xp_ranking_slash_command(
        interaction,
        scope="all",
        page=1,
        context={
            "bot": bot,
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
            "page_size": 20,
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="xp_disabled")


@pytest.mark.asyncio
async def test_xp_ranking_helper_rejects_blocked_user_before_ranking(monkeypatch):
    bot = FakeBot()
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(777))
    ranking_called = False

    def fake_get_xp_ranking_page(**kwargs):
        nonlocal ranking_called
        ranking_called = True
        return XpRankingPage(title="경험치 순위", page=1, total_pages=1, unit="XP", entries=())

    monkeypatch.setattr(slash_xp_handlers_module, "get_xp_ranking_page", fake_get_xp_ranking_page)

    result = await run_xp_ranking_slash_command(
        interaction,
        scope="all",
        page=1,
        context={
            "bot": bot,
            "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단"),
            "xp_setting": {777: [True, 15, 30, None, None, "XP"]},
            "page_size": 20,
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert ranking_called is False


def test_main_routes_attendance_through_xp_helper():
    source = Path("main.py").read_text(encoding="utf-8")
    attendance_start = source.index('@bot.tree.command(name="출석체크", description="출석체크하고 경험치를 받습니다.")')
    attendance_end = source.index('@bot.tree.command(name="경험치확인"', attendance_start)
    attendance_source = source[attendance_start:attendance_end]

    assert "from bot_app.commands.slash_xp_handlers import (" in source
    assert "run_attendance_slash_command," in source
    assert "await run_attendance_slash_command(" in attendance_source
    assert "process_attendance_reward(" not in attendance_source
    assert "get_effective_xp_setting(" not in attendance_source
    assert "status, until, reason = is_blocked(interaction.user)" not in attendance_source


def test_main_routes_remaining_xp_commands_through_xp_helper():
    source = Path("main.py").read_text(encoding="utf-8")
    check_start = source.index('@bot.tree.command(name="경험치확인"')
    check_end = source.index('@bot.tree.command(name="사용자정보"', check_start)
    check_block = source[check_start:check_end]

    assert "run_check_xp_slash_command," in source
    assert "run_gift_xp_slash_command," in source
    assert "run_add_xp_slash_command," in source
    assert "run_xp_ranking_slash_command," in source
    assert "await run_check_xp_slash_command(" in check_block
    assert "await run_gift_xp_slash_command(" in check_block
    assert "await run_add_xp_slash_command(" in check_block
    assert "await run_xp_ranking_slash_command(" in check_block
    assert "get_xp(interaction.guild.id, member.id)" not in check_block
    assert "update_xp(interaction.guild.id, interaction.user.id, -amount)" not in check_block
    assert "get_all_xp(interaction.guild.id)" not in check_block
