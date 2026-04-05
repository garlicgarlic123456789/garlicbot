import json
from importlib import import_module
from pathlib import Path

import pytest

from bot_app.repositories.file_storage import FileStorageRepository
from bot_app.services.storage_service import (
    load_command_blocked_users,
    load_mentions_data,
    load_suggestions_data,
    read_auto_verify_state,
    read_confidential_message_ids,
    save_command_blocked_users,
    save_mentions_data,
    save_suggestions_data,
    write_auto_verify_state,
    write_confidential_message_ids,
)


class FakeFileStorageRepository:
    def __init__(self):
        self.calls = []
        self.json_value = []
        self.text_value = ""
        self.lines_value = []

    def read_json(self, path: str, *, default, recover_decode_error=False):
        self.calls.append(("read_json", path, default, recover_decode_error))
        return self.json_value

    def write_json(self, path: str, data, *, ensure_ascii=False, indent=4):
        self.calls.append(("write_json", path, data, ensure_ascii, indent))

    def read_text(self, path: str, *, default: str = "") -> str:
        self.calls.append(("read_text", path, default))
        return self.text_value

    def write_text(self, path: str, content: str):
        self.calls.append(("write_text", path, content))

    async def read_lines_async(self, path: str):
        self.calls.append(("read_lines_async", path))
        return self.lines_value

    async def write_lines_async(self, path: str, lines):
        self.calls.append(("write_lines_async", path, list(lines)))


def test_storage_service_wraps_json_and_text_file_access():
    repository = FakeFileStorageRepository()
    repository.json_value = [{"id": 1}]
    repository.text_value = " 42 \n"

    assert load_mentions_data("mentions.json", repository=repository) == [{"id": 1}]
    save_mentions_data("mentions.json", [{"id": 2}], repository=repository)
    assert read_auto_verify_state("auto_verify.txt", repository=repository) == "42"
    write_auto_verify_state("auto_verify.txt", "hello", repository=repository)
    assert load_suggestions_data("suggestions.json", repository=repository) == [{"id": 1}]
    save_suggestions_data("suggestions.json", [{"id": 3}], repository=repository)
    assert load_command_blocked_users("blocked.json", repository=repository) == [{"id": 1}]
    save_command_blocked_users("blocked.json", {"1": {"until": "2099-01-01"}}, repository=repository)

    assert repository.calls == [
        ("read_json", "mentions.json", [], False),
        ("write_json", "mentions.json", [{"id": 2}], False, 4),
        ("read_text", "auto_verify.txt", "파일이 존재하지 않습니다."),
        ("write_text", "auto_verify.txt", "hello"),
        ("read_json", "suggestions.json", [], False),
        ("write_json", "suggestions.json", [{"id": 3}], False, 2),
        ("read_json", "blocked.json", {}, True),
        ("write_json", "blocked.json", {"1": {"until": "2099-01-01"}}, False, 4),
    ]


@pytest.mark.asyncio
async def test_storage_service_wraps_async_confidential_message_io():
    repository = FakeFileStorageRepository()
    repository.lines_value = [" alpha ", "beta", ""]

    assert await read_confidential_message_ids("secret.txt", repository=repository) == {"alpha", "beta"}
    await write_confidential_message_ids("secret.txt", ["x", "y"], repository=repository)

    assert repository.calls == [
        ("read_lines_async", "secret.txt"),
        ("write_lines_async", "secret.txt", ["x", "y"]),
    ]


def test_file_storage_repository_handles_missing_and_invalid_json(tmp_path: Path):
    repository = FileStorageRepository()
    missing_path = tmp_path / "missing.json"
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not json}", encoding="utf-8")

    assert repository.read_json(str(missing_path), default=[]) == []
    with pytest.raises(json.JSONDecodeError):
        repository.read_json(str(invalid_path), default={})
    assert repository.read_json(str(invalid_path), default={}, recover_decode_error=True) == {}


@pytest.mark.asyncio
async def test_file_storage_repository_handles_text_and_lines(tmp_path: Path):
    repository = FileStorageRepository()
    text_path = tmp_path / "state.txt"
    lines_path = tmp_path / "secret.txt"

    repository.write_text(str(text_path), "hello")
    assert repository.read_text(str(text_path), default="fallback") == "hello"
    assert repository.read_text(str(tmp_path / "none.txt"), default="fallback") == "fallback"

    await repository.write_lines_async(str(lines_path), ["a", "b"])
    assert await repository.read_lines_async(str(lines_path)) == ["a", "b"]


def test_main_and_define_use_storage_service_boundaries():
    main_source = Path("main.py").read_text(encoding="utf-8")
    define_source = Path("commands/define.py").read_text(encoding="utf-8")

    assert "from bot_app.services.storage_service import (" in main_source
    assert "load_mentions_data" in main_source
    assert "read_confidential_message_ids" in main_source
    assert "write_auto_verify_state" in main_source
    assert "load_suggestions_data" in main_source
    assert 'with open(MENTION_FILE, "r"' not in main_source
    assert 'with open(MENTION_FILE, "w"' not in main_source
    assert "aiofiles.open(secret_file_name" not in main_source
    assert 'with open(FILE_PATH, "w"' not in main_source
    assert 'with open(FILE_PATH, "r"' not in main_source
    assert "load_command_blocked_users" in define_source
    assert "save_command_blocked_users" in define_source
    assert 'with open(BLOCKED_USERS_FILE, "r"' not in define_source
    assert 'with open(BLOCKED_USERS_FILE, "w"' not in define_source


def test_file_storage_repository_delegates_basic_json_io(tmp_path: Path):
    calls = []
    file_storage_module = import_module("bot_app.repositories.file_storage")
    repository = FileStorageRepository()
    target = tmp_path / "data.json"

    original_json_dump = file_storage_module.json.dump
    original_json_load = file_storage_module.json.load

    def fake_json_dump(data, handle, ensure_ascii=False, indent=4):
        calls.append(("json.dump", data, ensure_ascii, indent))
        return original_json_dump(data, handle, ensure_ascii=ensure_ascii, indent=indent)

    def fake_json_load(handle):
        calls.append(("json.load", target.name))
        return original_json_load(handle)

    file_storage_module.json.dump = fake_json_dump
    file_storage_module.json.load = fake_json_load
    try:
        repository.write_json(str(target), {"ok": True}, ensure_ascii=False, indent=2)
        assert repository.read_json(str(target), default={}) == {"ok": True}
    finally:
        file_storage_module.json.dump = original_json_dump
        file_storage_module.json.load = original_json_load

    assert calls == [
        ("json.dump", {"ok": True}, False, 2),
        ("json.load", "data.json"),
    ]
