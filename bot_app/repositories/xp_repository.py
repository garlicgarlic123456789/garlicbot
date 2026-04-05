from commands.database import (
    get_all_month_xp,
    get_all_xp,
    get_attendance_settings,
    get_month_xp,
    get_old_xp,
    get_xp,
    get_xp_setting_dict,
    process_attendance,
    update_month_xp,
    update_xp,
)
from bot_app.types.readability_contracts import XpSetting


def _build_xp_setting(raw_setting: list | tuple) -> XpSetting:
    enabled, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit = raw_setting
    return XpSetting(
        enabled=bool(enabled),
        chat_xp=chat_xp,
        chat_xp_cooldown=chat_xp_cooldown,
        voice_xp=voice_xp,
        voice_xp_cooldown=voice_xp_cooldown,
        unit=unit or "",
    )


class XpRepository:
    def get_xp_setting(self, server_id: int) -> XpSetting:
        return _build_xp_setting(get_xp_setting_dict(server_id))

    async def get_attendance_settings(self, server_id: int):
        return await get_attendance_settings(server_id)

    def process_attendance(self, server_id: int, user_id: int):
        return process_attendance(server_id, user_id)

    def add_xp(self, server_id: int, user_id: int, amount: int):
        update_xp(server_id, user_id, amount)

    def add_month_xp(self, server_id: int, user_id: int, amount: int):
        update_month_xp(server_id, user_id, amount)

    def get_xp(self, server_id: int, user_id: int) -> int:
        return get_xp(server_id, user_id)

    def get_month_xp(self, server_id: int, user_id: int) -> int:
        return get_month_xp(server_id, user_id)

    def get_old_xp(self, server_id: int, user_id: int) -> int:
        return get_old_xp(server_id, user_id)

    def get_all_xp(self, server_id: int):
        return get_all_xp(server_id)

    def get_all_month_xp(self, server_id: int):
        return get_all_month_xp(server_id)


xp_repository = XpRepository()
