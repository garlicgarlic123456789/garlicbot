from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class LikeabilityRepository:
    """Persist likeability scores in the legacy JSON file format."""

    def __init__(self, file_path: str | Path = "likeability.json"):
        self.file_path = Path(file_path)
        self._lock = Lock()

    def _load_scores(self) -> dict[str, int]:
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_scores(self, scores: dict[str, int]) -> None:
        self.file_path.write_text(
            json.dumps(scores, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_score(self, user_id: int | str) -> int:
        scores = self._load_scores()
        return int(scores.get(str(user_id), 0))

    def add_score(self, user_id: int | str, delta: int) -> int:
        with self._lock:
            scores = self._load_scores()
            key = str(user_id)
            scores[key] = int(scores.get(key, 0)) + delta
            self._save_scores(scores)
            return int(scores[key])


likeability_repository = LikeabilityRepository()
