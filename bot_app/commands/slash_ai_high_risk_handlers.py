from __future__ import annotations

from typing import Any, Mapping

import discord

from bot_app.services.ai_high_risk_service import (
    build_mining_help_response,
    delegate_generative_ai_command,
    delegate_judge_command,
    delegate_same_person_check,
)
from bot_app.types.readability_contracts import SlashCommandResult


def _build_error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="오류", description=description, color=discord.Color.red())


async def run_same_person_check_slash_command(
    interaction: discord.Interaction,
    *,
    first_user: discord.User,
    second_user: discord.User,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    return await delegate_same_person_check(
        interaction=interaction,
        first_user=first_user,
        second_user=second_user,
        context=context,
    )


async def run_judge_slash_command(
    interaction: discord.Interaction,
    *,
    start_message_link: str,
    end_message_link: str | None,
    private_reply: str,
    version: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    return await delegate_judge_command(
        interaction=interaction,
        start_message_link=start_message_link,
        end_message_link=end_message_link,
        private_reply=private_reply,
        version=version,
        context=context,
    )


async def run_generative_ai_slash_command(
    interaction: discord.Interaction,
    *,
    prompt_text: str,
    model_name: str,
    attachment,
    reasoning_effort: str,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    return await delegate_generative_ai_command(
        interaction=interaction,
        prompt_text=prompt_text,
        model_name=model_name,
        attachment=attachment,
        reasoning_effort=reasoning_effort,
        context=context,
    )


async def run_mining_help_slash_command(
    interaction: discord.Interaction,
    *,
    context: Mapping[str, Any],
) -> SlashCommandResult:
    mining_help_response = build_mining_help_response(
        actor=interaction.user,
        guild_id=interaction.guild.id,
        context=context,
    )
    if mining_help_response.status == "unsupported_server":
        await interaction.response.send_message(embed=_build_error_embed(mining_help_response.embed_description or "오류"))
        return SlashCommandResult(status="rejected", reason_code=mining_help_response.reason_code)

    await interaction.response.defer()
    await interaction.followup.send(mining_help_response.message_text)
    if mining_help_response.status == "blocked":
        return SlashCommandResult(status="rejected", reason_code=mining_help_response.reason_code)
    return SlashCommandResult(status="completed", reason_code=mining_help_response.reason_code)
