from __future__ import annotations

import asyncio
from typing import Any, Mapping

import discord

from bot_app.services.xp_economy_service import create_gamble_offer, purchase_shop_item, resolve_gamble_round
from bot_app.types.readability_contracts import SlashCommandResult, UserBlockState


def _resolve_user_block_state(block_checker, user) -> UserBlockState:
    is_blocked_now, blocked_until, block_reason = block_checker(user)
    if not is_blocked_now:
        return UserBlockState(status="not_blocked")
    blocked_until_label = None if blocked_until is None else str(blocked_until)
    return UserBlockState(
        status="blocked",
        blocked_until_label=blocked_until_label,
        reason=block_reason,
    )


def _format_blocked_message(user_id: int, block_state: UserBlockState) -> str:
    return f"**[오류!]** {user_id}님은 `{block_state.reason}` 사유로 {block_state.blocked_until_label}까지 차단 중입니다."


def _slash_result(*, status: str, reason_code: str | None = None) -> SlashCommandResult:
    return SlashCommandResult(status=status, reason_code=reason_code)


class GambleButtonView(discord.ui.View):
    """Preserve the legacy 홀짝 gamble interaction behind a testable helper boundary."""

    def __init__(
        self,
        author: discord.Member,
        *,
        xp_amount: int,
        choice: str,
        unit: str,
        context: Mapping[str, Any],
    ):
        super().__init__(timeout=600)
        self.author = author
        self.xp_amount = xp_amount
        self.choice = choice
        self.unit = unit
        self.context = context
        self.lock = asyncio.Lock()
        self.already_played = False

    async def button_callback(self, interaction: discord.Interaction, user_choice: str):
        async with self.lock:
            if interaction.user == self.author:
                await interaction.response.send_message("**[오류!]** 자신의 게임에서는 선택할 수 없습니다!", ephemeral=True)
                return

            block_state = _resolve_user_block_state(self.context["is_blocked"], interaction.user)
            if block_state.status == "blocked":
                await interaction.response.send_message(
                    _format_blocked_message(interaction.user.id, block_state),
                    ephemeral=True,
                )
                return

            settlement = resolve_gamble_round(
                server_id=interaction.guild.id,
                creator_user_id=self.author.id,
                participant_user_id=interaction.user.id,
                amount=self.xp_amount,
                correct_choice=self.choice,
                selected_choice=user_choice,
                unit=self.unit,
            )
            if settlement.status == "participant_insufficient_balance":
                await interaction.response.send_message(
                    f"**[오류!]** 게임 참가자의 {self.unit}이(가) 부족합니다.",
                    ephemeral=True,
                )
                return
            if settlement.status == "creator_insufficient_balance":
                await interaction.response.send_message(
                    f"**[오류!]** 게임 생성자의 {self.unit}이(가) 부족합니다.",
                    ephemeral=True,
                )
                return

            self.disable_all_buttons()
            if self.already_played:
                await interaction.response.send_message("**[오류!]** 이미 게임이 종료되었습니다.", ephemeral=True)
                return

            self.already_played = True
            await interaction.response.defer()
            await interaction.message.edit(view=self)
            await interaction.followup.send(
                f"<@{settlement.winner_id}>님이 승리하고 <@{settlement.loser_id}>님이 패배하였습니다. "
                f"정답은 **{settlement.correct_choice}**이었고 걸린 {settlement.unit}은(는) `{settlement.amount}`입니다."
            )

    @discord.ui.button(label="홀", style=discord.ButtonStyle.primary)
    async def odd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.button_callback(interaction, "홀")

    @discord.ui.button(label="짝", style=discord.ButtonStyle.primary)
    async def even_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.button_callback(interaction, "짝")

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True


async def run_buy_shop_slash_command(
    interaction: discord.Interaction,
    *,
    item_key: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if interaction.guild.id != context["using_server"]:
        embed = discord.Embed(
            title="오류",
            description="이 기능은 아직 여러 서버들에서 지원되지 않습니다. [도움말 바로가기](https://asdfasdfqwer.notion.site/1aa4a653ce01808ea2c0c18f7e0ee0d0?pvs=4)",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        return _slash_result(status="rejected", reason_code="shop_unsupported_server")

    await interaction.response.defer()
    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.followup.send(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    purchase_result = purchase_shop_item(
        server_id=interaction.guild.id,
        user_id=interaction.user.id,
        item_key=item_key,
        using_server=context["using_server"],
        owned_role_ids={role.id for role in interaction.user.roles},
    )

    if purchase_result.status == "manual_only_item":
        embed = discord.Embed(
            title="오류",
            color=discord.Color.red(),
            description="해당 상품은 자동 구매가 지원되지 않습니다. <#1327836359804850269>에서 문의해 주세요.",
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="shop_manual_only_item")

    if purchase_result.status == "invalid_item":
        embed = discord.Embed(
            title="오류",
            color=discord.Color.red(),
            description="해당 상품은 자동 구매가 지원되지 않습니다. <#1327836359804850269>에서 문의해 주세요.",
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="shop_invalid_item")

    if purchase_result.status == "already_owned":
        embed = discord.Embed(
            title="오류",
            color=discord.Color.red(),
            description="이미 해당 역할이 있습니다.",
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="shop_already_owned")

    if purchase_result.status == "insufficient_balance":
        embed = discord.Embed(
            title="오류",
            color=discord.Color.red(),
            description="경험치가 부족합니다.",
        )
        await interaction.followup.send(embed=embed)
        return _slash_result(status="rejected", reason_code="shop_insufficient_balance")

    role = interaction.guild.get_role(purchase_result.item_spec.role_id)
    await interaction.user.add_roles(role, reason="/경험치샵구매 명령어를 통한 구매")
    embed = discord.Embed(
        title="성공",
        color=int("a5f0ff", 16),
        description="성공적으로 구매 처리되었습니다.",
    )
    await interaction.followup.send(embed=embed)
    return _slash_result(status="completed", reason_code="shop_purchase_success")


async def run_gamble_slash_command(
    interaction: discord.Interaction,
    *,
    amount: int,
    choice,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    if interaction.guild.id not in context["xp_setting"] or context["xp_setting"][interaction.guild.id][0] is False:
        embed = discord.Embed(
            title="오류",
            description="경험치 기능이 사용 중지되어 있는 서버입니다.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return _slash_result(status="rejected", reason_code="gamble_xp_disabled")

    block_state = _resolve_user_block_state(context["is_blocked"], interaction.user)
    if block_state.status == "blocked":
        await interaction.response.send_message(_format_blocked_message(interaction.user.id, block_state))
        return _slash_result(status="rejected", reason_code="blocked_user")

    offer_result = create_gamble_offer(
        amount=amount,
        choice=choice.value,
        unit=context["xp_setting"][interaction.guild.id][5],
    )
    if offer_result.status == "amount_too_small":
        await interaction.response.send_message("**[오류!]** amount의 값은 1 이상이여야 합니다.")
        return _slash_result(status="rejected", reason_code="gamble_amount_too_small")
    if offer_result.status == "amount_too_large":
        await interaction.response.send_message("**[오류!]** amount의 값은 1000000 이하여야 합니다.")
        return _slash_result(status="rejected", reason_code="gamble_amount_too_large")

    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="경험치 도박 게임!",
        description=(
            f"<@{interaction.user.id}>님이 경험치 `{offer_result.amount}` {offer_result.unit}을(를) 걸고 게임을 생성하였습니다.\n"
            "홀 또는 짝 중 해당 유저가 고른 것이 무엇인지 맞춰보세요."
        ),
        color=discord.Color.gold(),
    )
    view = GambleButtonView(
        interaction.user,
        xp_amount=offer_result.amount,
        choice=offer_result.choice,
        unit=offer_result.unit,
        context={"is_blocked": context["is_blocked"]},
    )
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("도박 게임이 생성되었습니다!")
    return _slash_result(status="completed", reason_code="gamble_created")
