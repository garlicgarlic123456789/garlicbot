from __future__ import annotations

import json
from pathlib import Path

import aiofiles


class FileStorageRepository:
    def read_json(self, path: str, *, default, recover_decode_error: bool = False):
        file_path = Path(path)
        if not file_path.exists():
            return default
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError:
            if recover_decode_error:
                return default
            raise

    def write_json(self, path: str, data, *, ensure_ascii=False, indent=4):
        file_path = Path(path)
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=ensure_ascii, indent=indent)

    def read_text(self, path: str, *, default: str = "") -> str:
        file_path = Path(path)
        if not file_path.exists():
            return default
        return file_path.read_text(encoding="utf-8")

    def write_text(self, path: str, content: str):
        Path(path).write_text(content, encoding="utf-8")

    async def read_lines_async(self, path: str) -> list[str]:
        file_path = Path(path)
        if not file_path.exists():
            return []
        async with aiofiles.open(file_path, mode="r", encoding="utf-8") as handle:
            lines = await handle.readlines()
        return [line.rstrip("\n") for line in lines]

    async def write_lines_async(self, path: str, lines):
        async with aiofiles.open(Path(path), mode="w", encoding="utf-8") as handle:
            await handle.writelines(f"{line}\n" for line in lines)


file_storage_repository = FileStorageRepository()
