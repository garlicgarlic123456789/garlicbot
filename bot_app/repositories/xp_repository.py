from commands.database import (
    get_attendance_settings,
    get_xp_setting_dict,
    process_attendance,
    update_month_xp,
    update_xp,
)
from bot_app.types.readability_contracts import XpSetting


class XpRepository:
    def get_xp_setting(self, server_id: int):
        setting = get_xp_setting_dict(server_id)
        return XpSetting(
            enabled=bool(setting[0]),
            chat_xp=setting[1],
            chat_xp_cooldown=setting[2],
            voice_xp=setting[3],
            voice_xp_cooldown=setting[4],
            unit=setting[5] or "",
        )

    async def get_attendance_settings(self, server_id: int):
        return await get_attendance_settings(server_id)

    def process_attendance(self, server_id: int, user_id: int):
        return process_attendance(server_id, user_id)

    def add_xp(self, server_id: int, user_id: int, amount: int):
        update_xp(server_id, user_id, amount)

    def add_month_xp(self, server_id: int, user_id: int, amount: int):
        update_month_xp(server_id, user_id, amount)


xp_repository = XpRepository()
