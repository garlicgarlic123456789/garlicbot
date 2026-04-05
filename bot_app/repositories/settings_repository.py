from commands.database import get_automod, get_automod_exception_channel, get_block_log_channel


class SettingsRepository:
    def get_automod(self, server_id: int):
        return get_automod(server_id)

    def is_automod_exception_channel(self, server_id: int, channel_id: int):
        return get_automod_exception_channel(server_id, channel_id)

    def get_block_log_channel(self, server_id: int):
        return get_block_log_channel(server_id)


settings_repository = SettingsRepository()
