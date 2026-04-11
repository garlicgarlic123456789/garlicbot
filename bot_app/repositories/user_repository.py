from __future__ import annotations

import sqlite3

from commands.database import get_premium, load_warning


class UserRepository:
    """Expose the legacy user-related persistence helpers through named methods."""

    async def get_warning_count(self, server_id: int, user_id: int) -> int:
        return await load_warning(server_id, user_id)

    def has_premium(self, user_id: int) -> bool:
        return get_premium(user_id)

    def get_user_money(self, user_id: int) -> int | None:
        conn = sqlite3.connect("garlicbot.db", isolation_level=None)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return int(row[0])


user_repository = UserRepository()
