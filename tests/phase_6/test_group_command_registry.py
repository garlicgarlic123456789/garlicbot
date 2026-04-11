import ast
from pathlib import Path

import bot_app.commands.registry as registry

from tests.helpers.fakes import FakeBot


def test_group_registration_summary_matches_phase6_contract():
    assert registry.get_registration_summary()["group_factories"] == (
        "train_command",
        "summarize_command",
        "mention_delay",
        "autorole",
        "phrase",
        "chat_analyze",
    )


def test_register_group_commands_adds_expected_group_names():
    bot = FakeBot()

    registry.register_group_commands(bot)

    assert [command.name for command in bot.tree.added_commands] == [
        "철도",
        "요약",
        "멘션지연",
        "자동역할",
        "문구",
        "채팅분석",
    ]


def test_register_group_commands_is_still_idempotent_with_real_factories():
    bot = FakeBot()

    registry.register_group_commands(bot)
    registry.register_group_commands(bot)

    assert [command.name for command in bot.tree.added_commands] == [
        "철도",
        "요약",
        "멘션지연",
        "자동역할",
        "문구",
        "채팅분석",
    ]


def test_main_no_longer_directly_imports_group_command_modules():
    main_source = Path("main.py").read_text(encoding="utf-8")
    main_ast = ast.parse(main_source)
    disallowed_modules = {
        "commands.train_command",
        "commands.summarize_command",
        "commands.mention_delay",
        "commands.autorole",
        "commands.phrase",
        "commands.chat_analyze",
    }
    disallowed_command_names = {
        "train_command",
        "summarize_command",
        "mention_delay",
        "autorole",
        "phrase",
        "chat_analyze",
    }

    for node in ast.walk(main_ast):
        if isinstance(node, ast.Import):
            imported_modules = {alias.name for alias in node.names}
            assert imported_modules.isdisjoint(disallowed_modules)

        if isinstance(node, ast.ImportFrom):
            if node.module in disallowed_modules:
                raise AssertionError(f"main.py must not import group module {node.module} directly")

            if node.module == "commands":
                imported_names = {alias.name for alias in node.names}
                assert imported_names.isdisjoint(disallowed_command_names)

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr != "add_command"

    register_known_commands_calls = [
        node
        for node in ast.walk(main_ast)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "register_known_commands"
    ]
    assert len(register_known_commands_calls) == 1
