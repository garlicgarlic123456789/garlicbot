import ast
import warnings
from pathlib import Path


EXPECTED_ACTIVE_COMMAND_NAMES = {
    "대화초기화",
    "출석체크",
    "경험치확인",
    "경험치선물",
    "경험치샵구매",
    "경험치도박",
    "경험치수정",
    "경험치순위",
    "사용자정보",
    "경고한도설정",
    "경고",
    "경고차감",
    "경고확인",
    "추방",
    "차단",
    "일괄차단",
    "차단해제",
    "일괄차단해제",
    "로그채널설정",
    "타임아웃",
    "타임아웃해제",
    "동일인여부확인",
    "판사",
    "대화요약쿨타임해제",
    "생성형인공지능",
    "제재내역확인",
    "일괄삭제",
    "초대링크삭제",
    "보안조치",
    "이용제한",
    "이용제한해제",
    "이용제한확인",
    "도움말광질",
    "채널명령어권한설정",
    "서버명령어권한설정",
    "개발명령",
    "해결처리",
    "서버조언",
    "자동검열예외채널설정",
    "자동검열설정",
    "격리역할설정",
    "격리",
    "테러방지설정",
    "테러방지화이트리스트",
    "역할설명수정",
    "역할정보",
    "초대링크메모",
    "유입경로확인",
    "선로신설",
    "운행계통신설",
    "운행계통폐지",
    "운행계통배차간격변경",
    "정보",
}

EXPECTED_INACTIVE_LEGACY_FUNCTIONS = {
    "이메일전송",
    "revoke_permissions",
    "update_anonymous_setting_command",
    "chat1",
    "check_likeability_command",
    "add_likeability_command",
    "embed",
    "link_check",
    "minecraft",
}


def _parse_main_module() -> ast.Module:
    source = Path("main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(source)


def test_phase7_active_runtime_command_set_is_stable():
    module_ast = _parse_main_module()
    active_command_names = set()

    for node in module_ast.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "command":
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    active_command_names.add(keyword.value.value)

    assert active_command_names == EXPECTED_ACTIVE_COMMAND_NAMES


def test_phase7_inactive_legacy_functions_stay_out_of_runtime_ast():
    module_ast = _parse_main_module()
    function_names = {node.name for node in ast.walk(module_ast) if isinstance(node, ast.AsyncFunctionDef)}

    for function_name in EXPECTED_INACTIVE_LEGACY_FUNCTIONS:
        assert function_name not in function_names


def test_phase7_main_drops_dead_handler_imports_from_removed_runtime_paths():
    source = Path("main.py").read_text(encoding="utf-8")
    import_block = source.split("parser = argparse.ArgumentParser()", 1)[0]

    assert "run_backup_channel_slash_command" not in import_block
    assert "run_check_user_join_route_slash_command" not in import_block
    assert "run_restore_channel_slash_command" not in import_block
    assert "run_set_user_join_route_slash_command" not in import_block
    assert "run_add_likeability_slash_command" not in import_block
    assert "run_check_likeability_slash_command" not in import_block
    assert "run_embed_output_slash_command" not in import_block
    assert "run_link_check_slash_command" not in import_block


def test_phase7_removed_low_value_legacy_blocks_do_not_return():
    source = Path("main.py").read_text(encoding="utf-8")

    assert 'model_name = "google/gemma-2-2b-it"' not in source
    assert "def send_email(sender_name, sender_display_name, sender_id, content):" not in source
    assert "VOICE_CHANNEL_IDS =" not in source
    assert 'async def 이메일전송(interaction: discord.Interaction, 내용: str):' not in source
    assert '@bot.tree.command(name = "광질"' not in source


def test_phase7_main_collapses_duplicate_helpers_to_single_definition():
    source = Path("main.py").read_text(encoding="utf-8")

    assert source.count("def load_data():") == 1
    assert source.count("def save_data(data):") == 1
    assert source.count("def load_blocked_users():") == 1
    assert source.count("def save_blocked_users(blocked_users):") == 1


def test_phase7_archives_high_value_inactive_legacy_blocks_outside_main():
    source = Path("main.py").read_text(encoding="utf-8")
    archive = Path("bot_app/legacy/main_inactive_archive.md").read_text(encoding="utf-8")

    assert 'elif 버전 == "v2"' not in source
    assert '@bot.tree.command(name="권한회수"' not in source
    assert '@bot.tree.command(name = "익명채팅설정"' not in source
    assert '@bot.tree.command(name = "익명채팅"' not in source
    assert '@bot.tree.command(name = "호감도확인"' not in source
    assert '@bot.tree.command(name = "호감도추가"' not in source
    assert '@bot.tree.command(name = "임베드출력"' not in source
    assert '@bot.tree.command(name = "링크검사"' not in source

    assert 'elif 버전 == "v2"' in archive
    assert '@bot.tree.command(name="권한회수"' in archive
    assert '@bot.tree.command(name = "익명채팅설정"' in archive
    assert '@bot.tree.command(name = "익명채팅"' in archive
