from __future__ import annotations

from pathlib import Path

from bot_app.repositories.admin_support_repository import admin_support_repository
from bot_app.repositories.file_storage import file_storage_repository
from bot_app.types.readability_contracts import (
    BlockHistoryMutationResult,
    ChannelBackupLookupResult,
    ChannelBackupManifest,
    ChannelBackupMessage,
    ChannelBackupWriteResult,
    InviteRouteEntry,
    InviteRouteMemoUpdateResult,
    InviteRouteReport,
    RoleDescriptionUpdateResult,
    RoleInfoSnapshot,
    UserJoinRouteLookupResult,
)


def update_role_description_entry(
    *,
    server_id: int,
    role_id: int,
    description: str | None,
    repository=admin_support_repository,
) -> RoleDescriptionUpdateResult:
    repository.update_role_description(server_id, role_id, description)
    return RoleDescriptionUpdateResult(status="updated", description=description)


def build_role_info_snapshot(
    *,
    role,
    server_id: int,
    permission_map: dict[str, str],
    repository=admin_support_repository,
) -> RoleInfoSnapshot:
    """Build the named role info snapshot while preserving legacy presentation rules."""
    description = repository.get_role_description(server_id, role.id) or "*(설명 없음)*"
    enabled_permissions = tuple(
        permission_map.get(permission_name, permission_name)
        for permission_name, enabled in role.permissions
        if enabled
    )

    if role.permissions.manage_roles or role.permissions.administrator or role.permissions.moderate_members or role.permissions.kick_members or role.permissions.ban_members:
        guild_roles = sorted(role.guild.roles, key=lambda item: item.position, reverse=True)
        cannot_moderate_role_mentions = tuple(item.mention for item in guild_roles if item.position >= role.position)
    else:
        cannot_moderate_role_mentions = ("*(관련 권한 없음)*",)

    sorted_members = sorted(role.members, key=lambda member: member.display_name)
    member_mentions = tuple(member.mention for member in sorted_members)

    return RoleInfoSnapshot(
        role_name=role.name,
        role_mention=role.mention,
        role_id=role.id,
        color_label=role.color,
        member_count=len(role.members),
        description=description,
        enabled_permissions=enabled_permissions,
        member_mentions=member_mentions,
        cannot_moderate_role_mentions=cannot_moderate_role_mentions,
    )


async def update_invite_route_memo_entry(
    *,
    server_id: int,
    invite_code: str,
    memo: str | None,
    repository=admin_support_repository,
) -> InviteRouteMemoUpdateResult:
    updated_memo = await repository.update_invite_route_memo(server_id, invite_code, memo)
    return InviteRouteMemoUpdateResult(status="updated", invite_code=invite_code, memo=updated_memo)


async def build_invite_route_report(
    *,
    server_id: int,
    user_id: int,
    repository=admin_support_repository,
) -> InviteRouteReport:
    raw_entries = repository.import_invite_log(server_id, user_id)
    rendered_entries: list[InviteRouteEntry] = []
    for invite_code in raw_entries:
        if invite_code is None:
            rendered_entries.append(
                InviteRouteEntry(
                    invite_code=None,
                    memo=None,
                    rendered_label="*(알 수 없음)*",
                )
            )
            continue
        memo = await repository.get_invite_route_memo(server_id, invite_code)
        if memo is None:
            rendered_entries.append(
                InviteRouteEntry(
                    invite_code=invite_code,
                    memo=None,
                    rendered_label=f"링크 {invite_code}",
                )
            )
            continue
        rendered_entries.append(
            InviteRouteEntry(
                invite_code=invite_code,
                memo=memo,
                rendered_label=f"링크 {invite_code} (유입 경로 메모: {memo})",
            )
        )

    if len(rendered_entries) == 1 and rendered_entries[0].invite_code is None:
        return InviteRouteReport(status="unknown", entries=tuple(rendered_entries))
    return InviteRouteReport(status="known", entries=tuple(rendered_entries))


def update_user_join_route_entry(
    *,
    user_id: int,
    join_route: str,
    repository=admin_support_repository,
) -> UserJoinRouteLookupResult:
    repository.update_user_join_route(user_id, join_route)
    return UserJoinRouteLookupResult(status="found", join_route=join_route)


def get_user_join_route_entry(
    *,
    user_id: int,
    repository=admin_support_repository,
) -> UserJoinRouteLookupResult:
    join_route = repository.get_user_join_route(user_id)
    if join_route is None:
        return UserJoinRouteLookupResult(status="missing")
    return UserJoinRouteLookupResult(status="found", join_route=join_route)


def delete_blockhistory_entry(
    *,
    entry_id: int,
    repository=admin_support_repository,
) -> BlockHistoryMutationResult:
    repository.remove_blockhistory(entry_id)
    return BlockHistoryMutationResult(status="deleted", entry_id=entry_id)


def add_blockhistory_entry(
    *,
    user_id: int,
    admin_id: int,
    reason: str,
    type_label: str,
    extra_value: int,
    server_id: int,
    repository=admin_support_repository,
) -> BlockHistoryMutationResult:
    repository.add_blockhistory(user_id, admin_id, reason, type_label, extra_value, server_id)
    return BlockHistoryMutationResult(
        status="added",
        user_id=user_id,
        admin_id=admin_id,
        type_label=type_label,
        extra_value=extra_value,
    )


def build_channel_backup_message(
    *,
    author_id: int,
    content: str,
    attachment_filenames: tuple[str, ...],
) -> ChannelBackupMessage:
    return ChannelBackupMessage(
        author_id=author_id,
        content=content,
        attachment_filenames=attachment_filenames,
    )


def _serialize_channel_backup_manifest(manifest: ChannelBackupManifest) -> list[dict[str, object]]:
    return [
        {
            "id": message.author_id,
            "내용": message.content,
            "첨부파일": list(message.attachment_filenames),
        }
        for message in manifest.messages
    ]


def write_channel_backup_manifest(
    *,
    base_folder: str,
    backup_name: str,
    manifest: ChannelBackupManifest,
    repository=file_storage_repository,
) -> ChannelBackupWriteResult:
    backup_path = Path(base_folder) / backup_name
    backup_path.mkdir(parents=True, exist_ok=True)
    repository.write_json(
        str(backup_path / "messages.json"),
        _serialize_channel_backup_manifest(manifest),
        ensure_ascii=False,
        indent=4,
    )
    return ChannelBackupWriteResult(status="written", backup_path=str(backup_path), message_count=len(manifest.messages))


def load_channel_backup_manifest(
    *,
    base_folder: str,
    backup_name: str,
    repository=file_storage_repository,
) -> ChannelBackupLookupResult:
    backup_path = Path(base_folder) / backup_name
    messages_path = backup_path / "messages.json"
    raw_messages = repository.read_json(str(messages_path), default=None, recover_decode_error=False)
    if raw_messages is None:
        return ChannelBackupLookupResult(status="missing", backup_path=str(backup_path))

    manifest = ChannelBackupManifest(
        messages=tuple(
            ChannelBackupMessage(
                author_id=int(raw_message["id"]),
                content=str(raw_message["내용"]),
                attachment_filenames=tuple(str(filename) for filename in raw_message["첨부파일"]),
            )
            for raw_message in raw_messages
        )
    )
    return ChannelBackupLookupResult(status="found", backup_path=str(backup_path), manifest=manifest)
