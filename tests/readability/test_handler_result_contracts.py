from pathlib import Path

from bot_app.types.readability_contracts import (
    AttendanceProcessResult,
    AttendanceRewardResult,
    AttendanceSettings,
    AutomodExecutionResult,
    AutomodExemptionResult,
    ErrorTrackedSlashCommandResult,
    LoopStartResult,
    MessageXpApplyResult,
    ModerationCommandResult,
    SlashCommandResult,
    UserBlockState,
    UserClassificationResult,
    WarningMutationSnapshot,
)


def test_message_handler_result_contracts_are_named_and_readable():
    moderation_result = ModerationCommandResult(
        status="handled",
        error_count=2,
        stop_processing=True,
        reason_code="warn_processed",
    )
    automod_result = AutomodExecutionResult(
        status="handled",
        stop_processing=True,
        reason_code="invite_link",
    )
    loop_result = LoopStartResult(
        status="started",
        started=True,
    )

    assert moderation_result.status == "handled"
    assert moderation_result.error_count == 2
    assert moderation_result.stop_processing is True
    assert automod_result.reason_code == "invite_link"
    assert loop_result.started is True

    slash_result = SlashCommandResult(
        status="completed",
        reason_code="unwarn_processed",
    )
    tracked_slash_result = ErrorTrackedSlashCommandResult(
        status="completed",
        error_count=4,
        reason_code="timeout_processed",
    )
    block_state = UserBlockState(
        status="blocked",
        blocked_until_label="내일",
        reason="테스트",
    )

    assert slash_result.status == "completed"
    assert tracked_slash_result.error_count == 4
    assert block_state.blocked_until_label == "내일"

    automod_exemption = AutomodExemptionResult(
        status="exempt",
        matched_scope="channel",
        matched_channel_id=20,
    )
    message_xp_result = MessageXpApplyResult(
        status="awarded",
        awarded_xp=15,
    )

    assert automod_exemption.matched_scope == "channel"
    assert message_xp_result.awarded_xp == 15

    attendance_reward = AttendanceRewardResult(
        status="success",
        streak=2,
        total_xp=120,
        unit="마늘",
    )

    assert attendance_reward.status == "success"
    assert attendance_reward.total_xp == 120

    attendance_settings = AttendanceSettings(
        on_off=True,
        minimum=100,
        maximum=200,
        step=10,
    )
    attendance_process = AttendanceProcessResult(checked=True, streak=3)
    warning_mutation = WarningMutationSnapshot(old_count=1, delta=2, new_count=3)
    classification = UserClassificationResult(status="premium", label="프리미엄 유저")

    assert attendance_settings.maximum == 200
    assert attendance_process.checked is True
    assert warning_mutation.new_count == 3
    assert classification.label == "프리미엄 유저"


def test_main_connection_points_use_named_handler_results():
    main_source = Path("main.py").read_text(encoding="utf-8")

    assert "moderation_result = await handle_moderation_text_commands(" in main_source
    assert "error = moderation_result.error_count" in main_source
    assert "if moderation_result.stop_processing:" in main_source
    assert "automod_result = await handle_automod_message(" in main_source
    assert "if automod_result.stop_processing:" in main_source


def test_main_slash_connection_points_use_named_slash_results():
    main_source = Path("main.py").read_text(encoding="utf-8")

    assert "warn_command_result = await run_warn_slash_command(" in main_source
    assert "error = warn_command_result.error_count" in main_source
    assert "timeout_command_result = await run_timeout_slash_command(" in main_source
    assert "error = timeout_command_result.error_count" in main_source
    assert "remove_timeout_result = await run_remove_timeout_slash_command(" in main_source
    assert "error = remove_timeout_result.error_count" in main_source


def test_service_boundaries_expose_named_result_objects():
    settings_service_source = Path("bot_app/services/settings_service.py").read_text(encoding="utf-8")
    xp_service_source = Path("bot_app/services/xp_service.py").read_text(encoding="utf-8")

    assert "AutomodExemptionResult" in settings_service_source
    assert "MessageXpApplyResult" in xp_service_source
    assert "AttendanceRewardResult" in xp_service_source
    assert "return MessageXpApplyResult(status=\"awarded\"" in xp_service_source
