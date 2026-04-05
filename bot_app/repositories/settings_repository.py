from commands.database import (
    get_automod,
    get_automod_exception_channel,
    get_block_log_channel,
    update_block_log_channel,
    update_log_channel,
)
from bot_app.types.readability_contracts import AutomodConfig, AutomodRuleConfig, GuildLogChannelSelection


def _build_rule_config(raw_rule: list | tuple) -> AutomodRuleConfig:
    enabled, action = raw_rule
    return AutomodRuleConfig(enabled=enabled, action=action)


class SettingsRepository:
    def get_automod(self, server_id: int) -> AutomodConfig:
        raw = get_automod(server_id)
        return AutomodConfig(
            political=_build_rule_config(raw["political"]),
            sexual=_build_rule_config(raw["sexual"]),
            invite_link=_build_rule_config(raw["invite_link"]),
            mention=_build_rule_config(raw["mention"]),
            whitelist_permission=raw["whitelist_permission"],
        )

    def is_automod_exception_channel(self, server_id: int, channel_id: int):
        return get_automod_exception_channel(server_id, channel_id)

    def get_block_log_channel(self, server_id: int):
        return get_block_log_channel(server_id)

    def update_guild_log_channels(self, server_id: int, selection: GuildLogChannelSelection):
        update_log_channel(server_id, selection.editdelete, selection.reaction, selection.role, selection.image)
        update_block_log_channel(server_id, selection.block)


settings_repository = SettingsRepository()
