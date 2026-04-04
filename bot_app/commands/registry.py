from __future__ import annotations

from discord.ext import commands

from commands import anti_raid_command
from commands import basic_info
from commands import bulk_cancel
from commands import chat_time
from commands import close_threads
from commands import compatibility
from commands import encode
from commands import ping
from commands import remove_all_roles
from commands import rules
from commands import security_check
from commands import server_info
from commands import slowmode
from commands import suggest_random
from commands import timestamp
from commands import turn_off
from commands import weather
from commands import xp_setup
from commands.autorole import autorole
from commands.chat_analyze import chat_analyze
from commands.mention_delay import mention_delay
from commands.phrase import phrase
from commands.summarize_command import summarize_command
from commands.train_command import train_command


SETUP_COMMAND_MODULES = (
    encode,
    bulk_cancel,
    turn_off,
    suggest_random,
    chat_time,
    timestamp,
    ping,
    basic_info,
    close_threads,
    remove_all_roles,
    security_check,
    weather,
    xp_setup,
    slowmode,
    server_info,
    rules,
    anti_raid_command,
    compatibility,
)

GROUP_COMMAND_FACTORIES = (
    train_command,
    summarize_command,
    mention_delay,
    autorole,
    phrase,
    chat_analyze,
)


def get_setup_command_modules():
    return SETUP_COMMAND_MODULES


def get_group_command_factories():
    return GROUP_COMMAND_FACTORIES


def register_setup_commands(bot: commands.Bot) -> None:
    if getattr(bot, "_phase2_setup_commands_registered", False):
        return

    for module in SETUP_COMMAND_MODULES:
        module.setup(bot)

    bot._phase2_setup_commands_registered = True


def register_group_commands(bot: commands.Bot) -> None:
    if getattr(bot, "_phase2_group_commands_registered", False):
        return

    for factory in GROUP_COMMAND_FACTORIES:
        bot.tree.add_command(factory())

    bot._phase2_group_commands_registered = True


def get_registration_summary() -> dict[str, tuple[str, ...]]:
    return {
        "setup_modules": tuple(module.__name__ for module in SETUP_COMMAND_MODULES),
        "group_factories": tuple(factory.__name__ for factory in GROUP_COMMAND_FACTORIES),
    }
