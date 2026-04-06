from types import SimpleNamespace

from bot_app.services.user_service import (
    build_user_profile_snapshot,
    get_displayed_profile_xp_snapshot,
    get_user_classification,
    get_user_money_lookup,
)
from bot_app.types.readability_contracts import DisplayedXpSnapshot, UserMoneyLookupResult, UserProfileSnapshot


class FakeUserRepository:
    def __init__(self, *, money=None, premium=False):
        self.money = money
        self.premium = premium

    def get_user_money(self, user_id: int):
        return self.money

    def has_premium(self, user_id: int) -> bool:
        return self.premium


class FakeXpSettingRepository:
    def get_xp_setting(self, server_id: int):
        return [True, 5, 60, 0, 0, "XP"]


class FakeXpDataRepository:
    def __init__(self, *, xp: int):
        self.xp = xp
        self.calls = []

    def get_xp(self, server_id: int, user_id: int) -> int:
        self.calls.append((server_id, user_id))
        return self.xp


def test_get_user_money_lookup_returns_found_and_missing_statuses():
    found_repository = FakeUserRepository(money=500)
    missing_repository = FakeUserRepository(money=None)

    assert get_user_money_lookup(10, repository=found_repository) == UserMoneyLookupResult(status="found", money=500)
    assert get_user_money_lookup(10, repository=missing_repository) == UserMoneyLookupResult(status="missing", money=None)


def test_get_user_classification_prefers_blocked_then_premium_then_general():
    blocked_user = SimpleNamespace(id=10)
    premium_user = SimpleNamespace(id=11)
    general_user = SimpleNamespace(id=12)

    assert get_user_classification(
        user=blocked_user,
        block_checker=lambda user: (True, "2099-01-01", "테스트"),
        repository=FakeUserRepository(premium=True),
    ) == ("blocked", "이용제한 유저 (2099-01-01까지, 사유: 테스트)")
    assert get_user_classification(
        user=premium_user,
        block_checker=lambda user: (False, None, None),
        repository=FakeUserRepository(premium=True),
    ) == ("premium", "프리미엄 유저")
    assert get_user_classification(
        user=general_user,
        block_checker=lambda user: (False, None, None),
        repository=FakeUserRepository(premium=False),
    ) == ("general", "일반 유저")


def test_get_displayed_profile_xp_snapshot_preserves_legacy_month_display():
    xp_data_repository = FakeXpDataRepository(xp=1200)

    result = get_displayed_profile_xp_snapshot(
        server_id=1,
        user_id=20,
        xp_settings={},
        xp_setting_repository=FakeXpSettingRepository(),
        xp_data_repository=xp_data_repository,
        leveler=lambda xp: xp // 100,
    )

    assert result == DisplayedXpSnapshot(
        total_xp=1200,
        displayed_month_xp=1200,
        total_level=12,
        displayed_month_level=12,
        unit="XP",
    )
    assert xp_data_repository.calls == [(1, 20), (1, 20)]


def test_build_user_profile_snapshot_returns_named_contract():
    user = SimpleNamespace(
        id=10,
        display_name="마늘",
        display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
    )

    result = build_user_profile_snapshot(
        source="guild_member",
        user=user,
        role_mentions=("<@&1>", "<@&2>"),
        xp_snapshot=DisplayedXpSnapshot(
            total_xp=100,
            displayed_month_xp=100,
            total_level=1,
            displayed_month_level=1,
            unit="XP",
        ),
        account_created_at_label="2026-04-01 12:00:00",
        joined_at_label="2026-04-02 12:00:00",
        warning_count=2,
        restriction_status_label="제한되지 않음",
        classification_status="general",
        classification_label="일반 유저",
    )

    assert result == UserProfileSnapshot(
        source="guild_member",
        user_id=10,
        display_name="마늘",
        mention="<@10>",
        role_mentions=("<@&1>", "<@&2>"),
        xp_snapshot=DisplayedXpSnapshot(
            total_xp=100,
            displayed_month_xp=100,
            total_level=1,
            displayed_month_level=1,
            unit="XP",
        ),
        account_created_at_label="2026-04-01 12:00:00",
        joined_at_label="2026-04-02 12:00:00",
        warning_count=2,
        restriction_status_label="제한되지 않음",
        classification_status="general",
        classification_label="일반 유저",
        avatar_url="https://example.com/avatar.png",
    )
