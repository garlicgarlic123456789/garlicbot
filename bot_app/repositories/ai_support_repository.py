from __future__ import annotations

import sqlite3

from commands.database import reset_gpt_chat_thread

from bot_app.types.readability_contracts import ModerationLogEntry


class AiSupportRepository:
    """Bridge legacy AI/support storage and SQLite reads behind named contracts."""

    def reset_chat_history(self, user_id: int) -> None:
        """Clear the stored Gemini/OpenAI thread history for one user."""

        reset_gpt_chat_thread(user_id)

    def load_moderation_log_entries(
        self,
        server_id: int,
        *,
        target_user_id: int | None = None,
        admin_id: int | None = None,
        include_legacy: bool = False,
    ) -> tuple[ModerationLogEntry, ...]:
        """Load normalized moderation log entries from current and legacy tables."""

        entries = list(
            self._load_blockhistory_rows(
                server_id,
                target_user_id=target_user_id,
                admin_id=admin_id,
            )
        )
        if include_legacy:
            entries.extend(
                self._load_legacy_blockhistory_rows(
                    target_user_id=target_user_id,
                    admin_id=admin_id,
                )
            )
        return tuple(entries)

    def _load_blockhistory_rows(
        self,
        server_id: int,
        *,
        target_user_id: int | None,
        admin_id: int | None,
    ) -> tuple[ModerationLogEntry, ...]:
        rows = self._execute_query(
            self._build_blockhistory_query(
                server_id,
                target_user_id=target_user_id,
                admin_id=admin_id,
            )
        )
        return tuple(self._build_entry_from_row(row, source_table="blockhistory") for row in rows)

    def _load_legacy_blockhistory_rows(
        self,
        *,
        target_user_id: int | None,
        admin_id: int | None,
    ) -> tuple[ModerationLogEntry, ...]:
        rows = self._execute_query(
            self._build_legacy_blockhistory_query(
                target_user_id=target_user_id,
                admin_id=admin_id,
            )
        )
        return tuple(self._build_entry_from_row(row, source_table="blockhistory_old") for row in rows)

    @staticmethod
    def _execute_query(query_payload: tuple[str, tuple[object, ...]]) -> tuple[tuple, ...]:
        query, params = query_payload
        connection = sqlite3.connect("garlicbot.db", isolation_level=None)
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            return tuple(cursor.fetchall())
        finally:
            connection.close()

    @staticmethod
    def _build_blockhistory_query(
        server_id: int,
        *,
        target_user_id: int | None,
        admin_id: int | None,
    ) -> tuple[str, tuple[object, ...]]:
        if target_user_id is not None and admin_id is not None:
            return (
                "SELECT id, user_id, admin_id, reason, type, addinfo FROM blockhistory WHERE user_id = ? AND admin_id = ? AND server_id = ? ORDER BY id DESC",
                (target_user_id, admin_id, server_id),
            )
        if target_user_id is not None:
            return (
                "SELECT id, user_id, admin_id, reason, type, addinfo FROM blockhistory WHERE user_id = ? AND server_id = ? ORDER BY id DESC",
                (target_user_id, server_id),
            )
        if admin_id is not None:
            return (
                "SELECT id, user_id, admin_id, reason, type, addinfo FROM blockhistory WHERE admin_id = ? AND server_id = ? ORDER BY id DESC",
                (admin_id, server_id),
            )
        return (
            "SELECT id, user_id, admin_id, reason, type, addinfo FROM blockhistory WHERE server_id = ? ORDER BY id DESC",
            (server_id,),
        )

    @staticmethod
    def _build_legacy_blockhistory_query(
        *,
        target_user_id: int | None,
        admin_id: int | None,
    ) -> tuple[str, tuple[object, ...]]:
        if target_user_id is not None and admin_id is not None:
            return (
                "SELECT output_id, user_id, admin_id, reason, type, addinfo FROM blockhistory_old WHERE user_id = ? AND admin_id = ?",
                (target_user_id, admin_id),
            )
        if target_user_id is not None:
            return (
                "SELECT output_id, user_id, admin_id, reason, type, addinfo FROM blockhistory_old WHERE user_id = ?",
                (target_user_id,),
            )
        if admin_id is not None:
            return (
                "SELECT output_id, user_id, admin_id, reason, type, addinfo FROM blockhistory_old WHERE admin_id = ?",
                (admin_id,),
            )
        return (
            "SELECT output_id, user_id, admin_id, reason, type, addinfo FROM blockhistory_old",
            (),
        )

    @staticmethod
    def _build_entry_from_row(
        row: tuple,
        *,
        source_table: str,
    ) -> ModerationLogEntry:
        entry_id, user_id, admin_id, reason, type_label, addinfo = row[:6]
        return ModerationLogEntry(
            entry_id=entry_id,
            target_user_id=user_id,
            admin_user_id=admin_id,
            reason=reason,
            type_label=type_label,
            extra_value=addinfo,
            source_table=source_table,
        )


ai_support_repository = AiSupportRepository()
