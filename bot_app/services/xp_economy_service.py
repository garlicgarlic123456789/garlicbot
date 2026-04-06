from __future__ import annotations

from bot_app.repositories.xp_repository import xp_repository
from bot_app.types.readability_contracts import (
    GambleOfferResult,
    GambleSettlementResult,
    XpShopItemSpec,
    XpShopPurchaseResult,
)


SHOP_ITEMS = {
    "file": XpShopItemSpec(item_key="file", name="파일 첨부 권한", price=3000, role_id=1333390128072232980),
    "vote": XpShopItemSpec(item_key="vote", name="투표 생성 권한", price=7000, role_id=1320315949005537310),
    "private_thread": XpShopItemSpec(item_key="private_thread", name="비공개 스레드 생성 권한", price=7000, role_id=1320600850082693172),
    "soundboard": XpShopItemSpec(item_key="soundboard", name="사운드보드 사용 권한", price=10000, role_id=1398550480707256433),
}
MANUAL_ONLY_ITEMS = {"add_answer", "pin", "unwarn"}


def purchase_shop_item(
    *,
    server_id: int,
    user_id: int,
    item_key: str,
    using_server: int,
    owned_role_ids: set[int],
    repository=xp_repository,
) -> XpShopPurchaseResult:
    """Apply the legacy XP shop purchase rules and return the named result."""
    if server_id != using_server:
        return XpShopPurchaseResult(status="unsupported_server")

    if item_key in MANUAL_ONLY_ITEMS:
        return XpShopPurchaseResult(status="manual_only_item")

    item_spec = SHOP_ITEMS.get(item_key)
    if item_spec is None:
        return XpShopPurchaseResult(status="invalid_item")

    if item_spec.role_id in owned_role_ids:
        return XpShopPurchaseResult(status="already_owned", item_spec=item_spec)

    if repository.get_xp(server_id, user_id) < item_spec.price:
        return XpShopPurchaseResult(status="insufficient_balance", item_spec=item_spec)

    repository.add_xp(server_id, user_id, -item_spec.price)
    repository.add_month_xp(server_id, user_id, -item_spec.price)
    return XpShopPurchaseResult(status="success", item_spec=item_spec)


def create_gamble_offer(
    *,
    amount: int,
    choice: str,
    unit: str,
) -> GambleOfferResult:
    """Validate the gamble amount while keeping the caller-owned XP enabled check."""
    if amount < 1:
        return GambleOfferResult(status="amount_too_small", unit=unit, choice=choice)
    if amount > 1000000:
        return GambleOfferResult(status="amount_too_large", unit=unit, choice=choice)
    return GambleOfferResult(status="created", amount=amount, unit=unit, choice=choice)


def resolve_gamble_round(
    *,
    server_id: int,
    creator_user_id: int,
    participant_user_id: int,
    amount: int,
    correct_choice: str,
    selected_choice: str,
    unit: str,
    repository=xp_repository,
) -> GambleSettlementResult:
    """Apply the legacy gamble settlement and report the winner/loser contract."""
    if repository.get_xp(server_id, participant_user_id) < amount:
        return GambleSettlementResult(status="participant_insufficient_balance", amount=amount, unit=unit)
    if repository.get_xp(server_id, creator_user_id) < amount:
        return GambleSettlementResult(status="creator_insufficient_balance", amount=amount, unit=unit)

    winner_id = participant_user_id if selected_choice == correct_choice else creator_user_id
    loser_id = creator_user_id if winner_id == participant_user_id else participant_user_id
    repository.add_xp(server_id, winner_id, amount)
    repository.add_month_xp(server_id, winner_id, amount)
    repository.add_xp(server_id, loser_id, -amount)
    repository.add_month_xp(server_id, loser_id, -amount)
    return GambleSettlementResult(
        status="completed",
        winner_id=winner_id,
        loser_id=loser_id,
        correct_choice=correct_choice,
        amount=amount,
        unit=unit,
    )
