from pathlib import Path

from bot_app.types.readability_contracts import (
    AutomodExecutionResult,
    LoopStartResult,
    ModerationCommandResult,
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


def test_main_connection_points_use_named_handler_results():
    main_source = Path("main.py").read_text(encoding="utf-8")

    assert "moderation_result = await handle_moderation_text_commands(" in main_source
    assert "error = moderation_result.error_count" in main_source
    assert "if moderation_result.stop_processing:" in main_source
    assert "automod_result = await handle_automod_message(" in main_source
    assert "if automod_result.stop_processing:" in main_source
