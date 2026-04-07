from bot_app.services.rail_service import create_rail, create_route, delete_route, update_route_dispatch_interval
from bot_app.types.readability_contracts import RouteRecord


class FakeRailRepository:
    def __init__(self):
        self.ensure_user_calls = []
        self.inserted_rails = []
        self.inserted_routes = []
        self.route_count = 0
        self.rail_exists_value = True
        self.route_record = None
        self.deleted_route_id = None
        self.updated_route = None
        self.raise_rail_integrity = False
        self.raise_route_integrity = False

    def ensure_user_exists(self, user_id: int) -> None:
        self.ensure_user_calls.append(user_id)

    def insert_rail(self, *, owner_id: int, channel_id: int, rail_count: int, rail_name: str) -> None:
        if self.raise_rail_integrity:
            import sqlite3

            raise sqlite3.IntegrityError("duplicate rail")
        self.inserted_rails.append((owner_id, channel_id, rail_count, rail_name))

    def rail_exists(self, channel_id: int) -> bool:
        return self.rail_exists_value

    def count_routes(self, channel_id: int) -> int:
        return self.route_count

    def insert_route(self, *, owner_id: int, channel_id: int, dispatch_interval: int, route_name: str, train_name: str) -> None:
        if self.raise_route_integrity:
            import sqlite3

            raise sqlite3.IntegrityError("duplicate route")
        self.inserted_routes.append((owner_id, channel_id, dispatch_interval, route_name, train_name))

    def get_route_record(self, *, channel_id: int, route_name: str):
        return self.route_record

    def delete_route(self, route_id: int) -> None:
        self.deleted_route_id = route_id

    def update_route_dispatch_interval(self, *, route_id: int, dispatch_interval: int) -> None:
        self.updated_route = (route_id, dispatch_interval)


def test_create_rail_returns_named_statuses():
    repository = FakeRailRepository()

    created_result = create_rail(user_id=1, channel_id=2, rail_name="노선", rail_count=2, repository=repository)
    repository.raise_rail_integrity = True
    duplicate_result = create_rail(user_id=1, channel_id=2, rail_name="노선", rail_count=2, repository=repository)
    too_many_result = create_rail(user_id=1, channel_id=2, rail_name="노선", rail_count=5, repository=repository)
    invalid_result = create_rail(user_id=1, channel_id=2, rail_name="노선", rail_count="두개", repository=repository)

    assert created_result.status == "created"
    assert duplicate_result.status == "already_exists"
    assert too_many_result.status == "too_many_tracks"
    assert invalid_result.status == "invalid_input"


def test_create_route_respects_legacy_single_route_limit():
    repository = FakeRailRepository()
    repository.route_count = 1

    limited_result = create_route(
        user_id=1,
        channel_id=2,
        route_name="노선",
        train_name="중전철",
        dispatch_interval=4,
        repository=repository,
    )

    assert limited_result.status == "temporary_single_route_limit"


def test_route_creation_and_update_cover_remaining_error_statuses():
    repository = FakeRailRepository()
    repository.rail_exists_value = False

    missing_rail_result = create_route(
        user_id=1,
        channel_id=2,
        route_name="노선",
        train_name="중전철",
        dispatch_interval=4,
        repository=repository,
    )

    repository.rail_exists_value = True
    invalid_dispatch_result = create_route(
        user_id=1,
        channel_id=2,
        route_name="노선",
        train_name="중전철",
        dispatch_interval="네분",
        repository=repository,
    )
    invalid_train_result = create_route(
        user_id=1,
        channel_id=2,
        route_name="노선",
        train_name="고속철",
        dispatch_interval=4,
        repository=repository,
    )

    repository.raise_route_integrity = True
    duplicate_name_result = create_route(
        user_id=1,
        channel_id=2,
        route_name="노선",
        train_name="중전철",
        dispatch_interval=4,
        repository=repository,
    )

    repository.route_record = RouteRecord(route_id=10, owner_id=1)
    route_missing_result = update_route_dispatch_interval(
        user_id=1,
        channel_id=2,
        route_name="없는노선",
        dispatch_interval=5,
        repository=FakeRailRepository(),
    )
    interval_too_small_result = update_route_dispatch_interval(
        user_id=1,
        channel_id=2,
        route_name="노선",
        dispatch_interval=1,
        repository=repository,
    )
    invalid_input_result = update_route_dispatch_interval(
        user_id=1,
        channel_id=2,
        route_name="노선",
        dispatch_interval="한분",
        repository=repository,
    )

    assert missing_rail_result.status == "rail_missing"
    assert invalid_dispatch_result.status == "invalid_input"
    assert invalid_train_result.status == "invalid_input"
    assert duplicate_name_result.status == "duplicate_name"
    assert route_missing_result.status == "route_missing"
    assert interval_too_small_result.status == "interval_too_small"
    assert invalid_input_result.status == "invalid_input"


def test_delete_route_and_update_dispatch_interval_use_named_results():
    repository = FakeRailRepository()
    repository.route_record = RouteRecord(route_id=10, owner_id=1)

    deleted_result = delete_route(user_id=1, channel_id=2, route_name="노선", repository=repository)
    updated_result = update_route_dispatch_interval(
        user_id=1,
        channel_id=2,
        route_name="노선",
        dispatch_interval=5,
        repository=repository,
    )
    permission_result = update_route_dispatch_interval(
        user_id=2,
        channel_id=2,
        route_name="노선",
        dispatch_interval=5,
        repository=repository,
    )

    assert deleted_result.status == "deleted"
    assert repository.deleted_route_id == 10
    assert updated_result.status == "updated"
    assert repository.updated_route == (10, 5)
    assert permission_result.status == "permission_denied"
    assert delete_route(user_id=1, channel_id=2, route_name="없는노선", repository=FakeRailRepository()).status == "route_missing"
