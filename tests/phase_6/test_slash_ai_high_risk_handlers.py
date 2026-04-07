import ast
import copy
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

import bot_app.commands.slash_ai_high_risk_handlers as handlers_module
from bot_app.commands.slash_ai_high_risk_handlers import (
    run_generative_ai_slash_command,
    run_judge_slash_command,
    run_mining_help_slash_command,
    run_same_person_check_slash_command,
)
from bot_app.services.ai_high_risk_service import build_mining_help_response
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
    def __init__(self, user_id: int, *, display_name: str = "사용자"):
        self.id = user_id
        self.display_name = display_name
        self.mention = f"<@{user_id}>"


class FakeInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.response = FakeResponse()
        self.followup = FakeFollowup()


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
async def test_same_person_helper_delegates_to_service(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    first_user = FakeUser(20, display_name="유저1")
    second_user = FakeUser(30, display_name="유저2")
    captured = {}

    async def fake_delegate(**kwargs):
        captured.update(kwargs)
        return SlashCommandResult(status="completed", reason_code="same_person_delegated")

    monkeypatch.setattr(handlers_module, "delegate_same_person_check", fake_delegate)

    result = await run_same_person_check_slash_command(
        interaction,
        first_user=first_user,
        second_user=second_user,
        context={"same_person_handler": object()},
    )

    assert result == SlashCommandResult(status="completed", reason_code="same_person_delegated")
    assert captured["interaction"] is interaction
    assert captured["first_user"] is first_user
    assert captured["second_user"] is second_user


@pytest.mark.asyncio
async def test_judge_helper_delegates_to_service(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    captured = {}

    async def fake_delegate(**kwargs):
        captured.update(kwargs)
        return SlashCommandResult(status="completed", reason_code="judge_delegated")

    monkeypatch.setattr(handlers_module, "delegate_judge_command", fake_delegate)

    result = await run_judge_slash_command(
        interaction,
        start_message_link="start",
        end_message_link="end",
        private_reply="True",
        version="v4",
        context={"judge_handler": object()},
    )

    assert result == SlashCommandResult(status="completed", reason_code="judge_delegated")
    assert captured["start_message_link"] == "start"
    assert captured["end_message_link"] == "end"
    assert captured["private_reply"] == "True"
    assert captured["version"] == "v4"


@pytest.mark.asyncio
async def test_generative_ai_helper_delegates_to_service(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    fake_attachment = SimpleNamespace(filename="sample.png", url="https://example.com/sample.png")
    captured = {}

    async def fake_delegate(**kwargs):
        captured.update(kwargs)
        return SlashCommandResult(status="completed", reason_code="generative_ai_delegated")

    monkeypatch.setattr(handlers_module, "delegate_generative_ai_command", fake_delegate)

    result = await run_generative_ai_slash_command(
        interaction,
        prompt_text="질문",
        model_name="GPT-5.1",
        attachment=fake_attachment,
        reasoning_effort="medium",
        context={"generative_ai_handler": object()},
    )

    assert result == SlashCommandResult(status="completed", reason_code="generative_ai_delegated")
    assert captured["prompt_text"] == "질문"
    assert captured["model_name"] == "GPT-5.1"
    assert captured["attachment"] is fake_attachment
    assert captured["reasoning_effort"] == "medium"


@pytest.mark.asyncio
async def test_mining_help_helper_sends_legacy_help_text(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    monkeypatch.setattr(
        handlers_module,
        "build_mining_help_response",
        lambda **kwargs: SimpleNamespace(
            status="ready",
            reason_code="mine_help_shown",
            message_text="광질 확률: 테스트",
            embed_description=None,
        ),
    )

    result = await run_mining_help_slash_command(
        interaction,
        context={"using_server": 1, "is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="completed", reason_code="mine_help_shown")
    assert interaction.response.deferred == [{"ephemeral": False}]
    assert interaction.followup.sent[0]["content"] == "광질 확률: 테스트"


@pytest.mark.asyncio
async def test_mining_help_helper_rejects_unsupported_server(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=999))

    monkeypatch.setattr(
        handlers_module,
        "build_mining_help_response",
        lambda **kwargs: SimpleNamespace(
            status="unsupported_server",
            reason_code="unsupported_server",
            message_text=None,
            embed_description="여러 서버들에서 지원되지 않습니다.",
        ),
    )

    result = await run_mining_help_slash_command(
        interaction,
        context={"using_server": 1, "is_blocked": lambda user: (False, None, None)},
    )

    assert result == SlashCommandResult(status="rejected", reason_code="unsupported_server")
    assert interaction.response.sent[0]["embed"].title == "오류"
    assert "지원되지 않습니다" in interaction.response.sent[0]["embed"].description


def test_mining_help_service_preserves_legacy_active_text():
    actor = FakeUser(10)

    result = build_mining_help_response(
        actor=actor,
        guild_id=1,
        context={"using_server": 1, "is_blocked": lambda user: (False, None, None)},
    )

    assert result == handlers_module.build_mining_help_response(
        actor=actor,
        guild_id=1,
        context={"using_server": 1, "is_blocked": lambda user: (False, None, None)},
    )
    assert result.message_text == (
        "광질 확률: 다이아몬드 1%, 에메랄드 2%, 금 47%, 철 49%, 용암 1%\n"
        "광질 시 소모 경험치: 일자굴 1블록 당 20 XP\n"
        "광질 시 지급 경험치: 다이아몬드 500 XP, 에메랄드 200 XP, 철 10 XP, 금 30 XP. 단, 용암 발견 시 지급하지 아니함."
    )


def test_wave7_helper_source_keeps_service_boundary_calls():
    source = Path("bot_app/commands/slash_ai_high_risk_handlers.py").read_text(encoding="utf-8")
    module_ast = ast.parse(source)

    expected_calls = {
        "run_same_person_check_slash_command": "delegate_same_person_check",
        "run_judge_slash_command": "delegate_judge_command",
        "run_generative_ai_slash_command": "delegate_generative_ai_command",
        "run_mining_help_slash_command": "build_mining_help_response",
    }

    function_nodes = {
        node.name: node for node in module_ast.body if isinstance(node, ast.AsyncFunctionDef)
    }
    for function_name, callee_name in expected_calls.items():
        function_node = function_nodes[function_name]
        called_names = {
            call.func.id
            for call in ast.walk(function_node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
        assert callee_name in called_names


@pytest.mark.asyncio
async def test_main_wave7_wrappers_delegate_to_ai_high_risk_helpers():
    source = Path("main.py").read_text(encoding="utf-8")
    wrappers = {
        "oritest": _extract_main_wrapper("oritest"),
        "judgement_": _extract_main_wrapper("judgement_"),
        "generative_ai": _extract_main_wrapper("generative_ai"),
        "mine_help": _extract_main_wrapper("mine_help"),
    }
    captured = {}

    async def fake_helper(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SlashCommandResult(status="completed", reason_code="delegated")

    namespace = {
        "discord": SimpleNamespace(Interaction=object, User=object, Attachment=object),
        "run_same_person_check_slash_command": fake_helper,
        "run_judge_slash_command": fake_helper,
        "run_generative_ai_slash_command": fake_helper,
        "run_mining_help_slash_command": fake_helper,
        "_legacy_same_person_check": object(),
        "_legacy_judgement_command": object(),
        "_legacy_generative_ai_command": object(),
        "using_server": 1,
        "is_blocked": object(),
    }

    for wrapper_module in wrappers.values():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(wrapper_module, "main.py", "exec"), namespace)

    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    await namespace["oritest"](interaction, FakeUser(20), FakeUser(30))
    assert captured["kwargs"]["first_user"].id == 20
    assert captured["kwargs"]["context"]["same_person_handler"] is namespace["_legacy_same_person_check"]

    await namespace["judgement_"](interaction, "start", "end", "True", "v4")
    assert captured["kwargs"]["start_message_link"] == "start"
    assert captured["kwargs"]["context"]["judge_handler"] is namespace["_legacy_judgement_command"]

    await namespace["generative_ai"](interaction, "질문", "GPT-5.1", None, "medium")
    assert captured["kwargs"]["prompt_text"] == "질문"
    assert captured["kwargs"]["context"]["generative_ai_handler"] is namespace["_legacy_generative_ai_command"]

    await namespace["mine_help"](interaction)
    assert captured["kwargs"]["context"]["using_server"] == 1
    assert captured["kwargs"]["context"]["is_blocked"] is namespace["is_blocked"]

    assert "await run_same_person_check_slash_command(" in source
    assert "await run_judge_slash_command(" in source
    assert "await run_generative_ai_slash_command(" in source
    assert "await run_mining_help_slash_command(" in source
