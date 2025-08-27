import sqlite3
from datetime import datetime
from datetime import timedelta
import discord
import asyncio
from discord import app_commands

from commands.define import xp_setting
from commands.define import gpt_chat_threads

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

    c.execute("CREATE TABLE IF NOT EXISTS warn_max (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, max INTEGER)") # 검열기능 사용 여부
    c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, year INTEGER, month INTEGER, date INTEGER, streak INTEGER, max_streak INTEGER)") # 출첵 데이터
    c.execute("CREATE TABLE IF NOT EXISTS anonymous (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, onoff INTEGER, log_channel INTEGER)") # 출첵 데이터
    c.execute("CREATE TABLE IF NOT EXISTS role_description (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, role_id INTEGER, description TEXT)") # 역할 설명
    c.execute("CREATE TABLE IF NOT EXISTS server_perm (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, command TEXT, role_user text, role integer, user integer, perm text)") # 서버별 명령어 권한
    c.execute("CREATE TABLE IF NOT EXISTS channel_perm (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, command TEXT, channel TEXT, role_user text, role integer, user integer, perm text)") # 채널별 명령어 권한
    c.execute("CREATE TABLE IF NOT EXISTS quarantine_role (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, quarantine_role integer)") # 격리 역할
    c.execute("CREATE TABLE IF NOT EXISTS xp_setting (id INTEGER PRIMARY KEY AUTOINCREMENT, onoff INTEGER,server_id INTEGER, chat_xp INTEGER, chat_xp_cooldown INTEGER, voice_xp INTEGER, voice_xp_cooldown INTEGER, unit TEXT)") # 서버별 경험치 기능 설정 테이블
    c.execute("CREATE TABLE IF NOT EXISTS xp (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, xp INTEGER)") # 서버별 경험치 데이터
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
            related_id TEXT
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
    
    c.execute("INSERT INTO mention_delay_user (user_id, sender_id, content, done, server_id, send_type) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, sender_id, content, done, server_id, send_type))
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

def done_mention_delay_user(mention_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
    c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (mention_id,))
    conn.close()

def cancel_mention_delay_user(mention_id: int, admin: bool, trigger_user: int, trigger_server: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()

    if not admin : 
        c.execute("SELECT id FROM mention_delay_user WHERE id = ? AND done = 0 AND sender_id = ?", (mention_id, trigger_user))
        row = c.fetchone()
        if row : 
            c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (mention_id,))
            conn.close()
            return True
        else : 
            return False
    else : 
        c.execute("SELECT id FROM mention_delay_user WHERE id = ? AND done = 0 AND server_id = ? AND send_type = 'reply'", (mention_id, trigger_server))
        row = c.fetchone()
        if row : 
            c.execute("UPDATE mention_delay_user SET done = 1 WHERE id = ?", (mention_id,))
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

def update_anti_nuke_option(server_id: int, time: int):
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

def get_server_link_block(server_id: int):
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

def add_blockhistory(user_id: int, admin_id, reason: str, blocktype: str, addinfo: int, server_id: int):
    conn = sqlite3.connect("garlicbot.db", isolation_level = None)
    c = conn.cursor()
    
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