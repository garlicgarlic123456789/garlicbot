from __future__ import annotations

import sqlite3

from bot_app.types.readability_contracts import RouteRecord


class RailRepository:
    """Wrap direct rail/route sqlite access behind named methods."""

    def _connect(self):
        return sqlite3.connect("garlicbot.db", isolation_level=None)

    def ensure_user_exists(self, user_id: int) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)", (user_id,))
            exists = cursor.fetchone()[0]
            if not exists:
                cursor.execute("INSERT INTO users (user_id, money) VALUES (?, ?)", (user_id, 0))

    def insert_rail(self, *, owner_id: int, channel_id: int, rail_count: int, rail_name: str) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO rails (owner_id, channel_id, rail_cnt, name) VALUES (?, ?, ?, ?)",
                (owner_id, channel_id, rail_count, rail_name),
            )

    def rail_exists(self, channel_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM rails WHERE channel_id = ?)", (channel_id,))
            return bool(cursor.fetchone()[0])

    def count_routes(self, channel_id: int) -> int:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM routes WHERE channel_id = ?", (channel_id,))
            return int(cursor.fetchone()[0])

    def insert_route(
        self,
        *,
        owner_id: int,
        channel_id: int,
        dispatch_interval: int,
        route_name: str,
        train_name: str,
    ) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO routes (owner_id, channel_id, dispatch_interval, name, train) VALUES (?, ?, ?, ?, ?)",
                (owner_id, channel_id, dispatch_interval, route_name, train_name),
            )

    def get_route_record(self, *, channel_id: int, route_name: str) -> RouteRecord | None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, owner_id FROM routes WHERE channel_id = ? AND name = ?",
                (channel_id, route_name),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return RouteRecord(route_id=row[0], owner_id=row[1])

    def delete_route(self, route_id: int) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM routes WHERE id = ?", (route_id,))

    def update_route_dispatch_interval(self, *, route_id: int, dispatch_interval: int) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE routes
                SET dispatch_interval = ?
                WHERE id = ?
                """,
                (dispatch_interval, route_id),
            )


rail_repository = RailRepository()
