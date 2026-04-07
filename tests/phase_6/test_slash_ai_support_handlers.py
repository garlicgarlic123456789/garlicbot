import ast
import copy
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

import bot_app.commands.slash_ai_support_handlers as handlers_module
from bot_app.commands.slash_ai_support_handlers import (
    run_check_moderation_log_slash_command,
    run_remove_summary_cooldown_slash_command,
    run_reset_chat_slash_command,
    run_server_advice_slash_command,
    run_show_help_slash_command,
    run_show_profile_image_slash_command,
)
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, SlashCommandResult
from tests.helpers.fakes import FakeBot


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

    async def send(self, content=None, *, embed=None, ephemeral=False, view=None):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral, "view": view})


class FakeDisplayAvatar:
    def __init__(self, url: str):
        self.url = url


class FakeUser:
    def __init__(self, user_id: int, *, display_name: str = "사용자"):
        self.id = user_id
        self.display_name = display_name
        self.name = display_name
        self.mention = f"<@{user_id}>"
        self.display_avatar = FakeDisplayAvatar(f"https://example.com/{user_id}.png")


class FakeInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self._original_response = SimpleNamespace(id=999)

    async def original_response(self):
        return self._original_response


def _extract_main_wrapper(function_name: str):
    source = Path("main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        module_ast = ast.parse(source)
    function_node = next(node for node in module_ast.body if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name)
    function_copy = copy.deepcopy(function_node)
    function_copy.decorator_list = []
    wrapper_module = ast.Module(body=[function_copy], type_ignores=[])
    ast.fix_missing_locations(wrapper_module)
    return wrapper_module


@pytest.mark.asyncio
async def test_help_helper_sends_help_embed():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    result = await run_show_help_slash_command(interaction)

    assert result == SlashCommandResult(status="completed", reason_code="help_shown")
    assert interaction.response.sent[0]["embed"].title == "도움말"


@pytest.mark.asyncio
async def test_profile_image_helper_blocks_restricted_user():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    result = await run_show_profile_image_slash_command(
        interaction,
        target_user=FakeUser(20),
        context={"is_blocked": lambda user: (True, "2099-01-01", "도배")},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="blocked_user")
    assert "**[오류!]** 10님은 `도배` 사유로 2099-01-01까지 차단 중입니다." == interaction.response.sent[0]["content"]


@pytest.mark.asyncio
async def test_reset_chat_helper_calls_service(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    captured = {}

    monkeypatch.setattr(handlers_module, "reset_chat_history", lambda user_id: captured.update({"user_id": user_id}))

    result = await run_reset_chat_slash_command(
        interaction,
        context={"is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="chat_reset")
    assert captured == {"user_id": 10}
    assert interaction.followup.sent[0]["embed"].description == "`마늘아 <할 말>` 및 `/생성형인공지능`으로 대화한 이력이 초기화되었습니다."


@pytest.mark.asyncio
async def test_check_moderation_log_helper_uses_snapshot_and_view(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    captured = {}

    monkeypatch.setattr(
        handlers_module,
        "load_moderation_log_snapshot",
        lambda *args, **kwargs: SimpleNamespace(
            status="found",
            entries=(SimpleNamespace(entry_id=1, type_label="warn", user_id=20, admin_id=30, addinfo=1, reason="사유"),),
            include_legacy=kwargs["include_legacy"],
        ),
    )

    class FakeView:
        def __init__(self, entries, user, interact_user):
            captured["entries"] = entries
            captured["user"] = user
            captured["interact_user"] = interact_user

        def get_embed(self):
            return SimpleNamespace(title="제재 내역")

    monkeypatch.setattr(handlers_module, "ModerationLogView", FakeView)

    result = await run_check_moderation_log_slash_command(
        interaction,
        target_user=FakeUser(20),
        admin_user=None,
        context={"is_blocked": lambda user: (False, None, None), "using_server": 1},
    )

    assert result == SlashCommandResult(status="completed", reason_code="moderation_log_found")
    assert captured["user"].id == 20
    assert interaction.followup.sent[0]["embed"].title == "제재 내역"


@pytest.mark.asyncio
async def test_remove_summary_cooldown_helper_requires_developer():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    bot = FakeBot()
    bot.cooldowns = {20: 123}

    result = await run_remove_summary_cooldown_slash_command(
        interaction,
        target_user=FakeUser(20),
        context={"developer": 99, "bot": bot},
        error_count=4,
    )

    assert result == ErrorTrackedSlashCommandResult(status="rejected", error_count=4, reason_code="developer_only")
    assert interaction.followup.sent[0]["embed"].description == "권한이 부족합니다. 다음 권한이 필요합니다: `개발자`"


@pytest.mark.asyncio
async def test_server_advice_helper_checks_permission_and_calls_handler():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    bot = FakeBot()
    captured = {}

    async def fake_advice_handler(*args):
        captured["args"] = args

    denied_result = await run_server_advice_slash_command(
        interaction,
        prompt_text="조언",
        provide_messages=False,
        provide_channels=False,
        start_message_link=None,
        end_message_link=None,
        role_label="일반 유저",
        context={"allowed_user_ids": (99,), "bot": bot, "advice_handler": fake_advice_handler},
    )
    assert denied_result == SlashCommandResult(status="rejected", reason_code="server_advice_missing_permission")

    allowed_interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    allowed_result = await run_server_advice_slash_command(
        allowed_interaction,
        prompt_text="조언",
        provide_messages=True,
        provide_channels=False,
        start_message_link="start",
        end_message_link="end",
        role_label="관리자",
        context={"allowed_user_ids": (10,), "bot": bot, "advice_handler": fake_advice_handler},
    )

    assert allowed_result == SlashCommandResult(status="completed", reason_code="server_advice_started")
    assert allowed_interaction.response.sent[0]["content"] == "처리 중입니다."
    assert captured["args"][0] is bot
    assert captured["args"][3] is True
    assert captured["args"][4] == "start"
    assert captured["args"][5] == "end"


@pytest.mark.asyncio
async def test_main_wave6_wrappers_delegate_to_ai_support_helpers():
    source = Path("main.py").read_text(encoding="utf-8")
    wrappers = {
        "reset_chat": _extract_main_wrapper("reset_chat"),
        "check_moderation_log": _extract_main_wrapper("check_moderation_log"),
        "remove_cooldown": _extract_main_wrapper("remove_cooldown"),
        "서버조언": _extract_main_wrapper("서버조언"),
    }
    captured = {}

    async def fake_helper(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(error_count=88)

    namespace = {
        "discord": SimpleNamespace(Interaction=object, User=object),
        "run_reset_chat_slash_command": fake_helper,
        "run_check_moderation_log_slash_command": fake_helper,
        "run_remove_summary_cooldown_slash_command": fake_helper,
        "run_server_advice_slash_command": fake_helper,
        "is_blocked": object(),
        "using_server": 1,
        "developer": 999,
        "bot": SimpleNamespace(cooldowns={}),
        "advice_main": object(),
        "error": 7,
    }

    for wrapper_module in wrappers.values():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(wrapper_module, "main.py", "exec"), namespace)

    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    await namespace["reset_chat"](interaction)
    assert captured["kwargs"]["context"]["is_blocked"] is namespace["is_blocked"]

    await namespace["check_moderation_log"](interaction, FakeUser(20), FakeUser(30))
    assert captured["kwargs"]["target_user"].id == 20
    assert captured["kwargs"]["admin_user"].id == 30

    await namespace["remove_cooldown"](interaction, FakeUser(40))
    assert captured["kwargs"]["context"]["developer"] == 999
    assert namespace["error"] == 88

    await namespace["서버조언"](interaction, "프롬프트", True, False, "start", "end", "관리자")
    assert captured["kwargs"]["prompt_text"] == "프롬프트"
    assert captured["kwargs"]["context"]["advice_handler"] is namespace["advice_main"]

    assert "await run_reset_chat_slash_command(" in source
    assert "await run_check_moderation_log_slash_command(" in source
    assert "await run_remove_summary_cooldown_slash_command(" in source
    assert "await run_server_advice_slash_command(" in source


@pytest.mark.asyncio
async def test_basic_info_setup_delegates_to_ai_support_helpers(monkeypatch):
    from commands import basic_info
    from tests.helpers.fakes import FakeBot

    bot = FakeBot()
    calls = []

    async def fake_help(interaction):
        calls.append(("help", interaction))

    async def fake_profile(interaction, *, target_user, context):
        calls.append(("profile", target_user.id, context["is_blocked"]))

    monkeypatch.setattr(basic_info, "run_show_help_slash_command", fake_help)
    monkeypatch.setattr(basic_info, "run_show_profile_image_slash_command", fake_profile)
    basic_info.setup(bot)

    registered = {command["name"]: command["callback"] for command in bot.tree.registered_commands}
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    await registered["도움말"](interaction)
    await registered["프로필사진"](interaction, FakeUser(20))

    assert calls[0][0] == "help"
    assert calls[1][0] == "profile"
    assert calls[1][1] == 20
