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

    disallowed_imports = (
        "from commands.train_command import *",
        "from commands.summarize_command import *",
        "from commands.mention_delay import *",
        "from commands.autorole import *",
        "from commands.phrase import *",
        "from commands.chat_analyze import *",
    )

    for import_line in disallowed_imports:
        assert import_line not in main_source
