from datetime import datetime, timezone
from types import SimpleNamespace

import discord
import pytest

from bot_app.services.ai_support_service import (
    clear_summary_cooldown,
    load_moderation_log_snapshot,
    reset_chat_history,
    scan_link_safety,
    validate_embed_output,
)
from bot_app.types.readability_contracts import ModerationLogEntry
from bot_app.ui.moderation_log_view import ModerationLogView


class FakeAiSupportRepository:
    def __init__(self):
        self.reset_calls = []
        self.entries = ()

    def reset_chat_history(self, user_id: int) -> None:
        self.reset_calls.append(user_id)

    def load_moderation_log_entries(
        self,
        server_id: int,
        *,
        target_user_id: int | None = None,
        admin_id: int | None = None,
        include_legacy: bool = False,
    ):
        self.last_load = {
            "server_id": server_id,
            "target_user_id": target_user_id,
            "admin_id": admin_id,
            "include_legacy": include_legacy,
        }
        return self.entries


def test_reset_chat_history_returns_named_result():
    repository = FakeAiSupportRepository()

    result = reset_chat_history(10, repository=repository)

    assert result.status == "completed"
    assert result.user_id == 10
    assert result.cleared is True
    assert repository.reset_calls == [10]


def test_load_moderation_log_snapshot_counts_current_and_legacy_entries():
    repository = FakeAiSupportRepository()
    repository.entries = (
        ModerationLogEntry(
            entry_id=1,
            target_user_id=20,
            admin_user_id=30,
            reason="경고",
            type_label="warn",
            extra_value=1,
            source_table="blockhistory",
        ),
        ModerationLogEntry(
            entry_id=2,
            target_user_id=21,
            admin_user_id=31,
            reason="타임아웃",
            type_label="timeout",
            extra_value=180,
            source_table="blockhistory_old",
        ),
    )

    snapshot = load_moderation_log_snapshot(
        1,
        target_user_id=20,
        admin_id=None,
        include_legacy=True,
        repository=repository,
    )

    assert snapshot.status == "found"
    assert snapshot.server_id == 1
    assert snapshot.target_user_id == 20
    assert snapshot.include_legacy is True
    assert snapshot.current_entry_count == 1
    assert snapshot.legacy_entry_count == 1
    assert snapshot.total_entries == 2


def test_clear_summary_cooldown_reports_cleared_and_missing_states():
    cooldown_store = {10: 123.0}

    cleared_result = clear_summary_cooldown(10, cooldown_store)
    missing_result = clear_summary_cooldown(99, cooldown_store)

    assert cleared_result.status == "cleared"
    assert cleared_result.removed is True
    assert 10 not in cooldown_store
    assert missing_result.status == "missing"
    assert missing_result.removed is False


def test_validate_embed_output_returns_named_reason_codes():
    whitelist_result = validate_embed_output(
        title_text="안전한 제목",
        body_text="안전한 내용",
        guild_id=1,
        using_server_id=1,
        requester_role_ids=(100,),
        spam_whitelist_role_ids=(100,),
        raid_keywords=("금지",),
        automod_keywords=("차단",),
    )
    discord_link_result = validate_embed_output(
        title_text="제목",
        body_text="discord.gg/test",
        guild_id=1,
        using_server_id=1,
        requester_role_ids=(),
        spam_whitelist_role_ids=(),
        raid_keywords=(),
        automod_keywords=(),
    )
    reserved_word_result = validate_embed_output(
        title_text="제목",
        body_text="이 내용은 완료 문구를 포함합니다.",
        guild_id=2,
        using_server_id=1,
        requester_role_ids=(),
        spam_whitelist_role_ids=(),
        raid_keywords=(),
        automod_keywords=(),
    )

    assert whitelist_result.status == "ok"
    assert discord_link_result.status == "discord_link"
    assert reserved_word_result.status == "reserved_word"


@pytest.mark.asyncio
async def test_scan_link_safety_normalizes_scan_result():
    async def fake_scan_url(_link: str):
        return {
            "malicious": 0,
            "suspicious": 2,
            "harmless": 5,
            "undetected": 1,
        }

    discord_link_snapshot = await scan_link_safety("discord.gg/test", scan_url=fake_scan_url)
    scan_snapshot = await scan_link_safety("https://example.com", scan_url=fake_scan_url)

    assert discord_link_snapshot.status == "discord_link"
    assert scan_snapshot.status == "ok"
    assert scan_snapshot.severity == "suspicious"
    assert scan_snapshot.stats.total_engines == 8


def test_moderation_log_view_renders_named_entries_without_magic_index():
    entries = (
        ModerationLogEntry(
            entry_id=1,
            target_user_id=20,
            admin_user_id=30,
            reason="경고 사유",
            type_label="warn",
            extra_value=2,
        ),
        ModerationLogEntry(
            entry_id=2,
            target_user_id=21,
            admin_user_id=31,
            reason="타임아웃 사유",
            type_label="timeout",
            extra_value=180,
        ),
    )
    view = ModerationLogView(entries, SimpleNamespace(__str__=lambda self: "테스트"), SimpleNamespace(id=10))

    embed = view.get_embed()

    assert embed.fields[0].name == "경고 - #1"
    assert "사용자: <@20>" in embed.fields[0].value
    assert "개수: +2" in embed.fields[0].value
    assert embed.fields[1].name == "타임아웃 - #2"
    assert "기간: 3분" in embed.fields[1].value


def test_moderation_log_view_preserves_legacy_timeout_boundary_format():
    entries = (
        ModerationLogEntry(
            entry_id=3,
            target_user_id=22,
            admin_user_id=32,
            reason="정확히 한 시간",
            type_label="timeout",
            extra_value=3600,
        ),
        ModerationLogEntry(
            entry_id=4,
            target_user_id=23,
            admin_user_id=33,
            reason="정확히 하루",
            type_label="timeout",
            extra_value=86400,
        ),
    )
    view = ModerationLogView(entries, "테스트", SimpleNamespace(id=10))

    embed = view.get_embed()

    assert "기간: 1시간" in embed.fields[0].value
    assert "0분" not in embed.fields[0].value
    assert "기간: 1일" in embed.fields[1].value
    assert "0시간" not in embed.fields[1].value
