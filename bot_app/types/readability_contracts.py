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
GambleBalanceStatus = Literal["ok", "participant_insufficient_balance", "creator_insufficient_balance"]
RoleDescriptionUpdateStatus = Literal["updated"]
InviteRouteMemoUpdateStatus = Literal["updated"]
InviteRouteReportStatus = Literal["known", "unknown"]
UserJoinRouteLookupStatus = Literal["found", "missing"]
BlockHistoryMutationStatus = Literal["deleted", "added"]
ChannelBackupLookupStatus = Literal["found", "missing"]
ChatResetStatus = Literal["completed"]
ModerationLogSnapshotStatus = Literal["found", "missing"]
SummaryCooldownResetStatus = Literal["cleared", "missing"]
EmbedOutputValidationStatus = Literal[
    "ok",
    "discord_link",
    "title_too_long",
    "description_too_long",
    "raid_keyword",
    "automod_keyword",
    "reserved_word",
]
LinkScanSnapshotStatus = Literal["ok", "discord_link", "scan_error"]
LinkScanSeverity = Literal["safe", "suspicious", "dangerous", "critical"]
RailCreationStatus = Literal["created", "too_many_tracks", "already_exists", "invalid_input"]
RouteCreationStatus = Literal["created", "rail_missing", "duplicate_name", "temporary_single_route_limit", "invalid_input"]
RouteDeletionStatus = Literal["deleted", "route_missing", "permission_denied"]
RouteDispatchIntervalUpdateStatus = Literal["updated", "route_missing", "permission_denied", "interval_too_small", "invalid_input"]


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
class GambleBalanceCheckResult:
    status: GambleBalanceStatus
    amount: int = 0
    unit: str = ""


@dataclass(frozen=True, slots=True)
class RoleDescriptionUpdateResult:
    status: RoleDescriptionUpdateStatus
    description: str | None


@dataclass(frozen=True, slots=True)
class RoleInfoSnapshot:
    role_name: str
    role_mention: str
    role_id: int
    color_label: object
    member_count: int
    description: str
    enabled_permissions: tuple[str, ...]
    member_mentions: tuple[str, ...]
    cannot_moderate_role_mentions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InviteRouteMemoUpdateResult:
    status: InviteRouteMemoUpdateStatus
    invite_code: str
    memo: str | None


@dataclass(frozen=True, slots=True)
class InviteRouteEntry:
    invite_code: str | None
    memo: str | None
    rendered_label: str


@dataclass(frozen=True, slots=True)
class InviteRouteReport:
    status: InviteRouteReportStatus
    entries: tuple[InviteRouteEntry, ...]


@dataclass(frozen=True, slots=True)
class UserJoinRouteLookupResult:
    status: UserJoinRouteLookupStatus
    join_route: str | None = None


@dataclass(frozen=True, slots=True)
class BlockHistoryMutationResult:
    status: BlockHistoryMutationStatus
    entry_id: int | None = None
    user_id: int | None = None
    admin_id: int | None = None
    type_label: str | None = None
    extra_value: int | None = None


@dataclass(frozen=True, slots=True)
class ChannelBackupMessage:
    author_id: int
    content: str
    attachment_filenames: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChannelBackupManifest:
    messages: tuple[ChannelBackupMessage, ...]


@dataclass(frozen=True, slots=True)
class ChatResetResult:
    """Outcome of clearing one user's stored chat thread state."""

    status: ChatResetStatus
    user_id: int
    cleared: bool = True


@dataclass(frozen=True, slots=True)
class ModerationLogEntry:
    """One moderation log row normalized away from legacy tuple indexing."""

    entry_id: int
    target_user_id: int | None
    admin_user_id: int | None
    reason: str | None
    type_label: str
    extra_value: int | None
    source_table: Literal["blockhistory", "blockhistory_old"] = "blockhistory"

    @property
    def user_id(self) -> int | None:
        """Compatibility alias for legacy callers that still expect user_id."""

        return self.target_user_id

    @property
    def admin_id(self) -> int | None:
        """Compatibility alias for legacy callers that still expect admin_id."""

        return self.admin_user_id

    @property
    def addinfo(self) -> int | None:
        """Compatibility alias for legacy callers that still expect addinfo."""

        return self.extra_value


@dataclass(frozen=True, slots=True)
class ModerationLogSnapshot:
    """Moderation log query result packaged for helpers and views."""

    status: ModerationLogSnapshotStatus
    server_id: int
    entries: tuple[ModerationLogEntry, ...]
    target_user_id: int | None = None
    admin_id: int | None = None
    include_legacy: bool = False
    current_entry_count: int = 0
    legacy_entry_count: int = 0

    @property
    def total_entries(self) -> int:
        return len(self.entries)


@dataclass(frozen=True, slots=True)
class SummaryCooldownResetResult:
    """Outcome of clearing a stored summary cooldown entry."""

    status: SummaryCooldownResetStatus
    user_id: int
    removed: bool


@dataclass(frozen=True, slots=True)
class EmbedOutputValidationResult:
    """Validation result for slash-command embed rendering requests."""

    status: EmbedOutputValidationStatus


@dataclass(frozen=True, slots=True)
class LinkScanStats:
    malicious: int
    suspicious: int
    harmless: int
    undetected: int

    @property
    def total_engines(self) -> int:
        return self.malicious + self.suspicious + self.harmless + self.undetected


@dataclass(frozen=True, slots=True)
class LinkScanSnapshot:
    """VirusTotal-like link scan result exposed without raw dict indexing."""

    status: LinkScanSnapshotStatus
    severity: LinkScanSeverity | None = None
    stats: LinkScanStats | None = None


@dataclass(frozen=True, slots=True)
class RailCreationResult:
    status: RailCreationStatus
    rail_count: int | None = None
    rail_name: str | None = None


@dataclass(frozen=True, slots=True)
class RouteCreationResult:
    status: RouteCreationStatus
    route_name: str | None = None
    train_name: str | None = None
    dispatch_interval: int | None = None


@dataclass(frozen=True, slots=True)
class RouteRecord:
    route_id: int
    owner_id: int


@dataclass(frozen=True, slots=True)
class RouteDeletionResult:
    status: RouteDeletionStatus
    route_name: str | None = None


@dataclass(frozen=True, slots=True)
class RouteDispatchIntervalUpdateResult:
    status: RouteDispatchIntervalUpdateStatus
    route_name: str | None = None
    dispatch_interval: int | None = None


@dataclass(frozen=True, slots=True)
class ChannelBackupWriteResult:
    status: Literal["written"]
    backup_path: str
    message_count: int


@dataclass(frozen=True, slots=True)
class ChannelBackupLookupResult:
    status: ChannelBackupLookupStatus
    backup_path: str
    manifest: ChannelBackupManifest | None = None


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
