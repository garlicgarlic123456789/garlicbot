from pathlib import Path

from bot_app.repositories.likeability_repository import LikeabilityRepository
from bot_app.services.likeability_service import force_adjust_likeability, get_likeability_snapshot
from bot_app.types.readability_contracts import LikeabilityAdjustmentResult, LikeabilitySnapshot


def test_get_likeability_snapshot_defaults_to_zero_for_missing_user(tmp_path: Path):
    repository = LikeabilityRepository(tmp_path / "likeability.json")

    result = get_likeability_snapshot(10, repository=repository)

    assert result == LikeabilitySnapshot(score=0)


def test_force_adjust_likeability_persists_updated_score(tmp_path: Path):
    repository = LikeabilityRepository(tmp_path / "likeability.json")

    first_result = force_adjust_likeability(user_id=10, delta=3, repository=repository)
    second_result = force_adjust_likeability(user_id=10, delta=-1, repository=repository)

    assert first_result == LikeabilityAdjustmentResult(delta=3, score=3)
    assert second_result == LikeabilityAdjustmentResult(delta=-1, score=2)
    assert repository.get_score(10) == 2
