from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

import bot_app.commands.slash_user_handlers as slash_user_handlers_module
from bot_app.commands.slash_user_handlers import (
    run_add_likeability_slash_command,
    run_check_likeability_slash_command,
    run_info_slash_command,
    run_user_profile_slash_command,
)
from bot_app.types.readability_contracts import (
    DisplayedXpSnapshot,
    LikeabilityAdjustmentResult,
    LikeabilitySnapshot,
    SlashCommandResult,
    UserClassificationResult,
)


class FakeUser:
    def __init__(
        self,
        user_id: int,
        *,
        mention: str | None = None,
        display_name: str = "마늘",
        name: str = "garlic",
        created_at: datetime | None = None,
    ):
        self.id = user_id
        self.mention = mention or f"<@{user_id}>"
        self.display_name = display_name
        self.name = name
        self.created_at = created_at or datetime(2026, 4, 1, tzinfo=timezone.utc)
        self.display_avatar = SimpleNamespace(url=f"https://example.com/{user_id}.png")


class FakeRole:
    def __init__(self, name: str, mention: str):
        self.name = name
        self.mention = mention


class FakeMember(FakeUser):
    def __init__(
        self,
        user_id: int,
        *,
        roles,
        joined_at: datetime | None = None,
        timed_out_until=None,
        display_name: str = "마늘",
        name: str = "garlic",
    ):
        super().__init__(user_id, display_name=display_name, name=name)
        self.roles = list(roles)
        self.joined_at = joined_at or datetime(2026, 4, 2, tzinfo=timezone.utc)
        self.timed_out_until = timed_out_until


class FakeGuild:
    def __init__(self, guild_id: int, *, member=None, ban_reason: str | None = None):
        self.id = guild_id
        self._member = member
        self._ban_reason = ban_reason

    async def fetch_member(self, user_id: int):
        if self._member is None:
            raise discord.NotFound(response=SimpleNamespace(status=404, reason="not found"), message="missing")
        return self._member

    async def fetch_ban(self, user):
        if self._ban_reason is None:
            raise discord.NotFound(response=SimpleNamespace(status=404, reason="not found"), message="missing")
        return SimpleNamespace(reason=self._ban_reason)


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
async def test_check_likeability_helper_uses_self_when_target_missing(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))

    monkeypatch.setattr(
        slash_user_handlers_module,
        "get_likeability_snapshot",
        lambda user_id: LikeabilitySnapshot(score=7),
    )

    result = await run_check_likeability_slash_command(interaction, target_user=None)

    assert result == SlashCommandResult(status="completed", reason_code="likeability_checked")
    assert interaction.response.deferred == [{"ephemeral": False}]
    assert interaction.followup.sent[0]["embed"].description == "<@10>의 호감도는 7입니다."


@pytest.mark.asyncio
async def test_add_likeability_helper_rejects_non_developer():
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    target_user = FakeUser(20)

    result = await run_add_likeability_slash_command(
        interaction,
        target_user=target_user,
        amount=5,
        context={"developer": 999},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="missing_developer_permission")
    assert interaction.followup.sent[0]["embed"].description == "권한이 부족합니다. 다음 권한이 필요합니다: `개발자`"


@pytest.mark.asyncio
async def test_add_likeability_helper_uses_service_result(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    target_user = FakeUser(20)
    captured = {}

    def fake_force_adjust_likeability(*, user_id: int, delta: int):
        captured.update({"user_id": user_id, "delta": delta})
        return LikeabilityAdjustmentResult(delta=delta, score=15)

    monkeypatch.setattr(slash_user_handlers_module, "force_adjust_likeability", fake_force_adjust_likeability)

    result = await run_add_likeability_slash_command(
        interaction,
        target_user=target_user,
        amount=5,
        context={"developer": 10},
    )

    assert result == SlashCommandResult(status="completed", reason_code="likeability_updated")
    assert captured == {"user_id": 20, "delta": 5}
    assert interaction.followup.sent[0]["embed"].description == "20의 새 호감도는 15(5만큼 추가됨)입니다."


@pytest.mark.asyncio
async def test_info_helper_returns_money_summary(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(1), guild=FakeGuild(1))
    target_user = FakeUser(20, display_name="양파", name="onion")

    monkeypatch.setattr(
        slash_user_handlers_module,
        "get_user_money_lookup",
        lambda user_id: SimpleNamespace(status="found", money=3000),
    )

    result = await run_info_slash_command(interaction, target_user=target_user)

    assert result == SlashCommandResult(status="completed", reason_code="user_money_found")
    assert interaction.response.sent[0]["content"] == "## 양파 정보\n사용자명: onion\n돈 보유량: 3000"


@pytest.mark.asyncio
async def test_info_helper_handles_missing_user(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(1), guild=FakeGuild(1))
    target_user = FakeUser(20)

    monkeypatch.setattr(
        slash_user_handlers_module,
        "get_user_money_lookup",
        lambda user_id: SimpleNamespace(status="missing", money=None),
    )

    result = await run_info_slash_command(interaction, target_user=target_user)

    assert result == SlashCommandResult(status="rejected", reason_code="user_money_missing")
    assert interaction.response.sent[0]["content"] == "**[오류!]** DB에서 해당 사용자를 찾을 수 없습니다."


@pytest.mark.asyncio
async def test_user_profile_helper_rejects_blocked_requester_before_fetch(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    target_user = FakeUser(20)
    warning_called = False

    async def fake_get_user_warning_count(**kwargs):
        nonlocal warning_called
        warning_called = True
        return 1

    monkeypatch.setattr(slash_user_handlers_module, "get_user_warning_count", fake_get_user_warning_count)

    result = await run_user_profile_slash_command(
        interaction,
        target_user=target_user,
        context={
            "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단"),
            "xp_setting": {},
        },
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert warning_called is False
    assert interaction.followup.sent[0]["content"] == "**[오류!]** 10님은 `테스트 차단` 사유로 2099-01-01까지 차단 중입니다."


@pytest.mark.asyncio
async def test_user_profile_helper_builds_member_profile_embed(monkeypatch):
    timed_out_until = datetime.now(timezone.utc) + timedelta(hours=1)
    member = FakeMember(
        20,
        roles=[
            FakeRole("@everyone", "@everyone"),
            FakeRole("역할1", "<@&1>"),
            FakeRole("역할2", "<@&2>"),
        ],
        timed_out_until=timed_out_until,
        display_name="양파",
        name="onion",
    )
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1, member=member))
    target_user = FakeUser(20, display_name="양파", name="onion")

    monkeypatch.setattr(
        slash_user_handlers_module,
        "get_displayed_profile_xp_snapshot",
        lambda **kwargs: DisplayedXpSnapshot(
            total_xp=1200,
            displayed_month_xp=1200,
            total_level=12,
            displayed_month_level=12,
            unit="XP",
        ),
    )
    monkeypatch.setattr(slash_user_handlers_module, "get_user_warning_count", AsyncMock(return_value=3))
    monkeypatch.setattr(
        slash_user_handlers_module,
        "get_user_classification",
        lambda **kwargs: UserClassificationResult(status="premium", label="프리미엄 유저"),
    )

    result = await run_user_profile_slash_command(
        interaction,
        target_user=target_user,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="user_profile_checked")
    embed = interaction.followup.sent[0]["embed"]
    assert embed.fields[0].value == "`20`"
    assert embed.fields[3].value == "<@&2>, <@&1>"
    assert "1200 XP" in embed.fields[5].value
    assert embed.fields[7].name == "서버 참가일"
    assert "타임아웃 중 (" in embed.fields[8].value
    assert embed.fields[9].value == "프리미엄 유저"


@pytest.mark.asyncio
async def test_user_profile_helper_falls_back_to_ban_lookup_for_external_user(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1, member=None, ban_reason="외부 테스트"))
    target_user = FakeUser(20, display_name="양파", name="onion")

    monkeypatch.setattr(slash_user_handlers_module, "get_displayed_profile_xp_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(slash_user_handlers_module, "get_user_warning_count", AsyncMock(return_value=1))
    monkeypatch.setattr(
        slash_user_handlers_module,
        "get_user_classification",
        lambda **kwargs: UserClassificationResult(status="general", label="일반 유저"),
    )

    result = await run_user_profile_slash_command(
        interaction,
        target_user=target_user,
        context={
            "is_blocked": lambda user: (False, None, None),
            "xp_setting": {},
        },
    )

    assert result == SlashCommandResult(status="completed", reason_code="user_profile_checked")
    embed = interaction.followup.sent[0]["embed"]
    field_names = [field.name for field in embed.fields]
    assert "보유한 역할" not in field_names
    assert "서버 참가일" not in field_names
    assert "차단 중 (사유: 외부 테스트)" in embed.fields[4].value
    assert embed.fields[5].value == "일반 유저"


def test_main_uses_user_slash_helpers_instead_of_direct_body_logic():
    source = Path("main.py").read_text(encoding="utf-8")
    user_info_block_start = source.index('@bot.tree.command(name="사용자정보"')
    user_info_block_end = source.index('@bot.tree.command(name = "경고한도설정"', user_info_block_start)
    user_info_block = source[user_info_block_start:user_info_block_end]
    info_block_start = source.index('@bot.tree.command(name="정보"')
    info_block_end = source.index("register_log_events(", info_block_start)
    info_block = source[info_block_start:info_block_end]

    assert "from bot_app.commands.slash_user_handlers import (" in source
    assert "run_user_profile_slash_command," in source
    assert "run_info_slash_command," in source
    assert "await run_user_profile_slash_command(" in user_info_block
    assert "await run_info_slash_command(" in info_block
    assert "SELECT money FROM users WHERE user_id = ?" not in info_block
    assert "load_warning(" not in user_info_block
    assert "get_premium(" not in user_info_block
