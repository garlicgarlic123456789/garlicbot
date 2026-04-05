from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


WhitelistPermission = Literal[
    "admin",
    "manage_server",
    "manage_messages",
    "ban_members",
    "timeout_members",
]
ModerationCommandStatus = Literal["handled", "not_handled", "error"]
AutomodStatus = Literal["handled", "not_handled"]
LoopStartStatus = Literal["started", "already_running"]
UserBlockStatus = Literal["blocked", "not_blocked"]
SlashCommandStatus = Literal["completed", "rejected", "failed"]


@dataclass(frozen=True, slots=True)
class XpSetting:
    enabled: bool
    chat_xp: int | None
    chat_xp_cooldown: int | None
    voice_xp: int | None
    voice_xp_cooldown: int | None
    unit: str


@dataclass(frozen=True, slots=True)
class AutomodRuleConfig:
    enabled: bool
    action: int


@dataclass(frozen=True, slots=True)
class AutomodConfig:
    political: AutomodRuleConfig
    sexual: AutomodRuleConfig
    invite_link: AutomodRuleConfig
    mention: AutomodRuleConfig
    whitelist_permission: WhitelistPermission


@dataclass(frozen=True, slots=True)
class LogChannelConfig:
    editdelete: int | None
    reaction: int | None
    role: int | None
    image: int | None


@dataclass(frozen=True, slots=True)
class AnonymousSetting:
    enabled: bool | None
    log_channel_id: int | None


@dataclass(frozen=True, slots=True)
class ModerationCommandResult:
    status: ModerationCommandStatus
    error_count: int
    stop_processing: bool
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class AutomodExecutionResult:
    status: AutomodStatus
    stop_processing: bool
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class LoopStartResult:
    status: LoopStartStatus
    started: bool


@dataclass(frozen=True, slots=True)
class UserBlockState:
    status: UserBlockStatus
    blocked_until_label: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SlashCommandResult:
    status: SlashCommandStatus
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class ErrorTrackedSlashCommandResult:
    status: SlashCommandStatus
    error_count: int
    reason_code: str | None = None
