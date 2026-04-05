from pathlib import Path
from importlib import import_module

import pytest

from bot_app.repositories.xp_repository import XpRepository
from bot_app.services.xp_service import apply_message_xp, process_attendance_reward
from bot_app.types.readability_contracts import MessageXpApplyResult, XpSetting


class FakeXpRepository:
    def __init__(self, *, xp_setting=None, attendance_settings=None, attendance_result=(True, 1)):
        self._xp_setting = xp_setting or XpSetting(True, 15, 30, None, None, "XP")
        self._attendance_settings = attendance_settings or {
            "on_off": True,
            "minimum": 100,
            "maximum": 200,
            "step": 10,
        }
        self._attendance_result = attendance_result
        self.add_xp_calls = []
        self.add_month_xp_calls = []

    def get_xp_setting(self, server_id: int):
        return self._xp_setting

    async def get_attendance_settings(self, server_id: int):
        return self._attendance_settings

    def process_attendance(self, server_id: int, user_id: int):
        return self._attendance_result

    def add_xp(self, server_id: int, user_id: int, amount: int):
        self.add_xp_calls.append((server_id, user_id, amount))

    def add_month_xp(self, server_id: int, user_id: int, amount: int):
        self.add_month_xp_calls.append((server_id, user_id, amount))


class FakeRandom:
    def __init__(self, values):
        self.values = list(values)

    def randrange(self, start, stop=None, step=1):
        value = self.values.pop(0)
        assert start <= value < stop
        assert (value - start) % step == 0
        return value


def test_apply_message_xp_skips_when_feature_missing():
    result = apply_message_xp(
        server_id=1,
        user_id=2,
        xp_settings={},
        last_exp_time={},
        now_monotonic=10.0,
        repository=FakeXpRepository(),
    )

    assert result == MessageXpApplyResult(status="skipped_missing_setting", awarded_xp=0)


def test_apply_message_xp_updates_without_cooldown():
    repository = FakeXpRepository(xp_setting=XpSetting(True, 25, 0, None, None, "XP"))

    result = apply_message_xp(
        server_id=1,
        user_id=2,
        xp_settings={1: [True, 25, 0, None, None, "XP"]},
        last_exp_time={},
        now_monotonic=10.0,
        repository=repository,
    )

    assert result == MessageXpApplyResult(status="awarded", awarded_xp=25)
    assert repository.add_xp_calls == [(1, 2, 25)]
    assert repository.add_month_xp_calls == [(1, 2, 25)]


def test_apply_message_xp_respects_cooldown():
    repository = FakeXpRepository()
    last_exp_time = {1: {2: 95.0}}

    result = apply_message_xp(
        server_id=1,
        user_id=2,
        xp_settings={1: [True, 15, 10, None, None, "XP"]},
        last_exp_time=last_exp_time,
        now_monotonic=100.0,
        repository=repository,
    )

    assert result == MessageXpApplyResult(status="skipped_cooldown", awarded_xp=0)
    assert repository.add_xp_calls == []
    assert repository.add_month_xp_calls == []


def test_apply_message_xp_records_cooldown_timestamp_when_awarded():
    repository = FakeXpRepository()
    last_exp_time = {}

    result = apply_message_xp(
        server_id=1,
        user_id=2,
        xp_settings={1: [True, 15, 10, None, None, "XP"]},
        last_exp_time=last_exp_time,
        now_monotonic=100.0,
        repository=repository,
    )

    assert result == MessageXpApplyResult(status="awarded", awarded_xp=15)
    assert last_exp_time == {1: {2: 100.0}}
    assert repository.add_xp_calls == [(1, 2, 15)]
    assert repository.add_month_xp_calls == [(1, 2, 15)]


@pytest.mark.asyncio
async def test_process_attendance_reward_handles_disabled_xp():
    repository = FakeXpRepository(xp_setting=XpSetting(False, 15, 30, None, None, "XP"))

    result = await process_attendance_reward(
        server_id=1,
        user_id=2,
        user_role_ids=set(),
        xp_settings={1: [False, 15, 30, None, None, "XP"]},
        using_server=999,
        server_booster_role_id=123,
        repository=repository,
    )

    assert result.status == "xp_disabled"
    assert repository.add_xp_calls == []


@pytest.mark.asyncio
async def test_process_attendance_reward_handles_already_checked():
    repository = FakeXpRepository(attendance_result=(False, 3))

    result = await process_attendance_reward(
        server_id=1,
        user_id=2,
        user_role_ids=set(),
        xp_settings={1: [True, 15, 30, None, None, "XP"]},
        using_server=999,
        server_booster_role_id=123,
        repository=repository,
    )

    assert result.status == "already_checked"
    assert result.streak == 3
    assert repository.add_xp_calls == []


@pytest.mark.asyncio
async def test_process_attendance_reward_awards_expected_bonus_flow():
    repository = FakeXpRepository(attendance_result=(True, 8))
    rng = FakeRandom([60, 120, 150, 700])

    result = await process_attendance_reward(
        server_id=1,
        user_id=2,
        user_role_ids={555},
        xp_settings={1: [True, 15, 30, None, None, "마늘"]},
        using_server=1,
        server_booster_role_id=555,
        repository=repository,
        rng=rng,
    )

    assert result.status == "success"
    assert result.streak == 8
    assert result.check_xp == 150
    assert result.boost_check_xp == 700
    assert result.streak_bonus == 180
    assert result.total_xp == 1030
    assert result.unit == "마늘"
    assert repository.add_xp_calls == [(1, 2, 1030)]
    assert repository.add_month_xp_calls == [(1, 2, 1030)]


def test_main_routes_message_xp_and_attendance_through_service_boundary():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "from bot_app.services.xp_service import (" in source
    assert "apply_message_xp," in source
    assert "process_attendance_reward," in source
    assert "apply_message_xp(" in source
    assert "reward_result = await process_attendance_reward(" in source
    assert "MessageXpApplyResult" in Path("bot_app/services/xp_service.py").read_text(encoding="utf-8")
    assert 'if interaction.guild.id not in xp_setting or xp_setting[interaction.guild.id][0] == False :' in source
    assert 'if reward_result.status == "attendance_disabled":' in source
    assert 'if reward_result.status == "already_checked":' in source
    assert "attendance_check, streak = process_attendance(" not in source


@pytest.mark.asyncio
async def test_xp_repository_delegates_to_database_helpers(monkeypatch):
    calls = []
    xp_repository_module = import_module("bot_app.repositories.xp_repository")

    def fake_get_xp_setting_dict(server_id):
        calls.append(("get_xp_setting", server_id))
        return [True, 15, 30, None, None, "XP"]

    async def fake_get_attendance_settings(server_id):
        calls.append(("get_attendance_settings", server_id))
        return {"on_off": True}

    def fake_process_attendance(server_id, user_id):
        calls.append(("process_attendance", server_id, user_id))
        return True, 2

    def fake_update_xp(server_id, user_id, amount):
        calls.append(("add_xp", server_id, user_id, amount))

    def fake_update_month_xp(server_id, user_id, amount):
        calls.append(("add_month_xp", server_id, user_id, amount))

    monkeypatch.setattr(xp_repository_module, "get_xp_setting_dict", fake_get_xp_setting_dict)
    monkeypatch.setattr(xp_repository_module, "get_attendance_settings", fake_get_attendance_settings)
    monkeypatch.setattr(xp_repository_module, "process_attendance", fake_process_attendance)
    monkeypatch.setattr(xp_repository_module, "update_xp", fake_update_xp)
    monkeypatch.setattr(xp_repository_module, "update_month_xp", fake_update_month_xp)

    repository = XpRepository()

    assert repository.get_xp_setting(1) == XpSetting(True, 15, 30, None, None, "XP")
    assert await repository.get_attendance_settings(1) == {"on_off": True}
    assert repository.process_attendance(1, 2) == (True, 2)
    repository.add_xp(1, 2, 30)
    repository.add_month_xp(1, 2, 40)

    assert calls == [
        ("get_xp_setting", 1),
        ("get_attendance_settings", 1),
        ("process_attendance", 1, 2),
        ("add_xp", 1, 2, 30),
        ("add_month_xp", 1, 2, 40),
    ]
