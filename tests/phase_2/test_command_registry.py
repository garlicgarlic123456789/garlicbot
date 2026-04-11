from types import SimpleNamespace

import bot_app.commands.registry as registry
from commands import basic_info

from tests.helpers.fakes import FakeBot


def test_registration_summary_matches_phase2_contract():
    assert registry.get_registration_summary() == {
        "setup_modules": (
            "commands.encode",
            "commands.bulk_cancel",
            "commands.turn_off",
            "commands.suggest_random",
            "commands.chat_time",
            "commands.timestamp",
            "commands.ping",
            "commands.basic_info",
            "commands.close_threads",
            "commands.remove_all_roles",
            "commands.security_check",
            "commands.weather",
            "commands.xp_setup",
            "commands.slowmode",
            "commands.server_info",
            "commands.rules",
            "commands.anti_raid_command",
            "commands.compatibility",
        ),
        "group_factories": (
            "train_command",
            "summarize_command",
            "mention_delay",
            "autorole",
            "phrase",
            "chat_analyze",
        ),
    }


def test_basic_info_setup_registers_phase2_moved_commands():
    bot = FakeBot()

    basic_info.setup(bot)

    assert [command["name"] for command in bot.tree.registered_commands] == [
        "도움말",
        "프로필사진",
    ]


def test_register_setup_commands_is_idempotent(monkeypatch):
    calls = []

    module_one = SimpleNamespace(__name__="commands.one")
    module_two = SimpleNamespace(__name__="commands.two")
    module_one.setup = lambda bot: calls.append(("one", bot))
    module_two.setup = lambda bot: calls.append(("two", bot))

    monkeypatch.setattr(
        registry,
        "SETUP_COMMAND_MODULES",
        (module_one, module_two),
    )

    bot = FakeBot()

    registry.register_setup_commands(bot)
    registry.register_setup_commands(bot)

    assert calls == [("one", bot), ("two", bot)]
    assert bot._phase2_setup_commands_registered is True


def test_register_group_commands_is_idempotent(monkeypatch):
    first_group = object()
    second_group = object()

    monkeypatch.setattr(
        registry,
        "GROUP_COMMAND_FACTORIES",
        (
            lambda: first_group,
            lambda: second_group,
        ),
    )

    bot = FakeBot()

    registry.register_group_commands(bot)
    registry.register_group_commands(bot)

    assert bot.tree.added_commands == [first_group, second_group]
    assert bot._phase2_group_commands_registered is True


def test_register_known_commands_calls_both_registration_paths(monkeypatch):
    calls = []

    monkeypatch.setattr(
        registry,
        "register_setup_commands",
        lambda bot: calls.append(("setup", bot)),
    )
    monkeypatch.setattr(
        registry,
        "register_group_commands",
        lambda bot: calls.append(("group", bot)),
    )

    bot = FakeBot()

    registry.register_known_commands(bot)

    assert calls == [("setup", bot), ("group", bot)]
