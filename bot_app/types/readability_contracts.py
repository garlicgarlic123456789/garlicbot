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
AutomodExemptionStatus = Literal["exempt", "not_exempt"]
MessageXpApplyStatus = Literal[
    "awarded",
    "skipped_missing_setting",
    "skipped_disabled",
    "skipped_missing_value",
    "skipped_cooldown",
]
AttendanceRewardStatus = Literal[
    "success",
    "xp_disabled",
    "attendance_disabled",
    "already_checked",
]


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


@dataclass(frozen=True, slots=True)
class AutomodExemptionResult:
    status: AutomodExemptionStatus
    matched_scope: str | None = None
    matched_channel_id: int | None = None


@dataclass(frozen=True, slots=True)
class MessageXpApplyResult:
    status: MessageXpApplyStatus
    awarded_xp: int = 0


@dataclass(frozen=True, slots=True)
class AttendanceRewardResult:
    status: AttendanceRewardStatus
    streak: int = 0
    check_xp: int = 0
    boost_check_xp: int = 0
    streak_bonus: int = 0
    total_xp: int = 0
    unit: str = ""
