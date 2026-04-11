from pathlib import Path
from types import SimpleNamespace

import pytest

import bot_app.commands.slash_guild_settings_handlers as slash_guild_settings_handlers_module
import bot_app.commands.slash_moderation_handlers as slash_moderation_handlers_module
from bot_app.commands.slash_guild_settings_handlers import run_set_log_channel_slash_command
from bot_app.commands.slash_moderation_handlers import (
    run_check_warning_slash_command,
    run_set_warn_limit_slash_command,
)
from bot_app.types.readability_contracts import (
    ErrorTrackedSlashCommandResult,
    GuildLogChannelSelection,
    SlashCommandResult,
    WarningStatusSnapshot,
)


class FakePermissions:
    def __init__(self, *, manage_guild=False):
        self.manage_guild = manage_guild


class FakeUser:
    def __init__(self, user_id: int, *, mention: str | None = None, manage_guild=False):
        self.id = user_id
        self.mention = mention or f"<@{user_id}>"
        self.guild_permissions = FakePermissions(manage_guild=manage_guild)


class FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id


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
async def test_set_warn_limit_helper_requires_manage_guild_permission():
    interaction = FakeInteraction(user=FakeUser(10, manage_guild=False), guild=FakeGuild(1))

    result = await run_set_warn_limit_slash_command(
        interaction,
        warn_limit=3,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="missing_manage_guild_permission")
    assert interaction.response.sent[0]["embed"].description == "권한이 부족합니다. 다음 권한이 필요합니다: `서버 관리하기`"


@pytest.mark.asyncio
async def test_set_warn_limit_helper_normalizes_zero_to_none(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, manage_guild=True), guild=FakeGuild(1))
    captured = {}

    def fake_set_warn_limit(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(warn_max=None)

    monkeypatch.setattr(slash_moderation_handlers_module, "set_warn_limit", fake_set_warn_limit)

    result = await run_set_warn_limit_slash_command(
        interaction,
        warn_limit=0,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="warn_limit_updated")
    assert captured == {"server_id": 1, "warn_max": None}
    assert interaction.followup.sent[0]["embed"].description == "경고 한도가 비활성화되었습니다."


@pytest.mark.asyncio
async def test_set_warn_limit_helper_rejects_out_of_range():
    interaction = FakeInteraction(user=FakeUser(10, manage_guild=True), guild=FakeGuild(1))

    result = await run_set_warn_limit_slash_command(
        interaction,
        warn_limit=101,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="warn_limit_out_of_range")
    assert "한도의 값은 0 이상 100 이하이어야 합니다." in interaction.followup.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_set_warn_limit_helper_rejects_blocked_user():
    interaction = FakeInteraction(user=FakeUser(10, manage_guild=True), guild=FakeGuild(1))

    result = await run_set_warn_limit_slash_command(
        interaction,
        warn_limit=3,
        context={"is_blocked": lambda user: (True, "2099-01-01", "테스트 차단")},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert interaction.followup.sent[0]["content"] == "**[오류!]** 10님은 `테스트 차단` 사유로 2099-01-01까지 차단 중입니다."


@pytest.mark.asyncio
async def test_check_warning_helper_uses_default_self_target(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(1))

    async def fake_get_warning_status(**kwargs):
        return WarningStatusSnapshot(warning_count=2, warn_max=5)

    monkeypatch.setattr(slash_moderation_handlers_module, "get_warning_status", fake_get_warning_status)

    result = await run_check_warning_slash_command(
        interaction,
        target_user=None,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="warning_checked")
    embed = interaction.followup.sent[0]["embed"]
    assert embed.fields[0].value == "<@10>"
    assert embed.fields[1].value == "2개 / 5개"


@pytest.mark.asyncio
async def test_check_warning_helper_handles_no_warn_limit(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(1))
    target_user = SimpleNamespace(id=20, mention="<@20>")

    async def fake_get_warning_status(**kwargs):
        return WarningStatusSnapshot(warning_count=1, warn_max=None)

    monkeypatch.setattr(slash_moderation_handlers_module, "get_warning_status", fake_get_warning_status)

    result = await run_check_warning_slash_command(
        interaction,
        target_user=target_user,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="warning_checked")
    embed = interaction.followup.sent[0]["embed"]
    assert embed.fields[0].value == "<@20>"
    assert embed.fields[1].value == "1개"


@pytest.mark.asyncio
async def test_check_warning_helper_rejects_blocked_user_before_service(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10, mention="<@10>"), guild=FakeGuild(1))
    service_called = False

    async def fake_get_warning_status(**kwargs):
        nonlocal service_called
        service_called = True
        return WarningStatusSnapshot(warning_count=1, warn_max=None)

    monkeypatch.setattr(slash_moderation_handlers_module, "get_warning_status", fake_get_warning_status)

    result = await run_check_warning_slash_command(
        interaction,
        target_user=None,
        context={"is_blocked": lambda user: (True, "2099-01-01", "테스트 차단")},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert service_called is False


@pytest.mark.asyncio
async def test_set_log_channel_helper_updates_service_with_normalized_ids(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    captured = {}

    def fake_update_guild_log_channels(**kwargs):
        captured.update(kwargs)
        return kwargs["selection"]

    monkeypatch.setattr(slash_guild_settings_handlers_module, "update_guild_log_channels", fake_update_guild_log_channels)

    result = await run_set_log_channel_slash_command(
        interaction,
        editdelete_channel=SimpleNamespace(id=11),
        reaction_channel=SimpleNamespace(id=12),
        role_channel=SimpleNamespace(id=13),
        block_channel=None,
        image_channel=SimpleNamespace(id=14),
        error_count=7,
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=7, reason_code="log_channel_updated")
    assert captured == {
        "server_id": 1,
        "selection": GuildLogChannelSelection(editdelete=11, reaction=12, role=13, image=14, block=0),
    }
    assert interaction.followup.sent[0]["embed"].description == "로그 채널 설정이 완료되었습니다."


@pytest.mark.asyncio
async def test_set_log_channel_helper_increments_error_on_failure(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))

    def fake_update_guild_log_channels(**kwargs):
        raise RuntimeError("db failed")

    monkeypatch.setattr(slash_guild_settings_handlers_module, "update_guild_log_channels", fake_update_guild_log_channels)

    result = await run_set_log_channel_slash_command(
        interaction,
        editdelete_channel=None,
        reaction_channel=None,
        role_channel=None,
        block_channel=None,
        image_channel=None,
        error_count=9,
    )

    assert result == ErrorTrackedSlashCommandResult(status="failed", error_count=10, reason_code="log_channel_update_error")
    assert "오류 #9" in interaction.followup.sent[0]["embed"].description


def test_main_routes_warn_settings_commands_through_helpers():
    source = Path("main.py").read_text(encoding="utf-8")
    warn_limit_start = source.index('@bot.tree.command(name = "경고한도설정"')
    warn_limit_end = source.index('@bot.tree.command(name="경고"', warn_limit_start)
    warn_limit_block = source[warn_limit_start:warn_limit_end]

    warn_check_start = source.index('@bot.tree.command(name="경고확인"')
    warn_check_end = source.index('@bot.tree.command(name="추방"', warn_check_start)
    warn_check_block = source[warn_check_start:warn_check_end]

    log_channel_start = source.index('@bot.tree.command(name = "로그채널설정"')
    log_channel_end = source.index('@bot.tree.command(name="타임아웃"', log_channel_start)
    log_channel_block = source[log_channel_start:log_channel_end]

    assert "run_set_warn_limit_slash_command," in source
    assert "run_check_warning_slash_command," in source
    assert "from bot_app.commands.slash_guild_settings_handlers import run_set_log_channel_slash_command" in source
    assert "await run_set_warn_limit_slash_command(" in warn_limit_block
    assert "update_warn_max(interaction.guild.id, 한도)" not in warn_limit_block
    assert "await run_check_warning_slash_command(" in warn_check_block
    assert "await load_warning(interaction.guild.id, 사용자.id)" not in warn_check_block
    assert "get_warn_max(interaction.guild.id)" not in warn_check_block
    assert "await run_set_log_channel_slash_command(" in log_channel_block
    assert "update_log_channel(interaction.guild.id" not in log_channel_block
    assert "update_block_log_channel(interaction.guild.id" not in log_channel_block
