from datetime import datetime, timedelta, timezone

from pathlib import Path

import discord
import pytest

from bot_app.events.member_events import (
    build_block_action_embed,
    build_member_departure_embed,
    build_role_change_embed,
    build_welcome_embed,
    prune_recent_members,
    register_member_events,
    resolve_used_invite,
    should_assign_autorole,
)
from tests.helpers.fakes import FakeBot, FakeGuild, FakeMember, FakeRole, FakeTextChannel


def test_should_assign_autorole_respects_target_type():
    assert should_assign_autorole("all", is_bot=False) is True
    assert should_assign_autorole("user", is_bot=False) is True
    assert should_assign_autorole("user", is_bot=True) is False
    assert should_assign_autorole("bot", is_bot=True) is True
    assert should_assign_autorole("bot", is_bot=False) is False


def test_prune_recent_members_keeps_only_interval_members():
    now = datetime.now(timezone.utc)
    recent_member = type("Member", (), {"joined_at": now - timedelta(seconds=10)})()
    old_member = type("Member", (), {"joined_at": now - timedelta(seconds=80)})()

    result = prune_recent_members([recent_member, old_member], now=now, interval_seconds=60)

    assert result == [recent_member]


def test_resolve_used_invite_detects_incremented_invite():
    invite_before = type("Invite", (), {"code": "abc", "uses": 1})()
    invite_after = type("Invite", (), {"code": "abc", "uses": 2})()
    untouched = type("Invite", (), {"code": "def", "uses": 3})()

    result = resolve_used_invite([invite_after, untouched], [invite_before, untouched])

    assert result is invite_after


def test_build_member_departure_embed_keeps_message_format():
    embed = build_member_departure_embed("<@1>")

    assert embed.title == "회원 탈퇴 알림"
    assert "<@1>님이 철도역에서 떠나셨습니다." in embed.description


def test_build_welcome_embed_supports_detailed_variant():
    embed = build_welcome_embed(
        member_mention="<@1>",
        display_name="마늘",
        time_text="12시 34분",
        train_number=777,
        platform_number=3,
        detailed=True,
    )

    assert embed.title == "환영합니다!"
    assert "<@1>님이 철도역에 도착하셨습니다." in embed.description
    assert "타는 곳 3번" in embed.description
    assert "<id:customize>" in embed.description


def test_build_block_and_role_embeds_keep_expected_fields():
    block_embed = build_block_action_embed(
        title="타임아웃",
        color=discord.Color.red(),
        user_mention="<@1>",
        moderator_mention="<@2>",
        duration_text="5분",
        reason="사유",
    )
    role_embed = build_role_change_embed(
        title="역할 부여",
        color=int("a5f0ff", 16),
        user_mention="<@1>",
        role_mention="<@&3>",
    )

    assert block_embed.fields[2].value == "5분"
    assert block_embed.fields[3].value == "사유"
    assert role_embed.fields[1].value == "<@&3>"


def test_register_member_events_registers_all_member_handlers():
    bot = FakeBot()

    register_member_events(
        bot,
        {
            "state": {
                "recent_joins": {},
                "invite_cache": {},
                "last_member_join_mention": None,
            },
            "using_server": 0,
            "byebye_channel": 0,
            "message_log": 0,
            "get_block_log_channel": lambda guild_id: 0,
            "add_blockhistory": lambda *args, **kwargs: None,
            "process_anti_nuke_ban": lambda *args, **kwargs: None,
            "get_anti_raid_settings": lambda guild_id: {"on_off": False},
            "get_quarantine_role": lambda guild_id: 0,
            "save_invite_log": lambda *args, **kwargs: None,
            "get_autorole": lambda guild_id: [],
            "verify_role": 0,
            "greeting_channel": 0,
            "get_log_channel": lambda guild_id: {"role": None},
            "add_mention_delay_user": lambda *args, **kwargs: None,
            "format_duration": lambda duration: "0초",
        },
    )

    assert set(bot.registered_events) == {
        "on_member_remove",
        "on_member_ban",
        "on_member_unban",
        "on_member_join",
        "on_member_update",
    }


def test_main_keeps_member_event_registration_boundary():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "register_member_events(" in source
    assert '"state": member_event_state' in source
    assert '"get_anti_raid_settings": get_anti_raid_settings' in source
    assert '"format_duration": format_duration' in source


@pytest.mark.asyncio
async def test_on_member_join_updates_invite_cache_and_assigns_matching_autorole():
    bot = FakeBot()
    guild = FakeGuild(100)
    role = FakeRole(200)
    guild.roles[200] = role

    old_invite = type("Invite", (), {"code": "abc", "uses": 1})()
    new_invite = type("Invite", (), {"code": "abc", "uses": 2})()
    guild._invites = [new_invite]

    saved_logs = []
    member = FakeMember(
        10,
        guild=guild,
        joined_at=datetime.now(timezone.utc),
    )

    async def fake_get_anti_raid_settings(guild_id):
        return {"on_off": False}

    async def fake_get_autorole(guild_id):
        return [{"bot_user": "user", "role_id": 200}]

    register_member_events(
        bot,
        {
            "state": {
                "recent_joins": {},
                "invite_cache": {100: [old_invite]},
                "last_member_join_mention": None,
            },
            "using_server": 0,
            "byebye_channel": 0,
            "message_log": 0,
            "get_block_log_channel": lambda guild_id: 0,
            "add_blockhistory": lambda *args, **kwargs: None,
            "process_anti_nuke_ban": lambda *args, **kwargs: None,
            "get_anti_raid_settings": fake_get_anti_raid_settings,
            "get_quarantine_role": lambda guild_id: 0,
            "save_invite_log": lambda *args: saved_logs.append(args),
            "get_autorole": fake_get_autorole,
            "verify_role": 0,
            "greeting_channel": 0,
            "get_log_channel": lambda guild_id: {"role": None},
            "add_mention_delay_user": lambda *args, **kwargs: None,
            "format_duration": lambda duration: "0초",
        },
    )

    await bot.registered_events["on_member_join"](member)

    assert saved_logs == [(10, "abc", 100)]
    assert member.added_roles[0]["role"] is role


@pytest.mark.asyncio
async def test_on_member_update_sends_welcome_embeds_for_verify_role():
    bot = FakeBot()
    guild = FakeGuild(300)
    greeting_channel = FakeTextChannel(channel_id=400)
    mention_channel = FakeTextChannel(channel_id=1483037564159131762)
    verify_role = FakeRole(500)
    guild.channels[400] = greeting_channel
    guild.channels[1483037564159131762] = mention_channel

    before = FakeMember(11, guild=guild, roles=[guild.default_role])
    after = FakeMember(11, guild=guild, roles=[guild.default_role, verify_role])

    register_member_events(
        bot,
        {
            "state": {
                "recent_joins": {},
                "invite_cache": {},
                "last_member_join_mention": None,
            },
            "using_server": 300,
            "byebye_channel": 0,
            "message_log": 0,
            "get_block_log_channel": lambda guild_id: 0,
            "add_blockhistory": lambda *args, **kwargs: None,
            "process_anti_nuke_ban": lambda *args, **kwargs: None,
            "get_anti_raid_settings": lambda guild_id: {"on_off": False},
            "get_quarantine_role": lambda guild_id: 0,
            "save_invite_log": lambda *args, **kwargs: None,
            "get_autorole": lambda guild_id: [],
            "verify_role": 500,
            "greeting_channel": 400,
            "get_log_channel": lambda guild_id: {"role": None},
            "add_mention_delay_user": lambda *args, **kwargs: None,
            "format_duration": lambda duration: "0초",
        },
    )

    await bot.registered_events["on_member_update"](before, after)

    assert len(greeting_channel.sent_embeds) == 1
    assert greeting_channel.sent_embeds[0].title == "환영합니다!"
    assert len(mention_channel.sent_embeds) == 1
    assert mention_channel.sent_messages[0]["content"] == "<@11>"


@pytest.mark.asyncio
async def test_on_member_update_logs_role_changes():
    bot = FakeBot()
    guild = FakeGuild(301)
    role_log_channel = FakeTextChannel(channel_id=777)
    bot.channels[777] = role_log_channel
    new_role = FakeRole(900)

    before = FakeMember(12, guild=guild, roles=[guild.default_role])
    after = FakeMember(12, guild=guild, roles=[guild.default_role, new_role])

    register_member_events(
        bot,
        {
            "state": {
                "recent_joins": {},
                "invite_cache": {},
                "last_member_join_mention": None,
            },
            "using_server": 0,
            "byebye_channel": 0,
            "message_log": 0,
            "get_block_log_channel": lambda guild_id: 0,
            "add_blockhistory": lambda *args, **kwargs: None,
            "process_anti_nuke_ban": lambda *args, **kwargs: None,
            "get_anti_raid_settings": lambda guild_id: {"on_off": False},
            "get_quarantine_role": lambda guild_id: 0,
            "save_invite_log": lambda *args, **kwargs: None,
            "get_autorole": lambda guild_id: [],
            "verify_role": 0,
            "greeting_channel": 0,
            "get_log_channel": lambda guild_id: {"role": 777},
            "add_mention_delay_user": lambda *args, **kwargs: None,
            "format_duration": lambda duration: "0초",
        },
    )

    await bot.registered_events["on_member_update"](before, after)

    assert len(role_log_channel.sent_embeds) == 1
    assert role_log_channel.sent_embeds[0].title == "역할 부여"
