from pathlib import Path

from bot_app.types.readability_contracts import (
    AutomodExecutionResult,
    ErrorTrackedSlashCommandResult,
    LoopStartResult,
    ModerationCommandResult,
    SlashCommandResult,
    UserBlockState,
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
