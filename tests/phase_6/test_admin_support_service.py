from pathlib import Path
from types import SimpleNamespace

from bot_app.services.admin_support_service import (
    add_blockhistory_entry,
    build_channel_backup_message,
    build_invite_route_report,
    build_role_info_snapshot,
    delete_blockhistory_entry,
    get_user_join_route_entry,
    load_channel_backup_manifest,
    update_invite_route_memo_entry,
    update_role_description_entry,
    update_user_join_route_entry,
    write_channel_backup_manifest,
)


class FakeRepository:
    def __init__(self):
        self.role_descriptions = {}
        self.invite_memos = {}
        self.invite_logs = {}
        self.join_routes = {}
        self.deleted_ids = []
        self.added_entries = []

    def update_role_description(self, server_id, role_id, description):
        self.role_descriptions[(server_id, role_id)] = description

    def get_role_description(self, server_id, role_id):
        return self.role_descriptions.get((server_id, role_id))

    async def update_invite_route_memo(self, server_id, invite_code, memo):
        self.invite_memos[(server_id, invite_code)] = memo
        return memo

    async def get_invite_route_memo(self, server_id, invite_code):
        return self.invite_memos.get((server_id, invite_code))

    def import_invite_log(self, server_id, user_id):
        return self.invite_logs.get((server_id, user_id), [None])

    def update_user_join_route(self, user_id, join_route):
        self.join_routes[user_id] = join_route

    def get_user_join_route(self, user_id):
        return self.join_routes.get(user_id)

    def remove_blockhistory(self, entry_id):
        self.deleted_ids.append(entry_id)

    def add_blockhistory(self, user_id, admin_id, reason, type_label, extra_value, server_id):
        self.added_entries.append((user_id, admin_id, reason, type_label, extra_value, server_id))


class FakeStorageRepository:
    def __init__(self):
        self.written = {}

    def write_json(self, path, data, *, ensure_ascii=False, indent=4):
        self.written[path] = data
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        import json

        file_path.write_text(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8")

    def read_json(self, path, *, default, recover_decode_error=False):
        file_path = Path(path)
        if not file_path.exists():
            return default
        import json

        return json.loads(file_path.read_text(encoding="utf-8"))


class FakePermissions:
    def __init__(self, pairs):
        self._pairs = tuple(pairs)
        self.manage_roles = True
        self.administrator = False
        self.moderate_members = False
        self.kick_members = False
        self.ban_members = True

    def __iter__(self):
        return iter(self._pairs)


def test_update_role_description_entry_returns_named_result():
    repository = FakeRepository()

    result = update_role_description_entry(
        server_id=1,
        role_id=2,
        description="설명",
        repository=repository,
    )

    assert result.status == "updated"
    assert repository.role_descriptions[(1, 2)] == "설명"


def test_build_role_info_snapshot_keeps_legacy_sorting_and_defaults():
    repository = FakeRepository()
    permission_map = {"manage_roles": "역할 관리하기", "ban_members": "멤버 차단"}
    role = SimpleNamespace(
        id=30,
        name="관리자",
        mention="<@&30>",
        color="#ffffff",
        permissions=[
            ("manage_roles", True),
            ("ban_members", True),
            ("send_messages", False),
        ],
        members=[
            SimpleNamespace(display_name="다", mention="<@3>"),
            SimpleNamespace(display_name="가", mention="<@1>"),
            SimpleNamespace(display_name="나", mention="<@2>"),
        ],
    )
    role.permissions = FakePermissions([("manage_roles", True), ("ban_members", True), ("send_messages", False)])
    role.guild = SimpleNamespace(
        roles=[
            SimpleNamespace(position=10, mention="<@&99>"),
            SimpleNamespace(position=5, mention="<@&30>"),
            SimpleNamespace(position=2, mention="<@&1>"),
        ]
    )
    role.position = 5

    snapshot = build_role_info_snapshot(
        role=role,
        server_id=1,
        permission_map=permission_map,
        repository=repository,
    )

    assert snapshot.description == "*(설명 없음)*"
    assert snapshot.enabled_permissions == ("역할 관리하기", "멤버 차단")
    assert snapshot.member_mentions == ("<@1>", "<@2>", "<@3>")
    assert snapshot.cannot_moderate_role_mentions == ("<@&99>", "<@&30>")


async def _build_report(repository):
    return await build_invite_route_report(server_id=1, user_id=10, repository=repository)


def test_build_invite_route_report_formats_unknown_and_memo_entries():
    repository = FakeRepository()
    repository.invite_logs[(1, 10)] = [None, "abc", "def"]
    repository.invite_memos[(1, "def")] = "테스트 메모"

    import asyncio

    report = asyncio.run(_build_report(repository))

    assert report.status == "known"
    assert [entry.rendered_label for entry in report.entries] == [
        "*(알 수 없음)*",
        "링크 abc",
        "링크 def (유입 경로 메모: 테스트 메모)",
    ]


def test_user_join_route_service_roundtrip_and_blockhistory_results():
    repository = FakeRepository()

    update_result = update_user_join_route_entry(user_id=10, join_route="트위터", repository=repository)
    lookup_result = get_user_join_route_entry(user_id=10, repository=repository)
    delete_result = delete_blockhistory_entry(entry_id=7, repository=repository)
    add_result = add_blockhistory_entry(
        user_id=10,
        admin_id=20,
        reason="테스트",
        type_label="warn",
        extra_value=2,
        server_id=1,
        repository=repository,
    )

    assert update_result.join_route == "트위터"
    assert lookup_result.status == "found"
    assert lookup_result.join_route == "트위터"
    assert delete_result.status == "deleted"
    assert repository.deleted_ids == [7]
    assert add_result.status == "added"
    assert repository.added_entries == [(10, 20, "테스트", "warn", 2, 1)]


def test_channel_backup_manifest_roundtrip(tmp_path):
    storage_repository = FakeStorageRepository()
    manifest = (
        build_channel_backup_message(author_id=10, content="안녕", attachment_filenames=("0_a.png",)),
        build_channel_backup_message(author_id=20, content="", attachment_filenames=("1_b.png", "2_c.png")),
    )

    write_result = write_channel_backup_manifest(
        base_folder=str(tmp_path),
        backup_name="wave3-test",
        manifest=SimpleNamespace(messages=manifest),
        repository=storage_repository,
    )
    lookup_result = load_channel_backup_manifest(
        base_folder=str(tmp_path),
        backup_name="wave3-test",
        repository=storage_repository,
    )

    assert write_result.status == "written"
    assert write_result.message_count == 2
    assert lookup_result.status == "found"
    assert lookup_result.manifest.messages[0].author_id == 10
    assert lookup_result.manifest.messages[0].attachment_filenames == ("0_a.png",)
    assert lookup_result.manifest.messages[1].attachment_filenames == ("1_b.png", "2_c.png")


def test_update_invite_route_memo_entry_returns_named_result():
    repository = FakeRepository()

    import asyncio

    result = asyncio.run(update_invite_route_memo_entry(server_id=1, invite_code="abc", memo="메모", repository=repository))

    assert result.status == "updated"
    assert repository.invite_memos[(1, "abc")] == "메모"
