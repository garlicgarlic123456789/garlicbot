import ast
import copy
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest
from discord.app_commands import Choice

import bot_app.commands.slash_rail_handlers as handlers_module
from bot_app.commands.slash_rail_handlers import (
    run_delete_route_slash_command,
    run_make_rail_slash_command,
    run_make_route_slash_command,
    run_update_route_dispatch_interval_slash_command,
)
from bot_app.types.readability_contracts import SlashCommandResult


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


class FakeUser:
    def __init__(self, user_id: int):
        self.id = user_id


class FakeInteraction:
    def __init__(self, *, user_id: int = 1, channel_id: int = 2):
        self.user = FakeUser(user_id)
        self.channel_id = channel_id
        self.response = FakeResponse()
        self.followup = FakeFollowup()


def _extract_main_wrapper(function_name: str):
    source = Path("main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        module_ast = ast.parse(source)
    function_node = next(node for node in ast.walk(module_ast) if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name)
    function_copy = copy.deepcopy(function_node)
    function_copy.decorator_list = []
    wrapper_module = ast.Module(body=[function_copy], type_ignores=[])
    ast.fix_missing_locations(wrapper_module)
    return wrapper_module


@pytest.mark.asyncio
async def test_make_rail_helper_sends_legacy_success_message(monkeypatch):
    interaction = FakeInteraction()

    monkeypatch.setattr(
        handlers_module,
        "create_rail",
        lambda **kwargs: SimpleNamespace(status="created", rail_count=2, rail_name="노선"),
    )

    result = await run_make_rail_slash_command(interaction, rail_name="노선", rail_count=2)

    assert result == SlashCommandResult(status="completed", reason_code="rail_created")
    assert interaction.response.sent[0]["content"] == "**[알림]** 선로 개수가 2인 노선 선로를 건설했습니다!"


@pytest.mark.asyncio
async def test_make_route_helper_preserves_single_route_limit_message(monkeypatch):
    interaction = FakeInteraction()

    monkeypatch.setattr(
        handlers_module,
        "create_route",
        lambda **kwargs: SimpleNamespace(status="temporary_single_route_limit"),
    )

    result = await run_make_route_slash_command(
        interaction,
        route_name="노선",
        train_choice=Choice(name="중전철", value="중전철"),
        dispatch_interval=4,
    )

    assert result == SlashCommandResult(status="rejected", reason_code="temporary_single_route_limit")
    assert "하나의 노선에는 하나의 운행계통만" in interaction.followup.sent[0]["content"]


@pytest.mark.asyncio
async def test_rail_helpers_cover_remaining_error_messages(monkeypatch):
    interaction = FakeInteraction()

    monkeypatch.setattr(handlers_module, "create_rail", lambda **kwargs: SimpleNamespace(status="invalid_input"))
    invalid_rail_result = await run_make_rail_slash_command(interaction, rail_name="노선", rail_count="두개")

    monkeypatch.setattr(handlers_module, "create_route", lambda **kwargs: SimpleNamespace(status="rail_missing"))
    missing_rail_result = await run_make_route_slash_command(
        interaction,
        route_name="노선",
        train_choice=Choice(name="중전철", value="중전철"),
        dispatch_interval=4,
    )

    monkeypatch.setattr(handlers_module, "create_route", lambda **kwargs: SimpleNamespace(status="duplicate_name"))
    duplicate_route_result = await run_make_route_slash_command(
        interaction,
        route_name="노선",
        train_choice=Choice(name="중전철", value="중전철"),
        dispatch_interval=4,
    )

    monkeypatch.setattr(handlers_module, "delete_route", lambda **kwargs: SimpleNamespace(status="route_missing"))
    missing_route_delete_result = await run_delete_route_slash_command(interaction, route_name="없는노선")

    monkeypatch.setattr(
        handlers_module,
        "update_route_dispatch_interval",
        lambda **kwargs: SimpleNamespace(status="interval_too_small"),
    )
    too_small_result = await run_update_route_dispatch_interval_slash_command(
        interaction,
        route_name="노선",
        dispatch_interval=1,
    )

    monkeypatch.setattr(
        handlers_module,
        "update_route_dispatch_interval",
        lambda **kwargs: SimpleNamespace(status="invalid_input"),
    )
    invalid_update_result = await run_update_route_dispatch_interval_slash_command(
        interaction,
        route_name="노선",
        dispatch_interval="한분",
    )

    assert invalid_rail_result == SlashCommandResult(status="rejected", reason_code="invalid_input")
    assert interaction.response.sent[0]["content"] == "**[오류!]** 입력값이 올바르지 않습니다."
    assert missing_rail_result == SlashCommandResult(status="rejected", reason_code="rail_missing")
    assert "선로가 건설되어 있지 않은 채널" in interaction.followup.sent[0]["content"]
    assert duplicate_route_result == SlashCommandResult(status="failed", reason_code="route_duplicate_name")
    assert "이미 같은 이름의 운행계통" in interaction.followup.sent[1]["content"]
    assert missing_route_delete_result == SlashCommandResult(status="rejected", reason_code="route_missing")
    assert interaction.followup.sent[2]["content"] == "**[오류!]** 입력값이 올바르지 않습니다."
    assert too_small_result == SlashCommandResult(status="rejected", reason_code="dispatch_interval_too_small")
    assert "dispatch_interval의 값은 2 이상" in interaction.followup.sent[3]["content"]
    assert invalid_update_result == SlashCommandResult(status="rejected", reason_code="invalid_input")
    assert interaction.followup.sent[4]["content"] == "**[오류!]** 입력값이 올바르지 않습니다."


@pytest.mark.asyncio
async def test_route_delete_and_update_helpers_delegate_to_service(monkeypatch):
    interaction = FakeInteraction(user_id=1)

    monkeypatch.setattr(
        handlers_module,
        "delete_route",
        lambda **kwargs: SimpleNamespace(status="deleted"),
    )
    delete_result = await run_delete_route_slash_command(interaction, route_name="노선")

    monkeypatch.setattr(
        handlers_module,
        "update_route_dispatch_interval",
        lambda **kwargs: SimpleNamespace(status="updated"),
    )
    update_result = await run_update_route_dispatch_interval_slash_command(
        interaction,
        route_name="노선",
        dispatch_interval=5,
    )

    assert delete_result == SlashCommandResult(status="completed", reason_code="route_deleted")
    assert update_result == SlashCommandResult(status="completed", reason_code="route_dispatch_interval_updated")


@pytest.mark.asyncio
async def test_main_wave7_rail_wrappers_delegate_to_handlers():
    source = Path("main.py").read_text(encoding="utf-8")
    wrappers = {
        "make_rail": _extract_main_wrapper("make_rail"),
        "make_route": _extract_main_wrapper("make_route"),
        "del_route": _extract_main_wrapper("del_route"),
        "dispatch_interval_change": _extract_main_wrapper("dispatch_interval_change"),
    }
    captured = {}

    async def fake_helper(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SlashCommandResult(status="completed", reason_code="delegated")

    namespace = {
        "discord": SimpleNamespace(Interaction=object),
        "app_commands": SimpleNamespace(Choice=Choice),
        "run_make_rail_slash_command": fake_helper,
        "run_make_route_slash_command": fake_helper,
        "run_delete_route_slash_command": fake_helper,
        "run_update_route_dispatch_interval_slash_command": fake_helper,
    }

    for wrapper_module in wrappers.values():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(wrapper_module, "main.py", "exec"), namespace)

    interaction = FakeInteraction()
    await namespace["make_rail"](interaction, "노선", 2)
    assert captured["kwargs"]["rail_name"] == "노선"

    await namespace["make_route"](interaction, "노선", Choice(name="중전철", value="중전철"), 4)
    assert captured["kwargs"]["route_name"] == "노선"
    assert captured["kwargs"]["train_choice"].value == "중전철"

    await namespace["del_route"](interaction, "노선")
    assert captured["kwargs"]["route_name"] == "노선"

    await namespace["dispatch_interval_change"](interaction, "노선", 5)
    assert captured["kwargs"]["dispatch_interval"] == 5

    assert "await run_make_rail_slash_command(" in source
    assert "await run_make_route_slash_command(" in source
    assert "await run_delete_route_slash_command(" in source
    assert "await run_update_route_dispatch_interval_slash_command(" in source


def test_main_wave7_rail_commands_stay_runtime_active():
    source = Path("main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        module_ast = ast.parse(source)

    command_names_by_function = {}
    for node in ast.walk(module_ast):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "command":
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    command_names_by_function[node.name] = keyword.value.value

    assert command_names_by_function["make_rail"] == "선로신설"
    assert command_names_by_function["make_route"] == "운행계통신설"
    assert command_names_by_function["del_route"] == "운행계통폐지"
    assert command_names_by_function["dispatch_interval_change"] == "운행계통배차간격변경"
