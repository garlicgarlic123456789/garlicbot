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
XpTransferStatus = Literal["success", "insufficient_balance"]
UserMoneyLookupStatus = Literal["found", "missing"]
UserProfileSource = Literal["guild_member", "external_user"]
UserClassificationStatus = Literal["blocked", "premium", "general"]
XpShopPurchaseStatus = Literal["success", "unsupported_server", "manual_only_item", "invalid_item", "already_owned", "insufficient_balance"]
GambleOfferStatus = Literal["created", "amount_too_small", "amount_too_large"]
GambleSettlementStatus = Literal["completed", "participant_insufficient_balance", "creator_insufficient_balance"]


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


@dataclass(frozen=True, slots=True)
class XpSnapshot:
    total_xp: int
    month_xp: int
    total_level: int
    month_level: int
    unit: str
    old_xp: int | None = None


@dataclass(frozen=True, slots=True)
class XpTransferResult:
    status: XpTransferStatus
    amount: int
    unit: str


@dataclass(frozen=True, slots=True)
class XpAdjustmentResult:
    amount: int
    total_xp: int
    month_xp: int
    unit: str


@dataclass(frozen=True, slots=True)
class XpRankingEntry:
    user_id: int
    xp: int
    level: int
    rank: int


@dataclass(frozen=True, slots=True)
class XpRankingPage:
    title: str
    page: int
    total_pages: int
    unit: str
    entries: tuple[XpRankingEntry, ...]


@dataclass(frozen=True, slots=True)
class LikeabilitySnapshot:
    score: int


@dataclass(frozen=True, slots=True)
class LikeabilityAdjustmentResult:
    delta: int
    score: int


@dataclass(frozen=True, slots=True)
class UserMoneyLookupResult:
    status: UserMoneyLookupStatus
    money: int | None = None


@dataclass(frozen=True, slots=True)
class DisplayedXpSnapshot:
    total_xp: int
    displayed_month_xp: int
    total_level: int
    displayed_month_level: int
    unit: str


@dataclass(frozen=True, slots=True)
class UserProfileSnapshot:
    source: UserProfileSource
    user_id: int
    display_name: str
    mention: str
    role_mentions: tuple[str, ...]
    xp_snapshot: DisplayedXpSnapshot | None
    account_created_at_label: str
    joined_at_label: str | None
    warning_count: int
    restriction_status_label: str
    classification_status: UserClassificationStatus
    classification_label: str
    avatar_url: str


@dataclass(frozen=True, slots=True)
class XpShopItemSpec:
    item_key: str
    name: str
    price: int
    role_id: int


@dataclass(frozen=True, slots=True)
class XpShopPurchaseResult:
    status: XpShopPurchaseStatus
    item_spec: XpShopItemSpec | None = None


@dataclass(frozen=True, slots=True)
class GambleOfferResult:
    status: GambleOfferStatus
    amount: int = 0
    unit: str = ""
    choice: str = ""


@dataclass(frozen=True, slots=True)
class GambleSettlementResult:
    status: GambleSettlementStatus
    winner_id: int | None = None
    loser_id: int | None = None
    correct_choice: str = ""
    amount: int = 0
    unit: str = ""


@dataclass(frozen=True, slots=True)
class WarningStatusSnapshot:
    warning_count: int
    warn_max: int | None


@dataclass(frozen=True, slots=True)
class WarnLimitSettingResult:
    warn_max: int | None


@dataclass(frozen=True, slots=True)
class GuildLogChannelSelection:
    editdelete: int | None
    reaction: int | None
    role: int | None
    image: int | None
    block: int
