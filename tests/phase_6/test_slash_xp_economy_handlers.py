from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

import bot_app.commands.slash_xp_economy_handlers as slash_xp_economy_handlers_module
from bot_app.commands.slash_xp_economy_handlers import GambleButtonView, run_buy_shop_slash_command, run_gamble_slash_command
from bot_app.types.readability_contracts import GambleOfferResult, GambleSettlementResult, SlashCommandResult, XpShopItemSpec, XpShopPurchaseResult


class FakeRole:
    def __init__(self, role_id: int, *, mention: str | None = None):
        self.id = role_id
        self.mention = mention or f"<@&{role_id}>"


class FakeUser:
    def __init__(self, user_id: int, *, roles=None):
        self.id = user_id
        self.mention = f"<@{user_id}>"
        self.roles = list(roles or [])
        self.added_roles = []

    async def add_roles(self, role, *, reason=None):
        self.added_roles.append({"role": role, "reason": reason})


class FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self.roles = {}

    def get_role(self, role_id: int):
        return self.roles.get(role_id)


class FakeResponse:
    def __init__(self):
        self.deferred = []
        self.sent = []

    async def defer(self, *, ephemeral=False):
        self.deferred.append({"ephemeral": ephemeral})

    async def send_message(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, embed=None, ephemeral=False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, embed=None, view=None):
        self.sent.append({"content": content, "embed": embed, "view": view})


class FakeInteraction:
    def __init__(self, *, user, guild, channel=None):
        self.user = user
        self.guild = guild
        self.channel = channel or FakeChannel()
        self.response = FakeResponse()
        self.followup = FakeFollowup()


class FakeMessage:
    def __init__(self):
        self.edited_views = []

    async def edit(self, *, view=None):
        self.edited_views.append(view)


class FakeButtonInteraction:
    def __init__(self, *, user, guild, message):
        self.user = user
        self.guild = guild
        self.message = message
        self.response = FakeResponse()
        self.followup = FakeFollowup()


@pytest.mark.asyncio
async def test_buy_shop_helper_rejects_unsupported_server_before_defer():
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(2))

    result = await run_buy_shop_slash_command(
        interaction,
        item_key="file",
        context={"using_server": 1, "is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="shop_unsupported_server")
    assert interaction.response.deferred == []
    assert "이 기능은 아직 여러 서버들에서 지원되지 않습니다." in interaction.response.sent[0]["embed"].description


@pytest.mark.asyncio
async def test_buy_shop_helper_rejects_blocked_user_after_defer():
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))

    result = await run_buy_shop_slash_command(
        interaction,
        item_key="file",
        context={"using_server": 1, "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단")},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert interaction.response.deferred == [{"ephemeral": False}]
    assert interaction.followup.sent[0]["content"] == "**[오류!]** 10님은 `테스트 차단` 사유로 2099-01-01까지 차단 중입니다."


@pytest.mark.asyncio
async def test_buy_shop_helper_applies_role_on_success(monkeypatch):
    user = FakeUser(10, roles=[])
    guild = FakeGuild(1)
    guild.roles[1333390128072232980] = FakeRole(1333390128072232980)
    interaction = FakeInteraction(user=user, guild=guild)

    monkeypatch.setattr(
        slash_xp_economy_handlers_module,
        "purchase_shop_item",
        lambda **kwargs: XpShopPurchaseResult(
            status="success",
            item_spec=XpShopItemSpec(item_key="file", name="파일 첨부 권한", price=3000, role_id=1333390128072232980),
        ),
    )

    result = await run_buy_shop_slash_command(
        interaction,
        item_key="file",
        context={"using_server": 1, "is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="shop_purchase_success")
    assert user.added_roles == [
        {
            "role": guild.roles[1333390128072232980],
            "reason": "/경험치샵구매 명령어를 통한 구매",
        }
    ]
    assert interaction.followup.sent[0]["embed"].description == "성공적으로 구매 처리되었습니다."


@pytest.mark.asyncio
async def test_gamble_helper_rejects_disabled_xp_before_other_checks():
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    choice = SimpleNamespace(value="홀")

    result = await run_gamble_slash_command(
        interaction,
        amount=100,
        choice=choice,
        context={"xp_setting": {}, "is_blocked": lambda user: (True, "2099-01-01", "테스트 차단")},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="gamble_xp_disabled")
    assert interaction.response.sent[0]["embed"].description == "경험치 기능이 사용 중지되어 있는 서버입니다."


@pytest.mark.asyncio
async def test_gamble_helper_creates_view_and_followup(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=FakeGuild(1))
    choice = SimpleNamespace(value="짝")

    monkeypatch.setattr(
        slash_xp_economy_handlers_module,
        "create_gamble_offer",
        lambda **kwargs: GambleOfferResult(status="created", amount=500, unit="XP", choice="짝"),
    )

    result = await run_gamble_slash_command(
        interaction,
        amount=500,
        choice=choice,
        context={"xp_setting": {1: [True, 5, 60, 0, 0, "XP"]}, "is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="gamble_created")
    assert interaction.response.deferred == [{"ephemeral": True}]
    sent_message = interaction.channel.sent[0]
    assert sent_message["embed"].title == "경험치 도박 게임!"
    assert isinstance(sent_message["view"], GambleButtonView)
    assert interaction.followup.sent[0]["content"] == "도박 게임이 생성되었습니다!"


@pytest.mark.asyncio
async def test_gamble_view_rejects_self_play():
    author = FakeUser(10)
    view = GambleButtonView(author, xp_amount=100, choice="홀", unit="XP", context={"is_blocked": lambda user: (False, None, None)})
    interaction = FakeButtonInteraction(user=author, guild=FakeGuild(1), message=FakeMessage())

    await view.button_callback(interaction, "홀")

    assert interaction.response.sent[0]["content"] == "**[오류!]** 자신의 게임에서는 선택할 수 없습니다!"
    assert interaction.response.sent[0]["ephemeral"] is True


@pytest.mark.asyncio
async def test_gamble_view_handles_balance_failure(monkeypatch):
    author = FakeUser(10)
    participant = FakeUser(20)
    view = GambleButtonView(author, xp_amount=100, choice="홀", unit="XP", context={"is_blocked": lambda user: (False, None, None)})
    message = FakeMessage()
    interaction = FakeButtonInteraction(user=participant, guild=FakeGuild(1), message=message)

    monkeypatch.setattr(
        slash_xp_economy_handlers_module,
        "check_gamble_balance",
        lambda **kwargs: SimpleNamespace(status="participant_insufficient_balance", amount=100, unit="XP"),
    )

    await view.button_callback(interaction, "홀")

    assert interaction.response.sent[0]["content"] == "**[오류!]** 게임 참가자의 XP이(가) 부족합니다."
    assert interaction.response.sent[0]["ephemeral"] is True
    assert view.already_played is False
    assert message.edited_views == []


@pytest.mark.asyncio
async def test_gamble_view_settles_round_and_edits_message(monkeypatch):
    author = FakeUser(10)
    participant = FakeUser(20)
    view = GambleButtonView(author, xp_amount=100, choice="홀", unit="XP", context={"is_blocked": lambda user: (False, None, None)})
    message = FakeMessage()
    interaction = FakeButtonInteraction(user=participant, guild=FakeGuild(1), message=message)

    monkeypatch.setattr(
        slash_xp_economy_handlers_module,
        "check_gamble_balance",
        lambda **kwargs: SimpleNamespace(status="ok", amount=100, unit="XP"),
    )
    monkeypatch.setattr(
        slash_xp_economy_handlers_module,
        "resolve_gamble_round",
        lambda **kwargs: GambleSettlementResult(
            status="completed",
            winner_id=20,
            loser_id=10,
            correct_choice="홀",
            amount=100,
            unit="XP",
        ),
    )

    await view.button_callback(interaction, "홀")

    assert interaction.response.deferred == [{"ephemeral": False}]
    assert message.edited_views == [view]
    assert view.already_played is True
    assert interaction.followup.sent[0]["content"] == "<@20>님이 승리하고 <@10>님이 패배하였습니다. 정답은 **홀**이었고 걸린 XP은(는) `100`입니다."


@pytest.mark.asyncio
async def test_gamble_view_does_not_resettle_after_game_finishes(monkeypatch):
    author = FakeUser(10)
    first_participant = FakeUser(20)
    second_participant = FakeUser(30)
    view = GambleButtonView(author, xp_amount=100, choice="홀", unit="XP", context={"is_blocked": lambda user: (False, None, None)})
    first_interaction = FakeButtonInteraction(user=first_participant, guild=FakeGuild(1), message=FakeMessage())
    second_interaction = FakeButtonInteraction(user=second_participant, guild=FakeGuild(1), message=FakeMessage())
    call_count = 0

    def fake_resolve_gamble_round(**kwargs):
        nonlocal call_count
        call_count += 1
        return GambleSettlementResult(
            status="completed",
            winner_id=20,
            loser_id=10,
            correct_choice="홀",
            amount=100,
            unit="XP",
        )

    monkeypatch.setattr(
        slash_xp_economy_handlers_module,
        "check_gamble_balance",
        lambda **kwargs: SimpleNamespace(status="ok", amount=100, unit="XP"),
    )
    monkeypatch.setattr(slash_xp_economy_handlers_module, "resolve_gamble_round", fake_resolve_gamble_round)

    await view.button_callback(first_interaction, "홀")
    await view.button_callback(second_interaction, "짝")

    assert call_count == 1
    assert second_interaction.response.sent[0]["content"] == "**[오류!]** 이미 게임이 종료되었습니다."
    assert second_interaction.response.sent[0]["ephemeral"] is True


@pytest.mark.asyncio
async def test_gamble_view_keeps_game_open_after_balance_failure(monkeypatch):
    author = FakeUser(10)
    first_participant = FakeUser(20)
    second_participant = FakeUser(30)
    view = GambleButtonView(author, xp_amount=100, choice="홀", unit="XP", context={"is_blocked": lambda user: (False, None, None)})
    first_interaction = FakeButtonInteraction(user=first_participant, guild=FakeGuild(1), message=FakeMessage())
    second_message = FakeMessage()
    second_interaction = FakeButtonInteraction(user=second_participant, guild=FakeGuild(1), message=second_message)
    balance_results = iter(
        [
            SimpleNamespace(status="participant_insufficient_balance", amount=100, unit="XP"),
            SimpleNamespace(status="ok", amount=100, unit="XP"),
        ]
    )
    settlement_call_count = 0

    def fake_check_gamble_balance(**kwargs):
        return next(balance_results)

    def fake_resolve_gamble_round(**kwargs):
        nonlocal settlement_call_count
        settlement_call_count += 1
        return GambleSettlementResult(
            status="completed",
            winner_id=30,
            loser_id=10,
            correct_choice="홀",
            amount=100,
            unit="XP",
        )

    monkeypatch.setattr(slash_xp_economy_handlers_module, "check_gamble_balance", fake_check_gamble_balance)
    monkeypatch.setattr(slash_xp_economy_handlers_module, "resolve_gamble_round", fake_resolve_gamble_round)

    await view.button_callback(first_interaction, "홀")
    await view.button_callback(second_interaction, "홀")

    assert first_interaction.response.sent[0]["content"] == "**[오류!]** 게임 참가자의 XP이(가) 부족합니다."
    assert settlement_call_count == 1
    assert second_interaction.response.deferred == [{"ephemeral": False}]
    assert second_interaction.followup.sent[0]["content"] == "<@30>님이 승리하고 <@10>님이 패배하였습니다. 정답은 **홀**이었고 걸린 XP은(는) `100`입니다."
    assert second_message.edited_views == [view]


def test_main_uses_xp_economy_helpers_instead_of_direct_logic():
    source = Path("main.py").read_text(encoding="utf-8")
    shop_block_start = source.index('@bot.tree.command(name = "경험치샵구매"')
    shop_block_end = source.index('@bot.tree.command(name="경험치수정"', shop_block_start)
    shop_block = source[shop_block_start:shop_block_end]
    gamble_block_start = source.index('@bot.tree.command(name="경험치도박"')
    gamble_block_end = source.index('@bot.tree.command(name="경험치수정"', gamble_block_start)
    gamble_block = source[gamble_block_start:gamble_block_end]

    assert "from bot_app.commands.slash_xp_economy_handlers import (" in source
    assert "GambleButtonView" not in gamble_block
    assert "await run_buy_shop_slash_command(" in shop_block
    assert "await run_gamble_slash_command(" in gamble_block
    assert "update_xp(" not in shop_block
    assert "update_xp(" not in gamble_block
