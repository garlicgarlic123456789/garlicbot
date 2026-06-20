import sqlite3
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import re
import discord
import asyncio
from discord import app_commands
import os
import json

from commands.define import anti_raid_settings_cache, xp_setting
from commands.define import ObsoleteFunctionError
from commands.define import gpt_chat_threads, chat_analyze_onoff_cache, maneul_chat_threads, maneul_chat_limit

def init_db() : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS blockhistory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id integar, admin_id integar, reason text, type text, addinfo integar, server_id integar)") # 제재 내역 테이블
    c.execute("CREATE TABLE IF NOT EXISTS channel (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id integar, message_log integar, reaction_log integar, punish_log_publish integar, punish_log_private integar)") # 서버정보 테이블
    c.execute("CREATE TABLE IF NOT EXISTS blacklist (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id integar, reason text, image_link text, image_private integar, report_user integar, reliability integar)") # 악성유저 테이블
    c.execute("CREATE TABLE IF NOT EXISTS anti_nuke_option (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, ban_kick INTEGER)") # 테러방지
    c.execute("CREATE TABLE IF NOT EXISTS anti_nuke_log_channel (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, channel_id INTEGER)") # 테러방지
    c.execute("CREATE TABLE IF NOT EXISTS anti_nuke_whitelist (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, ban_kick INTEGER)") # 테러 방지 화이트리스트
    c.execute("CREATE TABLE IF NOT EXISTS block_log_channel (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, channel_id INTEGER)") # 제재 로그 채널
    c.execute("CREATE TABLE IF NOT EXISTS server_link_block (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, time INTEGER)") # 제재 로그 채널
    c.execute("CREATE TABLE IF NOT EXISTS invite_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, link TEXT, server_id INTEGER)") # 초대 로그
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_id INTEGER NOT NULL,
            sub_id INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS mention_delay_block (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            blocked INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_join_route (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            join_route TEXT
        )
    ''')
    c.execute("CREATE TABLE IF NOT EXISTS log_channel (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, editdelete INTEGER, reaction INTEGER, role INTEGER, image INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS premium (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, premium INTEGER)") # 프리미엄 계정 여부
    c.execute("CREATE TABLE IF NOT EXISTS automod (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, political INTEGER, sexual INTEGER, invite_link INTEGER, mention INTEGER, whitelist_permission TEXT)") # 검열기능 사용 여부
    # -1은 기능 비활성회, 0은 삭제만 하고 타임아웃하지 않기, 1 이상은 타임아웃.

    c.execute("CREATE TABLE IF NOT EXISTS automod_exception_channel (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, channel_id INTEGER, on_off INTEGER)") # 자동검열 예외 채널
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS warn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            user_id INTEGER,
            warn INTEGER
        )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS warn_max (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, max INTEGER)") # 검열기능 사용 여부
    c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, year INTEGER, month INTEGER, date INTEGER, streak INTEGER, max_streak INTEGER)") # 출첵 데이터
    c.execute("CREATE TABLE IF NOT EXISTS anonymous (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, onoff INTEGER, log_channel INTEGER)") # 출첵 데이터
    c.execute("CREATE TABLE IF NOT EXISTS role_description (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, role_id INTEGER, description TEXT)") # 역할 설명
    c.execute("CREATE TABLE IF NOT EXISTS server_perm (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, command TEXT, role_user text, role integer, user integer, perm text)") # 서버별 명령어 권한
    c.execute("CREATE TABLE IF NOT EXISTS channel_perm (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, command TEXT, channel TEXT, role_user text, role integer, user integer, perm text)") # 채널별 명령어 권한
    c.execute("CREATE TABLE IF NOT EXISTS quarantine_role (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, quarantine_role integer)") # 격리 역할
    c.execute("CREATE TABLE IF NOT EXISTS xp_setting (id INTEGER PRIMARY KEY AUTOINCREMENT, onoff INTEGER,server_id INTEGER, chat_xp INTEGER, chat_xp_cooldown INTEGER, voice_xp INTEGER, voice_xp_cooldown INTEGER, unit TEXT)") # 서버별 경험치 기능 설정 테이블
    c.execute("CREATE TABLE IF NOT EXISTS xp (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, xp INTEGER)") # 서버별 경험치 데이터
    c.execute("CREATE TABLE IF NOT EXISTS monthly_xp (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, year INTEGER, month INTEGER, user_id INTEGER, xp INTEGER)") # 서버별 월간 경험치 데이터
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            on_off INTEGER,
            min INTEGER,
            max INTEGER,
            step INTEGER
        )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS maneul_chat_limit (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date INTEGER, unlimited INTEGER, usage INTEGER)") # 마느라 한도
    c.execute("CREATE TABLE IF NOT EXISTS maneul_chat_threads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, thread_id INTEGER)") # 마느라
    c.execute("CREATE TABLE IF NOT EXISTS gpt_chat_threads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, thread_id INTEGER)") # GPT 채팅 스레드
    c.execute("""
        CREATE TABLE IF NOT EXISTS vote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            creator_id INTEGER,
            selection TEXT,
            result_visible TEXT,
            anonymous INTEGER,
            ongoing INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_vote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_id INTEGER,
            voter_id INTEGER,
            selection TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mention_delay_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender_id INTEGER,
            content TEXT,
            done INTEGER,
            server_id INTEGER,
            send_type TEXT,
            related_id TEXT,
            cancel_together TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS autorole (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            role_id INTEGER,
            bot_user TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS server_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            rule TEXT,
            rule_guide TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS phrase (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            server_id INTEGER,
            user_id INTEGER,
            phrase TEXT
        )
    """)
    # pass_station_visible: 시각표에 통과역을 표시할지 여부(subway는 열차번호 앞에 S, K 등 머리글자가 붙는 열차, train은 머리글자 없는 열차), timetable_delay_visible: 시각표에 지연 정보를 표시할지 여부
    # simple_delay_info: 지연정보 간략화 여부 (3분 미만의 지연 표시 생략)
    c.execute("""
        CREATE TABLE IF NOT EXISTS train_info_option (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subway_pass_station_visible INTEGER,
            train_pass_station_visible INTEGER,
            timetable_delay_visible INTEGER,
            simple_delay_info INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS anti_raid_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            on_off INTEGER,
            action TEXT,
            alert_channel_id INTEGER,
            duration INTEGER,
            join_time INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS railblue_accept (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            accept INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS server_join_route_memo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            invite_link TEXT,
            memo TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_analyze_onoff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            on_off INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_time (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            hour INTEGER,
            minute INTEGER,
            message INTEGER,
            user INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_time_channel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            channel INTEGER,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            hour INTEGER,
            minute INTEGER,
            message INTEGER,
            user INTEGER
        )
    """)
    '''
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id integar UNIQUE, money integar)") # 유저 리스트
    c.execute("CREATE TABLE IF NOT EXISTS rails (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id integar, channel_id integar UNIQUE, rail_cnt integar, name text UNIQUE)") # 노선 (선로)
    c.execute("CREATE TABLE IF NOT EXISTS routes (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id integar, channel_id integar, dispatch_interval integar, name text UNIQUE, train text)") # 운행 계통
    c.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id integar, admin_id integar, reason text, type text, warncnt integar, time text)") # 제재 내역 테이블
    c.execute("CREATE TABLE IF NOT EXISTS warn (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id integar, warn integar)") # 유저 경고 개수
    '''
    conn.close()

'''
c.execute("""
        CREATE TABLE IF NOT EXISTS warn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            user_id INTEGER,
            warn INTEGER
        )
    """)'''

no_support_fuction = {}


def init_dict() : 
    global no_support_fuction

    no_support_fuction = {
        "마느라" : {
            "dm": {

            },
            "guild": {

            }
        }
    }

init_dict()

async def import_xp(server_id: int, file: discord.Attachment, option) : 
    valid_option = ["add", "overwrite"]
    if option not in valid_option : 
        raise ValueError("invalid_option")

    if file.size > 1024 * 1024:
        raise ValueError("file_too_large")
    
    if not file.filename.endswith('.json'):
        raise ValueError("invalid_file_type")
    
    file_bytes = await file.read()
    raw_data = json.loads(file_bytes.decode('utf-8'))

    import_result = {}

    if "data" not in raw_data:
        raise ValueError("invalid_file")
    
    if raw_data.get("file_version") == 1 : 
        import_result["version"] = 1
        valid_data = []
        for entry in raw_data["data"]:
            u_id = entry.get("user_id")
            xp_val = entry.get("xp")
            
            # 데이터 타입 검증: id와 xp가 모두 정수인지 확인
            if isinstance(u_id, int) and isinstance(xp_val, int):
                valid_data.append({"user_id": u_id, "xp": xp_val})
            else:
                continue # 이상한 데이터는 무시

        # 5. DB 작업 (정제된 valid_data만 사용)
        if valid_data:
            import_result["data"] = valid_data
        else:
            raise ValueError("no_data")
    else : 
        raise ValueError("invalid_file_version")
    
    if import_result["version"] == 1 :
        conn = sqlite3.connect("garlicbot.db")
        c = conn.cursor()
        try : 
            if option == "add" : 
                for i in import_result["data"] : 
                    user_id = i["user_id"]
                    xp = i["xp"]
                    c.execute("SELECT 1 FROM xp WHERE server_id = ? AND user_id = ?", (server_id, u_id))

                    if c.fetchone():
                        c.execute("UPDATE xp SET xp = xp + ? WHERE server_id = ? AND user_id = ?", 
                                (xp, server_id, user_id))
                    else:
                        c.execute("INSERT INTO xp (server_id, user_id, xp) VALUES (?, ?, ?)", 
                                (server_id, user_id, xp))
                conn.commit()
            elif option == "overwrite" : 
                c.execute("DELETE FROM xp WHERE server_id = ?", (server_id,))
                
                for i in import_result["data"] : 
                    u_id = i["user_id"]
                    xp_val = i["xp"]

                    if isinstance(u_id, int) and isinstance(xp_val, int):
                        c.execute("INSERT INTO xp (server_id, user_id, xp) VALUES (?, ?, ?)", 
                                (server_id, u_id, xp_val))
                
                # 모든 작업이 성공했을 때만 실제 반영
                conn.commit()
        except Exception as e : 
            conn.rollback()
            raise e
        finally : 
            conn.close()

async def export_xp(server_id: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    query = "SELECT user_id, xp FROM xp WHERE server_id = ?"
    c.execute(query, (server_id,))

    rows = c.fetchall()
    user_data_list = [{"user_id": row[0], "xp": row[1]} for row in rows]

    final_structure = {
        "file_version": 1,
        "data": user_data_list
    }

    file_path = f'export_{server_id}.json'
    if os.path.exists(file_path):
        os.remove(file_path)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_structure, f, indent=4, ensure_ascii=False)

    conn.close()

    return file_path

async def get_server_join_route_memo(server_id: int, invite_link: str) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT memo FROM server_join_route_memo WHERE server_id = ? AND invite_link = ?", (server_id, invite_link,))
    row = c.fetchone()
    if row : 
        return row[0]
    else : 
        return None

async def update_server_join_route_memo(server_id: int, invite_link: str, memo: str) : 
    if memo is not None and len(memo) > 150 : 
        raise ValueError("set_server_join_route_memo() 함수에서 유효하지 않은 값. memo의 값은 150자를 초과할 수 없습니다.")
    if len(invite_link) > 100 : 
        raise ValueError("set_server_join_route_memo() 함수에서 유효하지 않은 값. invite_link의 값은 100자를 초과할 수 없습니다.")
    
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT memo FROM server_join_route_memo WHERE server_id = ? AND invite_link = ?", (server_id, invite_link,))
    row = c.fetchone()
    if row : 
        c.execute("UPDATE server_join_route_memo SET memo = ? WHERE server_id = ? AND invite_link = ?", (memo, server_id, invite_link,))
        return memo
    else : 
        c.execute("INSERT INTO server_join_route_memo (server_id, invite_link, memo) VALUES (?, ?, ?)", (server_id, invite_link, memo))
        return memo

async def delete_server_join_route_memo(server_id: int, invite_link: str) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("DELETE FROM server_join_route_memo WHERE server_id = ? AND invite_link = ?", (server_id, invite_link,))

async def list_server_join_route_memo(server_id: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT invite_link, memo FROM server_join_route_memo WHERE server_id = ?", (server_id,))

    rows = c.fetchall()
    
    result = []
    for row in rows:
        result.append(
            {
                "link": row[0],
                "memo": row[1],
            }
        )
        
    return result

async def add_chat_analyze_data(server_id: int, dt: int, chat_count: int, user_count: int) : 
    dt2 = datetime.strptime(dt, "%Y-%m-%d %H:%M")
    dt2 = {
        "year": dt2.year,
        "month": dt2.month,
        "day": dt2.day, 
        "hour": dt2.hour,
        "minute": dt2.minute
    }
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("INSERT INTO chat_time (server_id, year, month, day, hour, minute, message, user) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (server_id, dt2["year"], dt2["month"], dt2["day"], dt2["hour"], dt2["minute"], chat_count, user_count))
    conn.close()

async def add_chat_analyze_channel_data(server_id: int, channel_id: int, dt: int, chat_count: int, user_count: int) : 
    dt2 = datetime.strptime(dt, "%Y-%m-%d %H:%M")
    dt2 = {
        "year": dt2.year,
        "month": dt2.month,
        "day": dt2.day, 
        "hour": dt2.hour,
        "minute": dt2.minute
    }
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("INSERT INTO chat_time_channel (server_id, channel, year, month, day, hour, minute, message, user) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (server_id, channel_id, dt2["year"], dt2["month"], dt2["day"], dt2["hour"], dt2["minute"], chat_count, user_count))
    conn.close()

async def update_chat_analyze_onoff(server_id: int, onoff: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    chat_analyze_onoff_cache[server_id] = onoff

    if onoff : 
        onoff = 1
    else : 
        onoff = 0

    c.execute("SELECT id FROM chat_analyze_onoff WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE chat_analyze_onoff SET on_off = ? WHERE server_id = ?", (onoff, server_id))
    else:
        c.execute("INSERT INTO chat_analyze_onoff (server_id, on_off) VALUES (?, ?)", (server_id, onoff))
    conn.close()

async def get_chat_analyze_onoff(server_id: int):
    if server_id in chat_analyze_onoff_cache : 
        return chat_analyze_onoff_cache[server_id]
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT on_off FROM chat_analyze_onoff WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    conn.close()
    if row:
        if row[0] == 1 : 
            chat_analyze_onoff_cache[server_id] = True
            return True
        else : 
            chat_analyze_onoff_cache[server_id] = False
            return False
    else : 
        chat_analyze_onoff_cache[server_id] = False
        return False

async def set_warning(server_id: int, user_id: int, warn: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT warn FROM warn WHERE server_id = ? AND user_id = ?", (server_id, user_id,))
    row = c.fetchone()
    if row : 
        c.execute("UPDATE warn SET warn = ? WHERE server_id = ? AND user_id = ?", (warn, server_id, user_id,))
        return warn
    else : 
        c.execute("INSERT INTO warn (server_id, user_id, warn) VALUES (?, ?, ?)", (server_id, user_id, warn))
        return warn

async def add_warning(server_id: int, user_id: int, adding: int) : 
    old_warning_cnt = await load_warning(server_id, user_id)
    new_warning = old_warning_cnt + adding
    new_warning_cnt = await set_warning(server_id, user_id, new_warning)
    return [old_warning_cnt, adding, new_warning_cnt]

async def remove_warning(server_id: int, user_id: int, removing: int) : 
    old_warning_cnt = await load_warning(server_id, user_id)
    if old_warning_cnt < removing : 
        new_warning = 0
    else :
        new_warning = old_warning_cnt - removing
    new_warning_cnt = await set_warning(server_id, user_id, new_warning)
    return [old_warning_cnt, removing, new_warning_cnt]

async def load_warning(server_id: int, user_id: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT warn FROM warn WHERE server_id = ? AND user_id = ?", (server_id, user_id,))
    row = c.fetchone()
    if row : 
        return row[0]
    else : 
        return 0

async def railblue_accept_get(user_id: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT accept FROM railblue_accept WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row : 
        if row[0] == 1 : 
            return True
        else : 
            return False
    else : 
        return False

async def railblue_accept_update(user_id: int, accept: bool) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT accept FROM railblue_accept WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if accept : 
        accept = 1
    else : 
        accept = 0
    if row : 
        c.execute("UPDATE railblue_accept SET accept = ? WHERE user_id = ?", (accept, user_id,))
    else : 
        c.execute("INSERT INTO railblue_accept (accept, user_id) VALUES (?, ?)", (accept, user_id,))

async def reset_exp(server_id: int, check: bool = False) : 
    if not check : 
        raise ValueError("reset_exp() 함수는 특정 서버의 경험치를 모두 초기화시킵니다. 초기화 후에는 복구할 수 없으니 주의하세요. 이 내용을 확인하였다면 함수의 check 매개변수 값을 True로 설정하여 이 함수를 실행합니다.")
        return
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS xp_backup (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, xp INTEGER)") # 서버별 경험치 데이터
    c.execute("SELECT user_id, xp FROM xp WHERE server_id = ?", (server_id,))
    rows = c.fetchall()
    for row in rows:
        user_id = row[0]
        xp = row[1]
        c.execute("INSERT INTO xp_backup (server_id, user_id, xp) VALUES (?, ?, ?)", (server_id, user_id, xp))
    c.execute("DELETE FROM xp WHERE server_id = ?", (server_id,))
    conn.close()

async def update_attendance_settings(server_id: int, on_off: int, minimum: int, maximum: int, step: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT id FROM attendance_settings WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    
    if row:
        c.execute("UPDATE attendance_settings SET on_off = ?, min = ?, max = ?, step = ? WHERE server_id = ?", (on_off, minimum, maximum, step, server_id))
    else:
        c.execute("INSERT INTO attendance_settings (server_id, on_off, min, max, step) VALUES (?, ?, ?, ?, ?)", (server_id, on_off, minimum, maximum, step))

    conn.close()

async def get_attendance_settings(server_id: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT * FROM attendance_settings WHERE server_id = ?", (server_id,))
    row = c.fetchone()

    if row : 
        if row[2] == 1 : 
            on_off = True
        else : 
            on_off = False
        minimum = row[3]
        maximum = row[4]
        step = row[5]
        return {
            "on_off": on_off,
            "minimum": minimum,
            "maximum": maximum,
            "step": step,
        }
    else : 
        on_off = False
        return {
            "on_off": on_off,
            "minimum": 0,
            "maximum": 0,
            "step": 1,
        }

async def get_anti_raid_settings(server_id: int) : 
    global anti_raid_settings_cache
    
    if server_id in anti_raid_settings_cache : 
        return anti_raid_settings_cache[server_id]
    else : 
        conn = sqlite3.connect("garlicbot.db", isolation_level = None)
        c = conn.cursor()
        c.execute("SELECT * FROM anti_raid_settings WHERE server_id = ?", (server_id,))
        row = c.fetchone()

        if row : 
            if row[2] == 1 : 
                temp = True
            else : 
                temp = False
            anti_raid_settings_cache[server_id] = {
                "on_off": temp,
                "action": row[3],
                "alert_channel_id": row[4],
                "duration": row[5],
                "join_time": row[6],
            }
        else : 
            anti_raid_settings_cache[server_id] = {
                "on_off": False,
                "action": "alert",
                "alert_channel_id": None,
                "duration": 180,
                "join_time": 5,
            }
        
        conn.close()
        return anti_raid_settings_cache[server_id]

async def update_anti_raid_settings(server_id: int, on_off: bool, action: str, alert_channel_id: int, duration: int, join_time: int) : 
    if duration > 900 or duration < 30 :
        raise ValueError("update_anti_raid_settings() 함수에서 유효하지 않은 값. duration의 값은 900보다 크거나 30보다 작을 수 없습니다.")
    
    if join_time > 50 or join_time < 3 : 
        raise ValueError("update_anti_raid_settings() 함수에서 유효하지 않은 값. join_time의 값은 50보다 크거나 3보다 작을 수 없습니다.")

    global anti_raid_settings_cache
    
    anti_raid_settings_cache[server_id] = {
        "on_off": on_off,
        "action": action,
        "alert_channel_id": alert_channel_id,
        "duration": duration,
        "join_time": join_time
    }
    
    if on_off : 
        on_off2 = 1
    else : 
        on_off2 = 0
    
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT id FROM anti_raid_settings WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    
    if row:
        c.execute("UPDATE anti_raid_settings SET on_off = ?, action = ?, alert_channel_id = ?, duration = ?, join_time = ? WHERE server_id = ?", (on_off2, action, alert_channel_id, duration, join_time, server_id))
    else:
        c.execute("INSERT INTO anti_raid_settings (server_id, on_off, action, alert_channel_id, duration, join_time) VALUES (?, ?, ?, ?, ?, ?)", (server_id, on_off2, action, alert_channel_id, duration, join_time))

    conn.close()

    anti_raid_settings_cache[server_id] = {
        "on_off": on_off,
        "action": action,
        "alert_channel_id": alert_channel_id,
        "duration": duration,
        "join_time": join_time
    }

async def remove_phrase(phrase_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("DELETE FROM phrase WHERE id = ?", (phrase_id,))
    conn.close()

async def add_phrase(name: str, type: str, server_id, user_id, phrase: str):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("INSERT INTO phrase (name, type, server_id, user_id, phrase) VALUES (?, ?, ?, ?, ?)", (name, type, server_id, user_id, phrase))
    conn.close()

async def get_user_all_phrase(user_id: int):
    phrases = []
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT * FROM phrase WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    for row in rows:
        phrases.append({
            "id": row[0],
            "name": row[1],
            "phrase": row[5]
        })
    return phrases

async def get_server_all_phrase(server_id: int, is_admin: bool):
    phrases = []
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    if is_admin:
        c.execute("SELECT * FROM phrase WHERE server_id = ? AND type = ?", (server_id, "server_admin",))
        rows = c.fetchall()
        for row in rows:
            phrases.append({
                "id": row[0],
                "name": row[1],
                "phrase": row[5]
            })
        c.execute("SELECT * FROM phrase WHERE server_id = ? AND type = ?", (server_id, "server_all",))
        rows = c.fetchall()
        conn.close()
        for row in rows:
            phrases.append({
                "id": row[0],
                "name": row[1],
                "phrase": row[5]
            })
        return phrases
    else:
        c.execute("SELECT * FROM phrase WHERE server_id = ? AND type = ?", (server_id, "server_all",))
        rows = c.fetchall()
        conn.close()
        for row in rows:
            phrases.append({
                "id": row[0],
                "name": row[1],
                "phrase": row[5]
            })
        return phrases

async def get_phrase(phrase_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT * FROM phrase WHERE id = ?", (phrase_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "server_id": row[3],
            "user_id": row[4],
            "phrase": row[5]
        }
    else : 
        return None

async def get_phrase_by_name(name: str, user_id: int, server_id: int, is_admin: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT * FROM phrase WHERE name = ? AND user_id = ?", (name, user_id))
    row = c.fetchone()
    if row:
        conn.close()
        return {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "server_id": row[3],
            "user_id": row[4],
            "phrase": row[5]
        }
    else : 
        if is_admin:
            c.execute("SELECT * FROM phrase WHERE name = ? AND server_id = ? AND type = ?", (name, server_id, "server_admin"))
            row = c.fetchone()
            if row:
                conn.close()
                return {
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "server_id": row[3],
                    "user_id": row[4],
                    "phrase": row[5]
                }
            else : 
                c.execute("SELECT * FROM phrase WHERE name = ? AND server_id = ? AND type = ?", (name, server_id, "server_all"))
                row = c.fetchone()
                if row:
                    conn.close()
                    return {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "server_id": row[3],
                        "user_id": row[4],
                        "phrase": row[5]
                    }
                else : 
                    conn.close()
                    return None
        c.execute("SELECT * FROM phrase WHERE name = ? AND server_id = ? AND type = ?", (name, server_id, "server_all"))
        row = c.fetchone()
        if row:
            conn.close()
            return {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "server_id": row[3],
                "user_id": row[4],
                "phrase": row[5]
            }
        else : 
            conn.close()
            return None

async def phrase_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    phrases = await get_user_all_phrase(interaction.user.id)
    phrases += await get_server_all_phrase(interaction.guild.id, interaction.user.guild_permissions.ban_members)
    return [
        app_commands.Choice(name=phrase["name"], value=str(phrase["id"]))
        for phrase in phrases if current.lower() in phrase["name"].lower()
    ][:25]  # 최대 25개만 반환 가능

async def delete_server_rules(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT id FROM server_rules WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM server_rules WHERE server_id = ?", (server_id,))
    else : 
        return [False, "server_rules_not_found"]
    conn.close()
    return [True, "success"]

async def update_server_rules(server_id: int, rule: str, rule_guide):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT id FROM server_rules WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE server_rules SET rule = ?, rule_guide = ? WHERE server_id = ?", (rule, rule_guide, server_id))
    else:
        c.execute("INSERT INTO server_rules (server_id, rule, rule_guide) VALUES (?, ?, ?)", (server_id, rule, rule_guide))
    conn.close()

async def get_server_rules(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT * FROM server_rules WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return [True, row[2], row[3]]
    else : 
        return [False, None, None]

async def add_autorole(server_id: int, role_id: id, bot_user: str):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    # 기존에 이미 있는 행인지 확인.
    c.execute("SELECT id FROM autorole WHERE server_id = ? AND role_id = ?", (server_id, role_id))
    row = c.fetchone()
    if row:
        return [False, "autorole_already_exists", None]
    # 추가
    c.execute("INSERT INTO autorole (server_id, role_id, bot_user) VALUES (?, ?, ?)", (server_id, role_id, bot_user))
    autorole_id = c.lastrowid
    conn.close()
    return [True, "success", autorole_id]

async def remove_autorole(server_id: int, role_id: id):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    # 있는지 확인
    c.execute("SELECT id FROM autorole WHERE server_id = ? AND role_id = ?", (server_id, role_id))
    row = c.fetchone()
    if not row:
        return [False, "autorole_not_found", None]
    # 제거
    c.execute("DELETE FROM autorole WHERE server_id = ? AND role_id = ?", (server_id, role_id))
    conn.close()
    return [True, "success", None]

async def get_autorole(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT * FROM autorole WHERE server_id = ?", (server_id,))
    rows = c.fetchall()
    conn.close()
    autoroles = []
    for row in rows:
        autoroles.append({
            "server_id": row[1],
            "role_id": row[2],
            "bot_user": row[3]
        })
    return autoroles

async def migrate_mention_delay_user():
    import json
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    with open("mentions.json", "r", encoding = "utf-8") as f : 
        mentions = json.load(f)
    
    for mention in mentions : 
        if "send_type" not in mention : 
            mention["send_type"] = "reply"
        if "server_id" not in mention : 
            mention["server_id"] = 1320303102703702037
        elif mention["server_id"] == 0 : 
            mention["server_id"] = None
        c.execute(
            """
            INSERT INTO mention_delay_user (id, user_id, sender_id, content, done, server_id, send_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id = excluded.user_id,
                sender_id = excluded.sender_id,
                content = excluded.content,
                done = excluded.done,
                server_id = excluded.server_id,
                send_type = excluded.send_type
            """,
            (mention["id"], mention["user_id"], mention["sender_id"], mention["content"], mention["done"], mention["server_id"], mention["send_type"])
        )
        await asyncio.sleep(0.03)
    conn.close()

def add_mention_delay_user(user_id: int, sender_id: int, content: str, done: int, server_id: int, send_type: str):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("INSERT INTO mention_delay_user (user_id, sender_id, content, done, server_id, send_type) VALUES (?, ?, ?, ?, ?, ?)", (user_id, sender_id, content, done, server_id, send_type))
    last_id = c.lastrowid
    conn.close()
    return last_id

def process_mention_relation(related_id: list) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    related = ",".join(related_id)
    for i in related_id : 
        c.execute("SELECT id FROM mention_delay_user WHERE id = ?", (i,))
        row = c.fetchone()
        if row : 
            c.execute("UPDATE mention_delay_user SET related_id = ? WHERE id = ?", (related, i))
    conn.close()

def process_mention_cancel_together(cancel_together: list) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    cancel_together2 = ",".join(cancel_together)
    for i in cancel_together : 
        c.execute("SELECT id FROM mention_delay_user WHERE id = ?", (i,))
        row = c.fetchone()
        if row :
            c.execute("UPDATE mention_delay_user SET cancel_together = ? WHERE id = ?", (cancel_together2, i))
    conn.close()

def done_mention_delay_user(mention_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (mention_id,))
    conn.close()

def cancel_mention_delay_user(mention_id: int, admin: bool, trigger_user: int, trigger_server: int, cancel_together: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    if not admin : 
        c.execute("SELECT cancel_together FROM mention_delay_user WHERE id = ? AND done = 0 AND sender_id = ?", (mention_id, trigger_user))
        row = c.fetchone()
        if row : 
            c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (mention_id,))
            if cancel_together : 
                if row[0] is not None : 
                    cancel_together_list = row[0].split(",")
                    for i in cancel_together_list : 
                        c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (i,))
                    conn.close()
                    return True
            conn.close()
            return True
        else : 
            return False
    else : 
        c.execute("SELECT cancel_together FROM mention_delay_user WHERE id = ? AND done = 0 AND server_id = ? AND send_type = 'reply'", (mention_id, trigger_server))
        row = c.fetchone()
        if row : 
            c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (mention_id,))
            if cancel_together : 
                if row[0] is not None : 
                    cancel_together_list = row[0].split(",")
                    for i in cancel_together_list : 
                        c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (i,))
                    conn.close()
                    return True
            conn.close()
            return True
        else : 
            conn.close()
            return False

def get_mention_delay_user(user_id: int, type: str = "all", server_id: int = None):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    if type == "all" : 
        c.execute("SELECT * FROM mention_delay_user WHERE user_id = ? AND done = 0", (user_id,))
    elif type == "server" : 
        c.execute("SELECT * FROM mention_delay_user WHERE user_id = ? AND server_id = ? AND done = 0 AND send_type = 'reply'", (user_id, server_id))
    rows = c.fetchall()
    conn.close()
    mentions = []
    for i in rows : 
        mentions.append({
            "id": i[0],
            "user_id": i[1],
            "sender_id": i[2],
            "content": i[3],
            "done": i[4],
            "server_id": i[5],
            "send_type": i[6],
            "related_id": i[7],
        })
    return mentions

def reset_gpt_chat_thread(user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("DELETE FROM gpt_chat_threads WHERE user_id = ?", (user_id,))
    if user_id in gpt_chat_threads : 
        del gpt_chat_threads[user_id]
    conn.close()

def update_gpt_chat_thread(user_id: int, thread_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT id FROM gpt_chat_threads WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE gpt_chat_threads SET thread_id = ? WHERE user_id = ?", (thread_id, user_id))
    else:
        c.execute("INSERT INTO gpt_chat_threads (user_id, thread_id) VALUES (?, ?)", (user_id, thread_id))
    
    conn.close()

def get_gpt_chat_thread(user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT thread_id FROM gpt_chat_threads WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

'''
c.execute("CREATE TABLE IF NOT EXISTS maneul_chat_limit (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date INTEGER, unlimited INTEGER, usage INTEGER)") # 마느라 한도
c.execute("CREATE TABLE IF NOT EXISTS maneul_chat_threads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, thread_id INTEGER)") # 마느라
'''

def add_maneul_chat_usage(user_id: int) : # 마느리 대화 기능 한도 도달했는지 확인 및 도달 안했으면 이용량 +1
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day

    date = f"{year}{month:02d}{day:02d}"

    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    c.execute("SELECT date, usage, unlimited FROM maneul_chat_limit WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row : 
        if row[2] == 1 : 
            return True
        elif row[2] == 0 : 
            if row[0] == date : 
                if row[1] >= maneul_chat_limit : 
                    return False
                new_usage = row[1] + 1
                c.execute("UPDATE maneul_chat_limit SET usage = ? WHERE user_id = ?", (new_usage, user_id))
                return True
            else : 
                if 0 >= maneul_chat_limit : 
                    return False
                c.execute("UPDATE maneul_chat_limit SET usage = 1, date = ? WHERE user_id = ?", (date, user_id))
                return True
    else : 
        if maneul_chat_limit <= 0 : 
            return False
        c.execute("INSERT INTO maneul_chat_limit (user_id, date, unlimited, usage) VALUES (?, ?, 0, 1)", (user_id, date))
        return True

def update_maneul_chat_thread(user_id: int, thread_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT id FROM maneul_chat_threads WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE maneul_chat_threads SET thread_id = ? WHERE user_id = ?", (thread_id, user_id))
    else:
        c.execute("INSERT INTO maneul_chat_threads (user_id, thread_id) VALUES (?, ?)", (user_id, thread_id))
    
    conn.close()

def get_maneul_chat_thread(user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT thread_id FROM maneul_chat_threads WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def get_all_xp_setting():
    global xp_setting
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT server_id FROM xp_setting")
    rows = c.fetchall()
    conn.close()
    for i in rows : 
        xp_setting[i[0]] = get_xp_setting(i[0])

def update_xp_setting(server_id: int, onoff: bool, chat_xp: int, chat_xp_cooldown: int, voice_xp: int, voice_xp_cooldown: int, unit: str):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    onoff_bool = onoff

    if onoff : 
        onoff = 1
    else : 
        onoff = 0
    
    c.execute("SELECT id FROM xp_setting WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    
    if row:
        c.execute("UPDATE xp_setting SET onoff = ?, chat_xp = ?, chat_xp_cooldown = ?, voice_xp = ?, voice_xp_cooldown = ?, unit = ? WHERE server_id = ?", (onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit, server_id))
    else:
        c.execute("INSERT INTO xp_setting (server_id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit) VALUES (?, ?, ?, ?, ?, ?, ?)", (server_id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit))
    
    xp_setting[server_id] = [onoff_bool, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit]

    conn.close()

def get_xp_setting_dict(server_id: int):
    if server_id not in xp_setting : 
        return [False, None, None, None, None, None]
    return xp_setting[server_id]

def get_xp_setting(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit FROM xp_setting WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    conn.close()
    if row : 
        onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit = row
        if unit is None : 
            unit = ""
        if onoff == 1 : 
            onoff = True
        else : 
            onoff = False
        return [onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit]
    return [False, None, None, None, None, None]

def update_xp(server_id: int, user_id: int, xp: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT xp FROM xp WHERE server_id = ? AND user_id = ?", (server_id, user_id))
    row = c.fetchone()
    
    if row : 
        current_xp = row[0]
        new_xp = current_xp + xp
        c.execute("UPDATE xp SET xp = ? WHERE server_id = ? AND user_id = ?", (new_xp, server_id, user_id))
    else : 
        c.execute("INSERT INTO xp (server_id, user_id, xp) VALUES (?, ?, ?)", (server_id, user_id, xp))
    
    conn.close()

def get_all_xp(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT user_id, xp FROM xp WHERE server_id = ?", (server_id,))
    rows = c.fetchall()
    conn.close()
    users_xp = {}
    for i in rows : 
        users_xp[i[0]] = i[1]
    return users_xp

def get_xp(server_id: int, user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT xp FROM xp WHERE server_id = ? AND user_id = ?", (server_id, user_id))
    row = c.fetchone()
    conn.close()
    if row : 
        return row[0]
    return 0

def update_month_xp(server_id: int, user_id: int, xp: int):
    now = datetime.now()
    year = now.year
    month = now.month

    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT xp FROM monthly_xp WHERE server_id = ? AND year = ? AND month = ? AND user_id = ?", (server_id, year, month, user_id))
    row = c.fetchone()
    
    if row : 
        current_xp = row[0]
        new_xp = current_xp + xp
        c.execute("UPDATE monthly_xp SET xp = ? WHERE server_id = ? AND year = ? AND month = ? AND user_id = ?", (new_xp, server_id, year, month, user_id))
    else : 
        c.execute("INSERT INTO monthly_xp (server_id, year, month, user_id, xp) VALUES (?, ?, ?, ?, ?)", (server_id, year, month, user_id, xp))
    
    conn.close()

def get_all_month_xp(server_id: int):
    now = datetime.now()
    year = now.year
    month = now.month

    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute("SELECT user_id, xp FROM monthly_xp WHERE server_id = ? AND year = ? AND month = ?", (server_id, year, month))
    rows = c.fetchall()
    conn.close()
    users_xp = {}
    for i in rows : 
        users_xp[i[0]] = i[1]
    return users_xp

def get_month_xp(server_id: int, user_id: int):
    now = datetime.now()
    year = now.year
    month = now.month
    
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT xp FROM monthly_xp WHERE server_id = ? AND year = ? AND month = ? AND user_id = ?", (server_id, year, month, user_id))
    row = c.fetchone()
    conn.close()
    if row : 
        return row[0]
    return 0

def get_old_xp(server_id: int, user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT xp FROM xp_backup WHERE server_id = ? AND user_id = ?", (server_id, user_id))
    row = c.fetchone()
    conn.close()
    if row : 
        return row[0]
    return None

def update_user_join_route(user_id: int, join_route: str):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    c.execute("SELECT id FROM user_join_route WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE user_join_route SET join_route = ? WHERE user_id = ?", (join_route, user_id))
    else:
        c.execute("INSERT INTO user_join_route (user_id, join_route) VALUES (?, ?)", (user_id, join_route))
    conn.close()

def get_user_join_route(user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT join_route FROM user_join_route WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def update_mention_delay_block(blocker_id: int, blocked_id: int, blocked: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    if blocked : 
        blocked = 1
    else : 
        blocked = 0
    c.execute("SELECT id FROM mention_delay_block WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE mention_delay_block SET blocked = ? WHERE blocker_id = ? AND blocked_id = ?", (blocked, blocker_id, blocked_id))
    else:
        c.execute("INSERT INTO mention_delay_block (blocker_id, blocked_id, blocked) VALUES (?, ?, ?)", (blocker_id, blocked_id, blocked))
    
    conn.close()

def get_mention_delay_block(blocker_id: int, blocked_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT blocked FROM mention_delay_block WHERE blocker_id = ? AND blocked_id = ?", (blocker_id, blocked_id))
    row = c.fetchone()
    conn.close()
    if row:
        if row[0] == 1 : 
            return True
        else : 
            return False
    return False

def update_quarantine_role(server_id: int, quarantine_role: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT id FROM quarantine_role WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE quarantine_role SET quarantine_role = ? WHERE server_id = ?", (quarantine_role, server_id))
    else:
        c.execute("INSERT INTO quarantine_role (server_id, quarantine_role) VALUES (?, ?)", (server_id, quarantine_role))

def get_quarantine_role(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT quarantine_role FROM quarantine_role WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    if row:
        return row[0]
    return None

def update_automod_exception_channel(server_id: int, channel_id: int, on_off: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    if on_off : 
        on_off = 1
    else : 
        on_off = 0
    c.execute("SELECT id FROM automod_exception_channel WHERE server_id = ? AND channel_id = ?", (server_id, channel_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE automod_exception_channel SET on_off = ? WHERE server_id = ? AND channel_id = ?", (on_off, server_id, channel_id))
    else : 
        c.execute("INSERT INTO automod_exception_channel (server_id, channel_id, on_off) VALUES (?, ?, ?)", (server_id, channel_id, on_off))

def get_automod_exception_channel(server_id: int, channel_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT on_off FROM automod_exception_channel WHERE server_id = ? AND channel_id = ?", (server_id, channel_id))
    row = c.fetchone()
    if row:
        if row[0] == 1 : 
            return True
        else : 
            return False
    return False

def update_server_perm(server_id: int, command: str, role_user: str, role, user, perm):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT id FROM server_perm WHERE server_id = ? AND command = ?", (server_id, command))
    row = c.fetchone()
    if row:
        c.execute("UPDATE server_perm SET role_user = ?, role = ?, user = ?, perm = ? WHERE server_id = ? AND command = ?", (role_user, role, user, perm, server_id, command))
    else:
        c.execute("INSERT INTO server_perm (server_id, command, role_user, role, user, perm) VALUES (?, ?, ?, ?, ?, ?)", (server_id, command, role_user, role, user, perm))

def get_server_perm(server_id: int, command: str, role, user):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    if role is not None : 
        c.execute("SELECT perm FROM server_perm WHERE server_id = ? AND command = ? AND role = ?", (server_id, command, role))
    elif user is not None : 
        c.execute("SELECT perm FROM server_perm WHERE server_id = ? AND command = ? AND user = ?", (server_id, command, user))
    else : 
        return None
    
    row = c.fetchone()
    if row:
        return row[0]
    return None

def update_channel_perm(server_id: int, command: str, channel: str, role_user: str, role, user, perm):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT id FROM channel_perm WHERE server_id = ? AND command = ? AND channel = ? AND role = ?", (server_id, command, channel, role))
    row = c.fetchone()
    if row:
        c.execute("UPDATE channel_perm SET perm = ? WHERE server_id = ? AND command = ? AND channel = ? AND role_user = ? AND role = ?", (perm, server_id, command, channel, role_user, role))
    else:
        c.execute("INSERT INTO channel_perm (server_id, command, channel, role_user, role, user, perm) VALUES (?, ?, ?, ?, ?, ?, ?)", (server_id, command, channel, role_user, role, user, perm))

def get_channel_perm(server_id: int, command: str, channel: str, role, user):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    if role is not None : 
        c.execute("SELECT perm FROM channel_perm WHERE server_id = ? AND command = ? AND channel = ? AND role = ?", (server_id, command, channel, role))
    elif user is not None : 
        c.execute("SELECT perm FROM channel_perm WHERE server_id = ? AND command = ? AND channel = ? AND user = ?", (server_id, command, channel, user))
    else : 
        return None
    
    row = c.fetchone()
    if row:
        return row[0]
    return None

async def check_perm(message, command: str):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    server_id = message.guild.id
    user = message.author.id
    channel = message.channel.id

    perm = get_channel_perm(server_id, command, channel, None, user)
    if perm is not None : 
        return perm
    
    role = message.author.roles

    # 유저가 가진 역할 상위 역할부터 정렬
    role = sorted(role, key=lambda x: x.position, reverse=True)

    for i in role : 
        perm = get_channel_perm(server_id, command, channel, i.id, None)
        if perm is not None : 
            return perm
    
    for i in role : 
        perm = get_server_perm(server_id, command, i.id, None)
        if perm is not None : 
            return perm

    return "allow"

def update_role_description(server_id: int, role_id: int, description):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT id FROM role_description WHERE server_id = ? AND role_id = ?", (server_id, role_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE role_description SET description = ? WHERE server_id = ? AND role_id = ?", (description, server_id, role_id))
    else:
        c.execute("INSERT INTO role_description (server_id, role_id, description) VALUES (?, ?, ?)", (server_id, role_id, description))

def get_role_description(server_id: int, role_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT description FROM role_description WHERE server_id = ? AND role_id = ?", (server_id, role_id))
    row = c.fetchone()
    if row:
        return row[0]
    return None

def update_anonymous_setting(server_id: int, onoff: bool, log_channel):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    if onoff : 
        onoff = 1
    else : 
        onoff = 0
    # user_id 존재 여부 확인
    c.execute("SELECT id FROM anonymous WHERE server_id = ?", (server_id,))
    row = c.fetchone()

    if row:
        # 존재하면 업데이트
        c.execute("UPDATE anonymous SET onoff = ?, log_channel = ? WHERE server_id = ?", (onoff, log_channel, server_id))
    else:
        # 없으면 삽입
        c.execute("INSERT INTO anonymous (server_id, onoff, log_channel) VALUES (?, ?, ?)", (server_id, onoff, log_channel))

def get_anonymous_setting(server_id: int) : 
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("""
        SELECT onoff, log_channel
        FROM anonymous
        WHERE server_id = ?
    """, (server_id,))
    row = c.fetchone()
    
    if row:
        onoff, log_channel = row[0], row[1]

        if onoff == 1 : 
            onoff = True
        elif onoff == 0 : 
            onoff = False
        else : 
            onoff = None
        
        return onoff, log_channel
    else : 
        return False, None

def update_warn_max(server_id: int, max_warn):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # user_id 존재 여부 확인
    c.execute("SELECT id FROM warn_max WHERE server_id = ?", (server_id,))
    row = c.fetchone()

    if row:
        # 존재하면 업데이트
        c.execute("UPDATE warn_max SET max = ? WHERE server_id = ?", (max_warn, server_id))
    else:
        # 없으면 삽입
        c.execute("INSERT INTO warn_max (server_id, max) VALUES (?, ?)", (server_id, max_warn))

def get_warn_max(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT max FROM warn_max WHERE server_id = ?", (server_id,))
    result = c.fetchone()
    if result:
        return result[0]
    return None

# premium 값 업데이트 또는 삽입 (fetchone 방식)
def update_premium(user_id: int, premium: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    premium_value = 1 if premium else 0

    # user_id 존재 여부 확인
    c.execute("SELECT id FROM premium WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if row:
        # 존재하면 업데이트
        c.execute("UPDATE premium SET premium = ? WHERE user_id = ?", (premium_value, user_id))
    else:
        # 없으면 삽입
        c.execute("INSERT INTO premium (user_id, premium) VALUES (?, ?)", (user_id, premium_value))


def get_premium(user_id: int) -> bool:
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT premium FROM premium WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result:
        return bool(result[0])
    return False


#server_id INTEGER, political INTEGER, sexual INTEGER, invite_link INTEGER, mention INTEGER)") # 검열기능 사용 여부

def update_automod(server_id, political: list, sexual: list, invite_link: list, mention: list, whitelist_permission):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # 먼저 server_id가 있는지 확인
    c.execute("SELECT id FROM automod WHERE server_id = ?", (server_id,))
    row = c.fetchone()

    political = political[1] if political[0] else -1
    sexual = sexual[1] if sexual[0] else -1
    invite_link = invite_link[1] if invite_link[0] else -1
    mention = mention[1] if mention[0] else -1
    
    if row:
        # 존재할 경우 update
        c.execute("""
            UPDATE automod 
            SET political = ?, sexual = ?, invite_link = ?, mention = ?, whitelist_permission = ?
            WHERE server_id = ?
        """, (political, sexual, invite_link, mention, whitelist_permission, server_id))
    else:
        # 없을 경우 insert
        c.execute("""
            INSERT INTO automod (server_id, political, sexual, invite_link, mention, whitelist_permission)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (server_id, political, sexual, invite_link, mention, whitelist_permission))

def get_automod(server_id):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("""
        SELECT political, sexual, invite_link, mention, whitelist_permission
        FROM automod
        WHERE server_id = ?
    """, (server_id,))
    row = c.fetchone()
    
    if row:
        political, sexual, invite_link, mention, whitelist_permission = row[0], row[1], row[2], row[3], row[4]
        if political == -1 : 
            political = [False, 0]
        else : 
            political = [True, political]
        if sexual == -1 :
            sexual = [False, 0]
        else : 
            sexual = [True, sexual]
        if invite_link == -1 :
            invite_link = [False, 0]
        else : 
            invite_link = [True, invite_link]
        if mention == -1 :
            mention = [False, 0]
        else : 
            mention = [True, mention]
        if whitelist_permission is None:
            whitelist_permission = 'admin'
        
        return {
            'political': political,
            'sexual': sexual,
            'invite_link': invite_link,
            'mention': mention,
            'whitelist_permission': whitelist_permission
        }
    else:
        return {
            'political': [False, 0],  # 검열 기능 비활성화
            'sexual': [False, 0],
            'invite_link': [False, 0],
            'mention': [False, 0],
            'whitelist_permission': 'admin'
        }

def update_log_channel(server_id, editdelete, reaction, role, image):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # 먼저 server_id가 있는지 확인
    c.execute("SELECT id FROM log_channel WHERE server_id = ?", (server_id,))
    row = c.fetchone()
    
    if row:
        # 존재할 경우 update
        c.execute("""
            UPDATE log_channel 
            SET editdelete = ?, reaction = ?, role = ?, image = ?
            WHERE server_id = ?
        """, (editdelete, reaction, role, image, server_id))
    else:
        # 없을 경우 insert
        c.execute("""
            INSERT INTO log_channel (server_id, editdelete, reaction, role, image)
            VALUES (?, ?, ?, ?, ?)
        """, (server_id, editdelete, reaction, role, image))

def get_log_channel(server_id):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("""
        SELECT editdelete, reaction, role, image
        FROM log_channel
        WHERE server_id = ?
    """, (server_id,))
    row = c.fetchone()
    
    if row:
        return {
            'editdelete': row[0],  # None일 경우 자동으로 Python의 None
            'reaction': row[1],
            'role': row[2],
            'image': row[3]
        }
    else:
        return {
            'editdelete': None,
            'reaction': None,
            'role': None,
            'image': None
        }

def import_invite_log(server_id: int, user_id: int) -> list[str | None]:
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT link FROM invite_log WHERE user_id = ? AND server_id = ?", (user_id, server_id))
    rows = c.fetchall()
    
    if not rows:
        return [None]
    
    return [row[0] for row in rows]


# 초대 로그 저장 함수
def save_invite_log(user_id: int, link: str | None, server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("INSERT INTO invite_log (user_id, link, server_id) VALUES (?, ?, ?)", (user_id, link, server_id))


def migrate_blockhistory(before: int, after: int, server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # user_id가 before이고 server_id가 일치하는 모든 row의 user_id 값을 after로 업데이트
    c.execute(
        "UPDATE blockhistory SET user_id = ? WHERE user_id = ? AND server_id = ?",
        (after, before, server_id)
    )


def add_account_relation(main_id: int, sub_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO accounts (main_id, sub_id) VALUES (?, ?)
    ''', (main_id, sub_id))

def get_related_accounts(account_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # 그래프 탐색을 위한 준비
    visited = set()
    to_visit = [account_id]

    while to_visit:
        current = to_visit.pop()
        if current in visited:
            continue
        visited.add(current)

        # main_id → sub_id
        c.execute('SELECT sub_id FROM accounts WHERE main_id = ?', (current,))
        subs = [row[0] for row in c.fetchall()]

        # sub_id → main_id
        c.execute('SELECT main_id FROM accounts WHERE sub_id = ?', (current,))
        mains = [row[0] for row in c.fetchall()]

        # 방문하지 않은 연결된 노드 추가
        to_visit.extend([acc for acc in subs + mains if acc not in visited])
    return sorted(visited)

def remove_account_relation(main_id: int, sub_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute('''
        DELETE FROM accounts WHERE main_id = ? AND sub_id = ?
    ''', (main_id, sub_id))

def update_block_log_channel(server_id: int, channel_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # server_id로 row 존재 여부 확인
    c.execute("SELECT 1 FROM block_log_channel WHERE server_id = ?", (server_id,))
    exists = c.fetchone()

    if exists:
        # 있으면 channel_id 업데이트
        c.execute("""
            UPDATE block_log_channel 
            SET channel_id = ? 
            WHERE server_id = ?
        """, (channel_id, server_id))
    else:
        # 없으면 새 row 삽입
        c.execute("""
            INSERT INTO block_log_channel (server_id, channel_id) 
            VALUES (?, ?)
        """, (server_id, channel_id))

def get_block_log_channel(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    # server_id로 channel_id 조회
    c.execute("SELECT channel_id FROM block_log_channel WHERE server_id = ?", (server_id,))
    result = c.fetchone()

    if result is not None:
        return result[0]  # channel_id 반환
    else:
        return 0  # 해당 server_id가 없을 경우

def update_anti_nuke_log_channel(server_id: int, channel_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # server_id로 row 존재 여부 확인
    c.execute("SELECT 1 FROM anti_nuke_log_channel WHERE server_id = ?", (server_id,))
    exists = c.fetchone()

    if exists:
        # 있으면 channel_id 업데이트
        c.execute("""
            UPDATE anti_nuke_log_channel 
            SET channel_id = ? 
            WHERE server_id = ?
        """, (channel_id, server_id))
    else:
        # 없으면 새 row 삽입
        c.execute("""
            INSERT INTO anti_nuke_log_channel (server_id, channel_id) 
            VALUES (?, ?)
        """, (server_id, channel_id))

def get_anti_nuke_log_channel(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    # server_id로 channel_id 조회
    c.execute("SELECT channel_id FROM anti_nuke_log_channel WHERE server_id = ?", (server_id,))
    result = c.fetchone()

    if result is not None:
        return result[0]  # channel_id 반환
    else:
        return None  # 해당 server_id가 없을 경우

async def get_all_anti_nuke_notify_channel(check: bool = False) : 
    if check == False : 
        raise ObsoleteFunctionError("이 함수는 개발명령 28을 위해 개발되었습니다. 무엇을 하는 함수인지 자세히 모른다면 테스트 환경에서 테스트 진행 후 \'check\' 매개변수의 값을 True로 변경하여 사용하십시오..")
        return
    
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT server_id, channel_id FROM anti_nuke_log_channel")
    rows = c.fetchall()

    conn.close()

    return rows

def update_anti_nuke_option(server_id: int, ban_kick: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    # bool 값을 정수로 변환
    ban_kick_value = 1 if ban_kick else 0

    # server_id에 해당하는 행이 있는지 확인
    c.execute("SELECT 1 FROM anti_nuke_option WHERE server_id = ?", (server_id,))
    exists = c.fetchone()

    if exists:
        # 있으면 업데이트
        c.execute("UPDATE anti_nuke_option SET ban_kick = ? WHERE server_id = ?", (ban_kick_value, server_id))
    else:
        # 없으면 새 행 삽입
        c.execute("INSERT INTO anti_nuke_option (server_id, ban_kick) VALUES (?, ?)", (server_id, ban_kick_value))


def get_anti_nuke_option(server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # ban_kick 값 조회
    c.execute("SELECT ban_kick FROM anti_nuke_option WHERE server_id = ?", (server_id,))
    result = c.fetchone()

    if result is not None:
        return bool(result[0])  # 1이면 True, 0이면 False
    else:
        return False  # 해당 server_id가 없을 경우

def update_server_link_block(server_id: int, time: int, force: bool = False):
    if not force : 
        raise ObsoleteFunctionError("더 이상 사용되지 않는 함수입니다. 이 함수를 지속해서 사용하려는 경우 \'force\' 매개변수를 True로 설정하고 이 함수를 호출하십시오.")
    
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    

    # server_id에 해당하는 행이 있는지 확인
    c.execute("SELECT 1 FROM server_link_block WHERE server_id = ?", (server_id,))
    exists = c.fetchone()

    if exists:
        # 있으면 업데이트
        c.execute("UPDATE server_link_block SET time = ? WHERE server_id = ?", (time, server_id))
    else:
        # 없으면 새 행 삽입
        c.execute("INSERT INTO server_link_block (server_id, time) VALUES (?, ?)", (server_id, time))

def get_server_link_block(server_id: int, force: bool = False):
    if not force : 
        raise ObsoleteFunctionError("더 이상 사용되지 않는 함수입니다. 이 함수를 지속해서 사용하려는 경우 \'force\' 매개변수를 True로 설정하고 이 함수를 호출하십시오.")
    
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT time FROM server_link_block WHERE server_id = ?", (server_id,))
    result = c.fetchone()

    if result is not None:
        return result[0]
    else:
        return 0  # 해당 server_id가 없을 경우

def update_anti_nuke_whitelist(server_id: int, user_id: int, ban_kick: bool):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # bool 값을 정수로 변환
    ban_kick_value = 1 if ban_kick else 0

    # server_id와 user_id로 해당 row 존재 여부 확인
    c.execute("""
        SELECT 1 FROM anti_nuke_whitelist 
        WHERE server_id = ? AND user_id = ?
    """, (server_id, user_id))
    exists = c.fetchone()

    if exists:
        # 있으면 ban_kick 값 업데이트
        c.execute("""
            UPDATE anti_nuke_whitelist 
            SET ban_kick = ? 
            WHERE server_id = ? AND user_id = ?
        """, (ban_kick_value, server_id, user_id))
    else:
        # 없으면 새 row 삽입
        c.execute("""
            INSERT INTO anti_nuke_whitelist (server_id, user_id, ban_kick) 
            VALUES (?, ?, ?)
        """, (server_id, user_id, ban_kick_value))

def get_anti_nuke_whitelist(server_id: int, user_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # ban_kick 값 조회
    c.execute("""
        SELECT ban_kick FROM anti_nuke_whitelist 
        WHERE server_id = ? AND user_id = ?
    """, (server_id, user_id))
    result = c.fetchone()

    if result is not None:
        return bool(result[0])  # 1이면 True, 0이면 False
    else:
        return False  # 해당 row가 없을 경우 False 반환

# c.execute("CREATE TABLE IF NOT EXISTS blacklist (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id integar, reason text, image_link text, image_private integar, report_user integar, reliability integar)") # 악성유저 테이블
def add_blacklist(user_id, reason, image_link, image_private, report_user, reliability):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO blacklist (user_id, reason, image_link, image_private, report_user, reliability)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, reason, image_link, image_private, report_user, reliability))

def check_blacklist(user_id):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("SELECT reason, image_link, image_private, report_user, reliability FROM blacklist WHERE user_id = ?", (user_id,))
    result = c.fetchone()

    if result:
        return [True, result[0], result[1], result[2], result[3], result[4]]
    else:
        return [False, None, None, None, None, None]
def delete_blacklist(user_id) :
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))

def remove_blockhistory(id) :
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("DELETE FROM blockhistory WHERE id = ?", (id,))
    c.close()

def decode_match(match):
    # 매칭된 텍스트를 확인
    matched_text = match.group(0)

    if matched_text == "\\\\n":
        return "\\n"  # 사용자가 \\n을 입력했다면 -> 텍스트 '\n'으로 변경
    else:
        return "\n"  # 사용자가 \n을 입력했다면 -> 진짜 줄바꿈으로 변경

def add_blockhistory(user_id: int, admin_id, reason: str, blocktype: str, addinfo: int, server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    reason2 = re.sub(r"\\\\n|\\n", decode_match, reason)
    reason = reason2
    
    c.execute("""
        INSERT INTO blockhistory (user_id, admin_id, reason, type, addinfo, server_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, admin_id, reason, blocktype, addinfo, server_id))

# 시작하기
def db_add_channel(server_id, message_log, reaction_log, punish_log_publish, punish_log_private):# 데이터 삽입
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO channel (server_id, message_log, reaction_log, punish_log_publish, punish_log_private)
        VALUES (?, ?, ?, ?, ?)
    """, (server_id, message_log, reaction_log, punish_log_publish, punish_log_private))


def check_user_exists(user_id):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    

    c.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)", (user_id,))
    return c.fetchone()[0]  # 1이면 존재, 0이면 존재하지 않음


def check_rail_exists(channel_id) :
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    

    c.execute("SELECT EXISTS(SELECT 1 FROM rails WHERE channel_id = ?)", (channel_id,))
    return c.fetchone()[0]  # 1이면 존재, 0이면 존재하지 않음

def process_attendance(server_id, user_id):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    # 현재 날짜 정보
    today = datetime.now()
    year, month, date = today.year, today.month, today.day

    # 기존 출석 정보 확인
    c.execute("SELECT year, month, date, streak FROM attendance WHERE server_id = ? AND user_id = ?", (server_id, user_id))
    row = c.fetchone()

    if row:
        last_date = datetime(row[0], row[1], row[2])
        streak = row[3]

        if last_date.date() == today.date():
            # 이미 오늘 출석함
            return False, streak

        elif last_date.date() == (today - timedelta(days=1)).date():
            # 어제도 출석했다면 연속 출석
            streak += 1
            max_streak = streak
        else:
            # 연속 출석 실패
            max_streak = streak
            streak = 1

        # 기존 레코드 업데이트
        c.execute("""
            UPDATE attendance
            SET year = ?, month = ?, date = ?, streak = ?, max_streak = ?
            WHERE server_id = ? AND user_id = ?
        """, (year, month, date, streak, max_streak, server_id, user_id))

    else:
        # 첫 출석 기록
        streak = 1
        max_streak = 1
        c.execute("""
            INSERT INTO attendance (server_id, user_id, year, month, date, streak, max_streak)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (server_id, user_id, year, month, date, streak, max_streak))
    
    return True, streak


# DB에서 고유한 join_route 값 가져오기
def get_all_join_routes():
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute('SELECT DISTINCT join_route FROM user_join_route WHERE join_route IS NOT NULL')
    results = c.fetchall()
    return [row[0] for row in results]


# 자동완성 함수
async def join_route_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    routes = get_all_join_routes()
    return [
        app_commands.Choice(name=route, value=route)
        for route in routes if current.lower() in route.lower()
    ][:25]  # 최대 25개만 반환 가능

async def migrate_old_blockhistory(interaction: discord.Interaction, channel: discord.TextChannel) : 
    res = await interaction.original_response()
    
    kst = timezone(timedelta(hours=9))
    dt_kst = datetime.fromtimestamp(1739773800, tz=kst)
    dt_utc = dt_kst.astimezone(timezone.utc)
    messages = [message async for message in channel.history(limit = None, before=dt_utc, oldest_first = False)]

    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS blockhistory_old')
    c.execute("CREATE TABLE IF NOT EXISTS blockhistory_old (id INTEGER PRIMARY KEY AUTOINCREMENT, output_id integar, user_id integar, admin_id integar, reason text, type text, addinfo integar)") # 제재 내역 테이블

    adding = []

    for message in messages : 
        migrate_msg = f" (이 제재 내역은 마늘이가 제재 내역을 db에 기록하지 않던 시기(2025년 2월 17일 15시 30분 이전)의 제재 내역을 <#1320304892992028785>을 바탕으로 2025년 10월 31일에 이전한 것입니다. 일부 정보가 부정확하거나 누락되어 있을 수 있습니다. | 원본 제재 내역: {message.jump_url})"
        if message.author.id == 495574108046753814 : 
            for i in message.embeds : 
                if "언밴" in i.title : 
                    blocktype = "unban"
                elif "밴" in i.title : 
                    blocktype = "ban"
                elif "타임아웃" in i.title : 
                    blocktype = "timeout"
                elif "경고 차감" in i.title : 
                    blocktype = "unwarn"
                elif "경고" in i.title : 
                    blocktype = "warn"
                elif "킥" in i.title or "추방" in i.title : 
                    blocktype = "kick"
                
                for j in i.fields : 
                    if j.name == "유저" : 
                        pattern = r"<@!?(\d+)>"
                        match = re.search(pattern, j.value)
                        if match:
                            blockuser = int(match.group(1))
                        else : 
                            blockuser = None
                    elif j.name == "관리자" : 
                        pattern = r"<@!?(\d+)>"
                        match = re.search(pattern, j.value)
                        if match:
                            blockadmin = int(match.group(1))
                        else : 
                            blockadmin = None
                    elif j.name == "사유" : 
                        if j.value == "없음" : 
                            blockreason = "*(사유 입력되지 않음)*" + migrate_msg
                        else : 
                            blockreason = j.value + migrate_msg
                    elif j.name == "경고 개수" : 
                        if blocktype == "warn" : 
                            pattern = r'\(\+\s*(\d+)\)'
                            match = re.search(pattern, j.value)
                            if match:
                                blockaddinfo = int(match.group(1))
                            else : 
                                blockaddinfo = None
                        elif blocktype == "unwarn" : 
                            pattern = r'\(-?(\d+)\)'
                            match = re.search(pattern, j.value)
                            if match:
                                blockaddinfo = int(match.group(1))
                            else : 
                                blockaddinfo = None
                    elif j.name == "시간" : 
                        if blocktype == "timeout" : 
                            if "분" in j.value : 
                                blockaddinfo = int(j.value[:-1]) * 60
                            elif "시간" in j.value : 
                                blockaddinfo = int(j.value[:-2]) * 60 * 60
                            elif "초" in j.value : 
                                blockaddinfo = int(j.value[:-1])
                            elif "일" in j.value : 
                                blockaddinfo = int(j.value[:-1]) * 60 * 60 * 24
                
                if not 'blockaddinfo' in locals():
                    blockaddinfo = 0

                adding.append([blockuser, blockadmin, blockreason, blocktype, blockaddinfo])
        elif message.author.id == 1316579106749681664 : 
            for i in message.embeds : 
                if "차단 해제" in i.title : 
                    blocktype = "unban"
                elif "차단" in i.title : 
                    blocktype = "ban"
                elif "타임아웃 해제" in i.title : 
                    blocktype = "untimeout"
                elif "타임아웃" in i.title : 
                    blocktype = "timeout"
                elif "경고 차감" in i.title : 
                    blocktype = "unwarn"
                elif "경고" in i.title : 
                    blocktype = "warn"
                elif "추방" in i.title : 
                    blocktype = "kick"
                
                for j in i.fields : 
                    if j.name == "사용자" : 
                        userlist = j.value.split(", ")
                        if len(userlist) == 1 : 
                            usercount = 1
                            pattern = r"<@!?(\d+)>"
                            match = re.search(pattern, userlist[0])
                            if match:
                                blockuser = int(match.group(1))
                            else : 
                                blockuser = None
                        else : 
                            usercount = len(userlist)
                            blockuser = []
                            for k in userlist : 
                                match = re.search(pattern, k)
                                if match:
                                    blockuser.append(int(match.group(1)))
                                else : 
                                    blockuser.append(None)

                    elif j.name == "관리자" : 
                        pattern = r"<@!?(\d+)>"
                        match = re.search(pattern, j.value)
                        if match:
                            blockadmin = match.group(1)
                        else : 
                            blockadmin = None
                    elif j.name == "사유" : 
                        if j.value == "없음" : 
                            blockreason = "*(사유 입력되지 않음)*" + migrate_msg
                        else : 
                            blockreason = j.value + migrate_msg

                if not 'blockaddinfo' in locals():
                    blockaddinfo = 0

                if usercount == 1 : 
                    adding.append([blockuser, blockadmin, blockreason, blocktype, None])
                else : 
                    for i in blockuser : 
                        adding.append([i, blockadmin, blockreason, blocktype, None])
    
    output_id = -1

    for i in adding : 
        c.execute("""
            INSERT INTO blockhistory_old (output_id, user_id, admin_id, reason, type, addinfo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (output_id, i[0], i[1], i[2], i[3], i[4]))
        output_id -= 1
    
    await res.reply("작업이 처리되었습니다.", mention_author = False)
    await interaction.user.send("작업이 처리되었습니다.")
