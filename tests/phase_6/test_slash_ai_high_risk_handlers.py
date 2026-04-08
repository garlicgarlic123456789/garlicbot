import ast
import asyncio
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
from bot_app.types.readability_contracts import ErrorTrackedSlashCommandResult, SlashCommandResult


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


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply(self, content=None, *, embed=None, mention_author=False):
        self.replies.append({"content": content, "embed": embed, "mention_author": mention_author})


class FakeUser:
    def __init__(self, user_id: int, *, display_name: str = "사용자"):
        self.id = user_id
        self.display_name = display_name
        self.mention = f"<@{user_id}>"


class FakeInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.channel = SimpleNamespace(id=55)
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self._original_response = FakeMessage()

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
async def test_same_person_helper_executes_bot_app_owned_flow():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    class FakeModel:
        def generate_content(self, prompt: str):
            assert "유저1" in prompt and "유저2" in prompt
            return SimpleNamespace(text="동일인 가능성: 42")

    result = await run_same_person_check_slash_command(
        interaction,
        first_user=FakeUser(20, display_name="유저1"),
        second_user=FakeUser(30, display_name="유저2"),
        context={
                "developer": 10,
                "bot": object(),
                "load_user_messages": lambda bot, first_id, second_id, guild_id: (
                asyncio.sleep(0, result=("메시지" * 10, "테스트" * 10))
            ),
                "two_five_lite_model": FakeModel(),
                "error_state": {"count": 3},
        },
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=3, reason_code="same_person_completed")
    assert interaction.response.sent == [{"content": "처리 중입니다.", "embed": None, "ephemeral": False}]
    assert interaction._original_response.replies[0]["embed"].title == "성공"


@pytest.mark.asyncio
async def test_judge_helper_dispatches_to_version_specific_runner(monkeypatch):
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    captured = {}

    async def fake_v4(interaction_arg, *, start_message_link, end_message_link, context):
        captured.update(
            {
                "interaction": interaction_arg,
                "start_message_link": start_message_link,
                "end_message_link": end_message_link,
                "context": context,
            }
        )
        return ErrorTrackedSlashCommandResult(status="completed", error_count=7, reason_code="judge_completed")

    monkeypatch.setattr(handlers_module, "_run_judge_v4", fake_v4)

    result = await run_judge_slash_command(
        interaction,
        start_message_link="start",
        end_message_link="end",
        private_reply="True",
        version="v4",
        context={"error_state": {"count": 7}},
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=7, reason_code="judge_completed")
    assert interaction.response.deferred == [{"ephemeral": True}]
    assert captured["interaction"] is interaction
    assert captured["start_message_link"] == "start"
    assert captured["end_message_link"] == "end"


@pytest.mark.asyncio
async def test_generative_ai_helper_executes_model_branch_without_main_callback():
    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))

    class FakeModel:
        def generate_content(self, prompt: str):
            assert prompt == "질문"
            return SimpleNamespace(text="답변")

    result = await run_generative_ai_slash_command(
        interaction,
        prompt_text="질문",
        model_name="Gemini 2.5 Flash Lite",
        attachment=None,
        reasoning_effort="medium",
        context={
            "is_blocked": lambda user: (False, None, None),
            "developer": 999,
            "get_premium": lambda user_id: False,
            "ai_cooldowns": {},
            "o3_cooldowns": {},
            "gpt_4_1_cooldowns": {},
            "COOLDOWN_DURATION": 15,
            "o3_cooldowns_d": 60,
            "gpt_4_1_cooldowns_d": 60,
            "model": object(),
            "two_model": object(),
            "two_lite_model": object(),
            "two_five_lite_model": FakeModel(),
            "gemini_client": object(),
            "cute_model": object(),
            "judge_model": object(),
            "cute_model3": object(),
            "gpt_chat_threads": {},
            "get_gpt_chat_thread": lambda user_id: None,
            "update_gpt_chat_thread": lambda user_id, response_id: None,
            "client": object(),
            "gpt_client": object(),
            "error_state": {"count": 5},
        },
    )

    assert result == ErrorTrackedSlashCommandResult(status="completed", error_count=5, reason_code="generative_ai_completed")
    assert interaction.response.deferred == [{"ephemeral": False}]
    assert interaction.followup.sent[0]["embed"].title == "성공"


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


def test_ai_high_risk_helper_source_owns_runtime_logic():
    source = Path("bot_app/commands/slash_ai_high_risk_handlers.py").read_text(encoding="utf-8")

    assert "delegate_same_person_check" not in source
    assert "delegate_judge_command" not in source
    assert "delegate_generative_ai_command" not in source
    assert "load_user_messages" in source
    assert "create_judge4_chain1" in source
    assert "client\"].responses.create" in source
    assert "build_mining_help_response" in source


@pytest.mark.asyncio
async def test_main_wave7_wrappers_build_runtime_context_without_legacy_callbacks():
    source = Path("main.py").read_text(encoding="utf-8")
    wrappers = {
        "oritest": _extract_main_wrapper("oritest"),
        "judgement_": _extract_main_wrapper("judgement_"),
        "generative_ai": _extract_main_wrapper("generative_ai"),
        "mine_help": _extract_main_wrapper("mine_help"),
    }
    captured = {}

    async def fake_tracked_helper(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return ErrorTrackedSlashCommandResult(status="completed", error_count=99, reason_code="delegated")

    namespace = {
        "discord": SimpleNamespace(Interaction=object, User=object, Attachment=object),
        "run_same_person_check_slash_command": fake_tracked_helper,
        "run_judge_slash_command": fake_tracked_helper,
        "run_generative_ai_slash_command": fake_tracked_helper,
        "run_mining_help_slash_command": fake_tracked_helper,
        "developer": 1,
        "bot": object(),
        "load_user_messages": object(),
        "two_five_lite_model": object(),
        "is_blocked": object(),
        "get_server_rules": object(),
        "fetch_messages": object(),
        "create_chain1": object(),
        "create_chain2": object(),
        "create_judge4_chain1": object(),
        "create_judge4_chain2": object(),
        "get_premium": object(),
        "ai_cooldowns": {},
        "o3_cooldowns": {},
        "gpt_4_1_cooldowns": {},
        "COOLDOWN_DURATION": 15,
        "o3_cooldowns_d": 60,
        "gpt_4_1_cooldowns_d": 60,
        "model": object(),
        "two_model": object(),
        "two_lite_model": object(),
        "gemini_client": object(),
        "cute_model": object(),
        "judge_model": object(),
        "cute_model3": object(),
        "gpt_chat_threads": {},
        "get_gpt_chat_thread": object(),
        "update_gpt_chat_thread": object(),
        "client": object(),
        "gpt_client": object(),
        "using_server": 1,
        "error": 5,
    }

    for wrapper_module in wrappers.values():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(wrapper_module, "main.py", "exec"), namespace)

    interaction = FakeInteraction(user=FakeUser(10), guild=SimpleNamespace(id=1))
    await namespace["oritest"](interaction, FakeUser(20), FakeUser(30))
    assert captured["kwargs"]["context"]["developer"] == 1
    assert captured["kwargs"]["context"]["load_user_messages"] is namespace["load_user_messages"]
    assert "same_person_handler" not in captured["kwargs"]["context"]
    assert namespace["error"] == 99

    await namespace["judgement_"](interaction, "start", "end", "True", "v4")
    assert captured["kwargs"]["context"]["create_judge4_chain1"] is namespace["create_judge4_chain1"]
    assert captured["kwargs"]["context"]["fetch_messages"] is namespace["fetch_messages"]
    assert "judge_handler" not in captured["kwargs"]["context"]
    assert namespace["error"] == 99

    await namespace["generative_ai"](interaction, "질문", "GPT-5.1", None, "medium")
    assert captured["kwargs"]["context"]["client"] is namespace["client"]
    assert captured["kwargs"]["context"]["gpt_chat_threads"] is namespace["gpt_chat_threads"]
    assert "generative_ai_handler" not in captured["kwargs"]["context"]
    assert namespace["error"] == 99

    await namespace["mine_help"](interaction)
    assert captured["kwargs"]["context"]["using_server"] == 1
    assert captured["kwargs"]["context"]["is_blocked"] is namespace["is_blocked"]

    assert "await run_same_person_check_slash_command(" in source
    assert "await run_judge_slash_command(" in source
    assert "await run_generative_ai_slash_command(" in source
    assert "await run_mining_help_slash_command(" in source
