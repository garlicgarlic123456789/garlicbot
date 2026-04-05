from commands.database import add_blockhistory, add_warning, get_warn_max, load_warning, remove_warning, set_warning, update_warn_max


class ModerationRepository:
    def get_warn_max(self, server_id: int):
        return get_warn_max(server_id)

    async def add_warning(self, server_id: int, user_id: int, amount: int):
        return await add_warning(server_id, user_id, amount)

    async def remove_warning(self, server_id: int, user_id: int, amount: int):
        return await remove_warning(server_id, user_id, amount)

    async def reset_warning(self, server_id: int, user_id: int):
        return await set_warning(server_id, user_id, 0)

    def add_blockhistory(self, user_id: int, admin_id: int, reason: str, type_: str, addinfo: int, server_id: int):
        add_blockhistory(user_id, admin_id, reason, type_, addinfo, server_id)

    async def get_warning_count(self, server_id: int, user_id: int):
        return await load_warning(server_id, user_id)

    def update_warn_max(self, server_id: int, max_warn: int | None):
        update_warn_max(server_id, max_warn)


moderation_repository = ModerationRepository()
