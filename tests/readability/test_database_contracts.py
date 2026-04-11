from bot_app.repositories.settings_repository import SettingsRepository
from bot_app.repositories.xp_repository import XpRepository
from bot_app.types.readability_contracts import AutomodConfig, AutomodRuleConfig, XpSetting


def test_xp_repository_coerces_legacy_setting_to_named_contract(monkeypatch):
    monkeypatch.setattr(
        "bot_app.repositories.xp_repository.get_xp_setting_dict",
        lambda server_id: [True, 15, 30, None, None, "XP"],
    )

    repository = XpRepository()

    assert repository.get_xp_setting(1) == XpSetting(
        enabled=True,
        chat_xp=15,
        chat_xp_cooldown=30,
        voice_xp=None,
        voice_xp_cooldown=None,
        unit="XP",
    )


def test_settings_repository_coerces_legacy_automod_to_named_contract(monkeypatch):
    monkeypatch.setattr(
        "bot_app.repositories.settings_repository.get_automod",
        lambda server_id: {
            "political": [True, 10],
            "sexual": [False, 0],
            "invite_link": [True, 60],
            "mention": [False, 0],
            "whitelist_permission": "manage_messages",
        },
    )

    repository = SettingsRepository()

    assert repository.get_automod(1) == AutomodConfig(
        political=AutomodRuleConfig(enabled=True, action=10),
        sexual=AutomodRuleConfig(enabled=False, action=0),
        invite_link=AutomodRuleConfig(enabled=True, action=60),
        mention=AutomodRuleConfig(enabled=False, action=0),
        whitelist_permission="manage_messages",
    )
