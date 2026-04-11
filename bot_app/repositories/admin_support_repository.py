from __future__ import annotations

from commands.database import (
    add_blockhistory,
    get_role_description,
    get_server_join_route_memo,
    get_user_join_route,
    import_invite_log,
    remove_blockhistory,
    save_invite_log,
    update_role_description,
    update_server_join_route_memo,
    update_user_join_route,
)


class AdminSupportRepository:
    def update_role_description(self, server_id: int, role_id: int, description: str | None):
        update_role_description(server_id, role_id, description)

    def get_role_description(self, server_id: int, role_id: int) -> str | None:
        return get_role_description(server_id, role_id)

    async def update_invite_route_memo(self, server_id: int, invite_code: str, memo: str | None) -> str | None:
        return await update_server_join_route_memo(server_id, invite_code, memo)

    async def get_invite_route_memo(self, server_id: int, invite_code: str) -> str | None:
        return await get_server_join_route_memo(server_id, invite_code)

    def import_invite_log(self, server_id: int, user_id: int) -> list[str | None]:
        return import_invite_log(server_id, user_id)

    def update_user_join_route(self, user_id: int, join_route: str):
        update_user_join_route(user_id, join_route)

    def get_user_join_route(self, user_id: int) -> str | None:
        return get_user_join_route(user_id)

    def remove_blockhistory(self, entry_id: int):
        remove_blockhistory(entry_id)

    def add_blockhistory(
        self,
        user_id: int,
        admin_id: int,
        reason: str,
        type_label: str,
        extra_value: int,
        server_id: int,
    ):
        add_blockhistory(user_id, admin_id, reason, type_label, extra_value, server_id)

    def save_invite_log(self, user_id: int, invite_code: str | None, server_id: int):
        save_invite_log(user_id, invite_code, server_id)


admin_support_repository = AdminSupportRepository()
