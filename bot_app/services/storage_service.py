from __future__ import annotations

from bot_app.repositories.file_storage import file_storage_repository


def load_mentions_data(path: str, repository=file_storage_repository):
    return repository.read_json(path, default=[], recover_decode_error=False)


def save_mentions_data(path: str, data, repository=file_storage_repository):
    repository.write_json(path, data, ensure_ascii=False, indent=4)


async def read_confidential_message_ids(path: str, repository=file_storage_repository):
    lines = await repository.read_lines_async(path)
    return {line.strip() for line in lines if line.strip()}


async def write_confidential_message_ids(path: str, messages, repository=file_storage_repository):
    await repository.write_lines_async(path, messages)


def read_auto_verify_state(path: str, repository=file_storage_repository) -> str:
    content = repository.read_text(path, default="파일이 존재하지 않습니다.")
    return content.strip() if content else ""


def write_auto_verify_state(path: str, content: str, repository=file_storage_repository):
    repository.write_text(path, content)


def load_suggestions_data(path: str, repository=file_storage_repository):
    return repository.read_json(path, default=[], recover_decode_error=False)


def save_suggestions_data(path: str, suggestions, repository=file_storage_repository):
    repository.write_json(path, suggestions, ensure_ascii=False, indent=2)


def load_command_blocked_users(path: str, repository=file_storage_repository):
    return repository.read_json(path, default={}, recover_decode_error=True)


def save_command_blocked_users(path: str, data, repository=file_storage_repository):
    repository.write_json(path, data, ensure_ascii=False, indent=4)
