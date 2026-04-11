from __future__ import annotations

from bot_app.repositories.likeability_repository import likeability_repository
from bot_app.types.readability_contracts import LikeabilityAdjustmentResult, LikeabilitySnapshot


def get_likeability_snapshot(user_id: int, repository=likeability_repository) -> LikeabilitySnapshot:
    """Return the current likeability score for a user."""
    return LikeabilitySnapshot(score=repository.get_score(user_id))


def force_adjust_likeability(
    *,
    user_id: int,
    delta: int,
    repository=likeability_repository,
) -> LikeabilityAdjustmentResult:
    """Adjust the legacy likeability score without cooldown semantics."""
    new_score = repository.add_score(user_id, delta)
    return LikeabilityAdjustmentResult(delta=delta, score=new_score)
