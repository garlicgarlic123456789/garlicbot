import ast
import copy
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import discord
import pytest

from bot_app.commands.slash_user_handlers import run_user_profile_slash_command
from bot_app.repositories.user_repository import user_repository
from bot_app.repositories.xp_repository import xp_repository
from bot_app.types.readability_contracts import XpSetting
from commands.return_level import return_level


ROOT_DIR = Path(__file__).resolve().parents[1]


def _extract_main_wrapper(function_name: str) -> ast.Module:
    source = Path("main.py").read_text(encoding="utf-8")
    module_ast = ast.parse(source)
    function_node = next(
        node
        for node in module_ast.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )
    function_copy = copy.deepcopy(function_node)
    function_copy.decorator_list = []
    wrapper_module = ast.Module(body=[function_copy], type_ignores=[])
    ast.fix_missing_locations(wrapper_module)
    return wrapper_module


class _FakeResponse:
    def __init__(self):
        self.deferred = []

    async def defer(self, *, ephemeral: bool = False):
        self.deferred.append({"ephemeral": ephemeral})


class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, embed=None, ephemeral: bool = False):
        self.sent.append({"content": content, "embed": embed, "ephemeral": ephemeral})


class _FakeUser:
    def __init__(
        self,
        user_id: int,
        *,
        display_name: str = "마늘",
        name: str = "garlic",
        created_at: datetime | None = None,
    ):
        self.id = user_id
        self.display_name = display_name
        self.name = name
        self.created_at = created_at or datetime(2026, 4, 1, tzinfo=timezone.utc)
        self.display_avatar = SimpleNamespace(url=f"https://example.com/{user_id}.png")


class _FakeRole:
    def __init__(self, *, name: str, mention: str):
        self.name = name
        self.mention = mention


class _FakeMember(_FakeUser):
    def __init__(
        self,
        user_id: int,
        *,
        roles,
        joined_at: datetime | None = None,
        timed_out_until=None,
        display_name: str = "마늘",
        name: str = "garlic",
    ):
        super().__init__(user_id, display_name=display_name, name=name)
        self.roles = list(roles)
        self.joined_at = joined_at or datetime(2026, 4, 2, tzinfo=timezone.utc)
        self.timed_out_until = timed_out_until


class _FakeGuild:
    def __init__(self, guild_id: int, *, member):
        self.id = guild_id
        self._member = member

    async def fetch_member(self, user_id: int):
        return self._member

    async def fetch_ban(self, user):
        raise discord.NotFound(
            response=SimpleNamespace(status=404, reason="not found"),
            message="missing",
        )


class _FakeInteraction:
    def __init__(self, *, user, guild):
        self.user = user
        self.guild = guild
        self.response = _FakeResponse()
        self.followup = _FakeFollowup()


def test_full_codebase_import_smoke_runs_without_internal_warning_or_import_error(tmp_path):
    script = f"""
import importlib
import os
import pkgutil
import sys
import warnings

sys.path.insert(0, {str(ROOT_DIR)!r})
os.environ.setdefault("GEMENI_API_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy-openai-key")
os.environ.setdefault("train_timetable_api", "dummy-train-timetable-key")
os.environ.setdefault("train_arrivals_api", "dummy-train-arrivals-key")

warnings.simplefilter("error")
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"discord\\.player")
warnings.filterwarnings("ignore", category=FutureWarning, message=r"[\\s\\S]*google\\.generativeai[\\s\\S]*")

module_names = []
for package_name in ("bot_app", "commands"):
    package = importlib.import_module(package_name)
    for module_info in pkgutil.walk_packages(package.__path__, package_name + "."):
        module_names.append(module_info.name)

for module_name in sorted(module_names):
    importlib.import_module(module_name)

print(len(module_names))
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) >= 80


@pytest.mark.asyncio
async def test_main_user_profile_wrapper_reaches_real_handler_and_services(monkeypatch):
    wrapper_module = _extract_main_wrapper("사용자정보")

    async def fake_get_warning_count(server_id: int, user_id: int) -> int:
        return 3

    monkeypatch.setattr(user_repository, "has_premium", lambda user_id: True)
    monkeypatch.setattr(user_repository, "get_warning_count", fake_get_warning_count)
    monkeypatch.setattr(
        xp_repository,
        "get_xp_setting",
        lambda server_id: XpSetting(
            enabled=True,
            chat_xp=10,
            chat_xp_cooldown=60,
            voice_xp=0,
            voice_xp_cooldown=0,
            unit="XP",
        ),
    )
    monkeypatch.setattr(xp_repository, "get_xp", lambda server_id, user_id: 1200)
    monkeypatch.setattr(xp_repository, "get_month_xp", lambda server_id, user_id: 450)

    namespace = {
        "discord": discord,
        "run_user_profile_slash_command": run_user_profile_slash_command,
        "is_blocked": lambda user: (False, None, None),
        "xp_setting": {},
    }
    exec(compile(wrapper_module, "main.py", "exec"), namespace)

    timeout_until = datetime.now(timezone.utc) + timedelta(hours=1)
    member = _FakeMember(
        20,
        roles=[
            _FakeRole(name="@everyone", mention="@everyone"),
            _FakeRole(name="역할1", mention="<@&1>"),
            _FakeRole(name="역할2", mention="<@&2>"),
        ],
        timed_out_until=timeout_until,
        display_name="양파",
        name="onion",
    )
    interaction = _FakeInteraction(user=_FakeUser(10), guild=_FakeGuild(1, member=member))
    target_user = _FakeUser(20, display_name="양파", name="onion")

    await namespace["사용자정보"](interaction, target_user)

    assert interaction.response.deferred == [{"ephemeral": False}]
    embed = interaction.followup.sent[0]["embed"]
    assert embed.title == "양파님의 정보"
    assert embed.fields[0].value == "`20`"
    assert embed.fields[3].value == "<@&2>, <@&1>"
    assert embed.fields[4].value == f"{return_level(1200)} 레벨 (월간 레벨: {return_level(450)} 레벨)"
    assert "1200 XP" in embed.fields[5].value
    assert "450 XP" in embed.fields[5].value
    assert "- 부여된 경고: 3개" in embed.fields[8].value
    assert "타임아웃 중 (" in embed.fields[8].value
    assert embed.fields[9].value == "프리미엄 유저"
