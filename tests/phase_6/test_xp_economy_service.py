from types import SimpleNamespace

from bot_app.services.xp_economy_service import create_gamble_offer, purchase_shop_item, resolve_gamble_round
from bot_app.types.readability_contracts import GambleOfferResult, GambleSettlementResult, XpShopItemSpec, XpShopPurchaseResult


class FakeXpRepository:
    def __init__(self, *, xp_by_user=None):
        self.xp_by_user = dict(xp_by_user or {})
        self.calls = []

    def get_xp(self, server_id: int, user_id: int) -> int:
        self.calls.append(("get_xp", server_id, user_id))
        return self.xp_by_user.get(user_id, 0)

    def add_xp(self, server_id: int, user_id: int, amount: int):
        self.calls.append(("add_xp", server_id, user_id, amount))
        self.xp_by_user[user_id] = self.xp_by_user.get(user_id, 0) + amount

    def add_month_xp(self, server_id: int, user_id: int, amount: int):
        self.calls.append(("add_month_xp", server_id, user_id, amount))


def test_purchase_shop_item_rejects_manual_only_and_existing_role():
    repository = FakeXpRepository(xp_by_user={10: 10000})

    manual_result = purchase_shop_item(
        server_id=1,
        user_id=10,
        item_key="pin",
        using_server=1,
        owned_role_ids=set(),
        repository=repository,
    )
    owned_result = purchase_shop_item(
        server_id=1,
        user_id=10,
        item_key="vote",
        using_server=1,
        owned_role_ids={1320315949005537310},
        repository=repository,
    )

    assert manual_result == XpShopPurchaseResult(status="manual_only_item")
    assert owned_result == XpShopPurchaseResult(
        status="already_owned",
        item_spec=XpShopItemSpec(item_key="vote", name="투표 생성 권한", price=7000, role_id=1320315949005537310),
    )


def test_purchase_shop_item_deducts_xp_on_success():
    repository = FakeXpRepository(xp_by_user={10: 12000})

    result = purchase_shop_item(
        server_id=1,
        user_id=10,
        item_key="soundboard",
        using_server=1,
        owned_role_ids=set(),
        repository=repository,
    )

    assert result == XpShopPurchaseResult(
        status="success",
        item_spec=XpShopItemSpec(item_key="soundboard", name="사운드보드 사용 권한", price=10000, role_id=1398550480707256433),
    )
    assert repository.xp_by_user[10] == 2000
    assert ("add_xp", 1, 10, -10000) in repository.calls
    assert ("add_month_xp", 1, 10, -10000) in repository.calls


def test_create_gamble_offer_validates_amount_and_resolves_unit():
    too_small = create_gamble_offer(amount=0, choice="홀", unit="XP")
    too_large = create_gamble_offer(amount=1000001, choice="홀", unit="XP")
    created = create_gamble_offer(amount=500, choice="짝", unit="XP")

    assert too_small == GambleOfferResult(status="amount_too_small", amount=0, unit="XP", choice="홀")
    assert too_large == GambleOfferResult(status="amount_too_large", amount=0, unit="XP", choice="홀")
    assert created == GambleOfferResult(status="created", amount=500, unit="XP", choice="짝")


def test_resolve_gamble_round_reports_balance_failures_and_success():
    insufficient_participant_repository = FakeXpRepository(xp_by_user={1: 1000, 2: 100})
    insufficient_creator_repository = FakeXpRepository(xp_by_user={1: 100, 2: 1000})
    success_repository = FakeXpRepository(xp_by_user={1: 1000, 2: 1000})

    participant_fail = resolve_gamble_round(
        server_id=1,
        creator_user_id=1,
        participant_user_id=2,
        amount=300,
        correct_choice="홀",
        selected_choice="홀",
        unit="XP",
        repository=insufficient_participant_repository,
    )
    creator_fail = resolve_gamble_round(
        server_id=1,
        creator_user_id=1,
        participant_user_id=2,
        amount=300,
        correct_choice="홀",
        selected_choice="짝",
        unit="XP",
        repository=insufficient_creator_repository,
    )
    success_result = resolve_gamble_round(
        server_id=1,
        creator_user_id=1,
        participant_user_id=2,
        amount=300,
        correct_choice="홀",
        selected_choice="홀",
        unit="XP",
        repository=success_repository,
    )

    assert participant_fail == GambleSettlementResult(status="participant_insufficient_balance", amount=300, unit="XP")
    assert creator_fail == GambleSettlementResult(status="creator_insufficient_balance", amount=300, unit="XP")
    assert success_result == GambleSettlementResult(
        status="completed",
        winner_id=2,
        loser_id=1,
        correct_choice="홀",
        amount=300,
        unit="XP",
    )
    assert success_repository.xp_by_user == {1: 700, 2: 1300}
