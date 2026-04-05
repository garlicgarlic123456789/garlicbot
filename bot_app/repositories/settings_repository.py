from commands.database import get_automod, get_automod_exception_channel, get_block_log_channel
from bot_app.types.readability_contracts import AutomodConfig, AutomodRuleConfig


class SettingsRepository:
    def get_automod(self, server_id: int):
        raw = get_automod(server_id)
        return AutomodConfig(
            political=AutomodRuleConfig(enabled=raw["political"][0], action=raw["political"][1]),
            sexual=AutomodRuleConfig(enabled=raw["sexual"][0], action=raw["sexual"][1]),
            invite_link=AutomodRuleConfig(enabled=raw["invite_link"][0], action=raw["invite_link"][1]),
            mention=AutomodRuleConfig(enabled=raw["mention"][0], action=raw["mention"][1]),
            whitelist_permission=raw["whitelist_permission"],
        )

    def is_automod_exception_channel(self, server_id: int, channel_id: int):
        return get_automod_exception_channel(server_id, channel_id)

    def get_block_log_channel(self, server_id: int):
        return get_block_log_channel(server_id)


settings_repository = SettingsRepository()
