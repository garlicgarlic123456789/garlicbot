from __future__ import annotations

import sqlite3

from bot_app.repositories.rail_repository import rail_repository
from bot_app.types.readability_contracts import (
    RailCreationResult,
    RouteCreationResult,
    RouteDeletionResult,
    RouteDispatchIntervalUpdateResult,
)


def create_rail(
    *,
    user_id: int,
    channel_id: int,
    rail_name: str,
    rail_count: int,
    repository=rail_repository,
) -> RailCreationResult:
    """Create one rail row using a named result instead of inline SQL branching."""

    repository.ensure_user_exists(user_id)
    if not isinstance(rail_count, int):
        return RailCreationResult(status="invalid_input")
    if rail_count > 4:
        return RailCreationResult(status="too_many_tracks", rail_count=rail_count, rail_name=rail_name)
    try:
        repository.insert_rail(owner_id=user_id, channel_id=channel_id, rail_count=rail_count, rail_name=rail_name)
    except sqlite3.IntegrityError:
        return RailCreationResult(status="already_exists", rail_count=rail_count, rail_name=rail_name)
    return RailCreationResult(status="created", rail_count=rail_count, rail_name=rail_name)


def create_route(
    *,
    user_id: int,
    channel_id: int,
    route_name: str,
    train_name: str,
    dispatch_interval: int,
    repository=rail_repository,
) -> RouteCreationResult:
    """Create one route while preserving the legacy temporary single-route rule."""

    repository.ensure_user_exists(user_id)
    if not repository.rail_exists(channel_id):
        return RouteCreationResult(status="rail_missing", route_name=route_name, train_name=train_name)
    if not isinstance(dispatch_interval, int):
        return RouteCreationResult(status="invalid_input", route_name=route_name, train_name=train_name)
    if train_name not in {"중전철", "경전철"}:
        return RouteCreationResult(status="invalid_input", route_name=route_name, train_name=train_name)
    if repository.count_routes(channel_id) != 0:
        return RouteCreationResult(
            status="temporary_single_route_limit",
            route_name=route_name,
            train_name=train_name,
            dispatch_interval=dispatch_interval,
        )
    try:
        repository.insert_route(
            owner_id=user_id,
            channel_id=channel_id,
            dispatch_interval=dispatch_interval,
            route_name=route_name,
            train_name=train_name,
        )
    except sqlite3.IntegrityError:
        return RouteCreationResult(
            status="duplicate_name",
            route_name=route_name,
            train_name=train_name,
            dispatch_interval=dispatch_interval,
        )
    return RouteCreationResult(
        status="created",
        route_name=route_name,
        train_name=train_name,
        dispatch_interval=dispatch_interval,
    )


def delete_route(
    *,
    user_id: int,
    channel_id: int,
    route_name: str,
    repository=rail_repository,
) -> RouteDeletionResult:
    """Delete one route row if the caller owns it."""

    route_record = repository.get_route_record(channel_id=channel_id, route_name=route_name)
    if route_record is None:
        return RouteDeletionResult(status="route_missing", route_name=route_name)
    if route_record.owner_id != user_id:
        return RouteDeletionResult(status="permission_denied", route_name=route_name)
    repository.delete_route(route_record.route_id)
    return RouteDeletionResult(status="deleted", route_name=route_name)


def update_route_dispatch_interval(
    *,
    user_id: int,
    channel_id: int,
    route_name: str,
    dispatch_interval: int,
    repository=rail_repository,
) -> RouteDispatchIntervalUpdateResult:
    """Update one route dispatch interval using named status results."""

    route_record = repository.get_route_record(channel_id=channel_id, route_name=route_name)
    if route_record is None:
        return RouteDispatchIntervalUpdateResult(status="route_missing", route_name=route_name)
    if not isinstance(dispatch_interval, int):
        return RouteDispatchIntervalUpdateResult(status="invalid_input", route_name=route_name)
    if dispatch_interval < 2:
        return RouteDispatchIntervalUpdateResult(
            status="interval_too_small",
            route_name=route_name,
            dispatch_interval=dispatch_interval,
        )
    if route_record.owner_id != user_id:
        return RouteDispatchIntervalUpdateResult(status="permission_denied", route_name=route_name)
    repository.update_route_dispatch_interval(route_id=route_record.route_id, dispatch_interval=dispatch_interval)
    return RouteDispatchIntervalUpdateResult(
        status="updated",
        route_name=route_name,
        dispatch_interval=dispatch_interval,
    )
