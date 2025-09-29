"""
GarlicBot Database Service

데이터베이스 연결 및 쿼리 작업을 담당하는 서비스 모듈입니다.
기존 database.py의 모든 기능을 클래스 기반으로 재구성하였습니다.
"""

import sqlite3
from datetime import datetime, timedelta
import discord
import asyncio
import logging
from typing import List, Dict, Optional, Tuple, Any


class DatabaseService:
    """데이터베이스 서비스 클래스"""

    def __init__(self, db_path: str = "garlicbot.db"):
        self.db_path = db_path
        self.logger = logging.getLogger('GarlicBot.Database')
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 반환합니다."""
        return sqlite3.connect(self.db_path, isolation_level=None)

    def _init_db(self):
        """데이터베이스 테이블들을 초기화합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()

            # 제재 내역 테이블
            c.execute("""CREATE TABLE IF NOT EXISTS blockhistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                admin_id INTEGER,
                reason TEXT,
                type TEXT,
                addinfo INTEGER,
                server_id INTEGER
            )""")

            # 서버정보 테이블
            c.execute("""CREATE TABLE IF NOT EXISTS channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                message_log INTEGER,
                reaction_log INTEGER,
                punish_log_publish INTEGER,
                punish_log_private INTEGER
            )""")

            # 악성유저 테이블
            c.execute("""CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                image_link TEXT,
                image_private INTEGER,
                report_user INTEGER,
                reliability INTEGER
            )""")

            # 테러방지 옵션
            c.execute("""CREATE TABLE IF NOT EXISTS anti_nuke_option (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                ban_kick INTEGER
            )""")

            # 테러방지 로그 채널
            c.execute("""CREATE TABLE IF NOT EXISTS anti_nuke_log_channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                channel_id INTEGER
            )""")

            # 테러 방지 화이트리스트
            c.execute("""CREATE TABLE IF NOT EXISTS anti_nuke_whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                user_id INTEGER,
                ban_kick INTEGER
            )""")

            # 제재 로그 채널
            c.execute("""CREATE TABLE IF NOT EXISTS block_log_channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                channel_id INTEGER
            )""")

            # 서버 링크 차단
            c.execute("""CREATE TABLE IF NOT EXISTS server_link_block (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                time INTEGER
            )""")

            # 초대 로그
            c.execute("""CREATE TABLE IF NOT EXISTS invite_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                link TEXT,
                server_id INTEGER
            )""")

            # 계정 연결
            c.execute("""CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                main_id INTEGER NOT NULL,
                sub_id INTEGER NOT NULL
            )""")

            # 멘션 지연 차단
            c.execute("""CREATE TABLE IF NOT EXISTS mention_delay_block (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker_id INTEGER NOT NULL,
                blocked_id INTEGER NOT NULL,
                blocked INTEGER NOT NULL
            )""")

            # 사용자 가입 경로
            c.execute("""CREATE TABLE IF NOT EXISTS user_join_route (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                join_route TEXT
            )""")

            # 로그 채널 설정
            c.execute("""CREATE TABLE IF NOT EXISTS log_channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                editdelete INTEGER,
                reaction INTEGER,
                role INTEGER,
                image INTEGER
            )""")

            # 프리미엄 계정
            c.execute("""CREATE TABLE IF NOT EXISTS premium (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                premium INTEGER
            )""")

            # 자동 검열 기능
            c.execute("""CREATE TABLE IF NOT EXISTS automod (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                political INTEGER,
                sexual INTEGER,
                invite_link INTEGER,
                mention INTEGER,
                whitelist_permission TEXT
            )""")

            # 자동검열 예외 채널
            c.execute("""CREATE TABLE IF NOT EXISTS automod_exception_channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                channel_id INTEGER,
                on_off INTEGER
            )""")

            # 추가 테이블들...
            self._create_additional_tables(c)

            conn.commit()
            self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def _create_additional_tables(self, cursor: sqlite3.Cursor):
        """추가 테이블들을 생성합니다."""
        # XP 설정 테이블
        cursor.execute("""CREATE TABLE IF NOT EXISTS xp_setting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER UNIQUE,
            onoff BOOLEAN DEFAULT 1,
            chat_xp INTEGER DEFAULT 10,
            chat_xp_cooldown INTEGER DEFAULT 60,
            voice_xp INTEGER DEFAULT 5,
            voice_xp_cooldown INTEGER DEFAULT 300,
            unit TEXT DEFAULT 'XP'
        )""")

        # XP 데이터 테이블
        cursor.execute("""CREATE TABLE IF NOT EXISTS xp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            user_id INTEGER,
            xp INTEGER DEFAULT 0,
            UNIQUE(server_id, user_id)
        )""")

        # 멘션 지연 테이블
        cursor.execute("""CREATE TABLE IF NOT EXISTS mention_delay (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender_id INTEGER,
            content TEXT,
            done INTEGER DEFAULT 0,
            server_id INTEGER,
            send_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # GPT 채팅 스레드
        cursor.execute("""CREATE TABLE IF NOT EXISTS gpt_chat_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            thread_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # 격리 역할 설정
        cursor.execute("""CREATE TABLE IF NOT EXISTS quarantine_role (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER UNIQUE,
            role_id INTEGER
        )""")

        # 자동 역할 설정
        cursor.execute("""CREATE TABLE IF NOT EXISTS autorole (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            role_id INTEGER,
            bot_user TEXT
        )""")

    # ===== 멘션 지연 관련 메소드들 =====

    def add_mention_delay_user(self, user_id: int, sender_id: int, content: str,
                              done: int, server_id: int, send_type: str) -> int:
        """멘션 지연 메시지를 추가합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO mention_delay (user_id, sender_id, content, done, server_id, send_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, sender_id, content, done, server_id, send_type))
            return c.lastrowid
        except Exception as e:
            self.logger.error(f"Failed to add mention delay: {e}")
            return None

    def process_mention_relation(self, related_id: List[int]) -> List[Dict]:
        """관련된 멘션 지연 항목들을 처리합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()

            placeholders = ','.join('?' * len(related_id))
            c.execute(f"""
                SELECT id, user_id, sender_id, content, server_id, send_type
                FROM mention_delay
                WHERE id IN ({placeholders}) AND done = 0
            """, related_id)

            results = []
            for row in c.fetchall():
                results.append({
                    'id': row[0],
                    'user_id': row[1],
                    'sender_id': row[2],
                    'content': row[3],
                    'server_id': row[4],
                    'send_type': row[5]
                })
            return results
        except Exception as e:
            self.logger.error(f"Failed to process mention relation: {e}")
            return []

    def done_mention_delay_user(self, mention_id: int) -> bool:
        """멘션 지연 항목을 완료 처리합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("UPDATE mention_delay SET done = 1 WHERE id = ?", (mention_id,))
            return c.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to mark mention delay as done: {e}")
            return False

    def cancel_mention_delay_user(self, mention_id: int, admin: bool,
                                 trigger_user: int, trigger_server: int) -> bool:
        """멘션 지연 항목을 취소합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()

            # 관리자가 아니면 자신의 메시지만 취소 가능
            if not admin:
                c.execute("""
                    SELECT sender_id FROM mention_delay
                    WHERE id = ? AND sender_id = ?
                """, (mention_id, trigger_user))
                if not c.fetchone():
                    return False

            c.execute("DELETE FROM mention_delay WHERE id = ?", (mention_id,))
            return c.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to cancel mention delay: {e}")
            return False

    def get_mention_delay_user(self, user_id: int, type: str = "all",
                              server_id: int = None) -> List[Dict]:
        """사용자의 멘션 지연 항목들을 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()

            query = """
                SELECT id, sender_id, content, done, server_id, send_type, created_at
                FROM mention_delay
                WHERE user_id = ?
            """
            params = [user_id]

            if type == "pending":
                query += " AND done = 0"
            elif type == "done":
                query += " AND done = 1"

            if server_id is not None:
                query += " AND server_id = ?"
                params.append(server_id)

            query += " ORDER BY created_at DESC"

            c.execute(query, params)
            results = []
            for row in c.fetchall():
                results.append({
                    'id': row[0],
                    'sender_id': row[1],
                    'content': row[2],
                    'done': bool(row[3]),
                    'server_id': row[4],
                    'send_type': row[5],
                    'created_at': row[6]
                })
            return results
        except Exception as e:
            self.logger.error(f"Failed to get mention delay: {e}")
            return []

    # ===== GPT 채팅 스레드 관련 메소드들 =====

    def reset_gpt_chat_thread(self, user_id: int) -> bool:
        """사용자의 GPT 채팅 스레드를 초기화합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM gpt_chat_threads WHERE user_id = ?", (user_id,))
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset GPT chat thread: {e}")
            return False

    def update_gpt_chat_thread(self, user_id: int, thread_id: int) -> bool:
        """사용자의 GPT 채팅 스레드를 업데이트합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO gpt_chat_threads (user_id, thread_id, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (user_id, thread_id))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update GPT chat thread: {e}")
            return False

    def get_gpt_chat_thread(self, user_id: int) -> Optional[int]:
        """사용자의 GPT 채팅 스레드를 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT thread_id FROM gpt_chat_threads WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get GPT chat thread: {e}")
            return None

    # ===== XP 시스템 관련 메소드들 =====

    def get_all_xp_setting(self) -> List[Dict]:
        """모든 서버의 XP 설정을 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT server_id, onoff, chat_xp, chat_xp_cooldown,
                       voice_xp, voice_xp_cooldown, unit
                FROM xp_setting
            """)

            results = []
            for row in c.fetchall():
                results.append({
                    'server_id': row[0],
                    'onoff': bool(row[1]),
                    'chat_xp': row[2],
                    'chat_xp_cooldown': row[3],
                    'voice_xp': row[4],
                    'voice_xp_cooldown': row[5],
                    'unit': row[6]
                })
            return results
        except Exception as e:
            self.logger.error(f"Failed to get all XP settings: {e}")
            return []

    def update_xp_setting(self, server_id: int, onoff: bool, chat_xp: int,
                         chat_xp_cooldown: int, voice_xp: int, voice_xp_cooldown: int,
                         unit: str) -> bool:
        """서버의 XP 설정을 업데이트합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO xp_setting
                (server_id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (server_id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update XP setting: {e}")
            return False

    def get_xp_setting_dict(self, server_id: int) -> Dict:
        """서버의 XP 설정을 딕셔너리로 반환합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit
                FROM xp_setting WHERE server_id = ?
            """, (server_id,))

            row = c.fetchone()
            if row:
                return {
                    'onoff': bool(row[0]),
                    'chat_xp': row[1],
                    'chat_xp_cooldown': row[2],
                    'voice_xp': row[3],
                    'voice_xp_cooldown': row[4],
                    'unit': row[5]
                }
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get XP setting dict: {e}")
            return {}

    def get_xp_setting(self, server_id: int) -> Tuple[bool, int, int, int, int, str]:
        """서버의 XP 설정을 튜플로 반환합니다."""
        setting = self.get_xp_setting_dict(server_id)
        if setting:
            return (setting['onoff'], setting['chat_xp'], setting['chat_xp_cooldown'],
                   setting['voice_xp'], setting['voice_xp_cooldown'], setting['unit'])
        return (True, 10, 60, 5, 300, 'XP')  # 기본값

    def update_xp(self, server_id: int, user_id: int, xp: int) -> bool:
        """사용자의 XP를 업데이트합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO xp (server_id, user_id, xp)
                VALUES (?, ?, ?)
            """, (server_id, user_id, xp))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update XP: {e}")
            return False

    def get_all_xp(self, server_id: int) -> List[Tuple[int, int]]:
        """서버의 모든 사용자 XP를 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT user_id, xp FROM xp WHERE server_id = ? ORDER BY xp DESC",
                     (server_id,))
            return c.fetchall()
        except Exception as e:
            self.logger.error(f"Failed to get all XP: {e}")
            return []

    def get_xp(self, server_id: int, user_id: int) -> int:
        """특정 사용자의 XP를 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT xp FROM xp WHERE server_id = ? AND user_id = ?",
                     (server_id, user_id))
            result = c.fetchone()
            return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to get XP: {e}")
            return 0

    # ===== 사용자 가입 경로 관련 메소드들 =====

    def update_user_join_route(self, user_id: int, join_route: str) -> bool:
        """사용자의 가입 경로를 업데이트합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO user_join_route (user_id, join_route)
                VALUES (?, ?)
            """, (user_id, join_route))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update user join route: {e}")
            return False

    def get_user_join_route(self, user_id: int) -> Optional[str]:
        """사용자의 가입 경로를 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT join_route FROM user_join_route WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get user join route: {e}")
            return None

    # ===== 멘션 차단 관련 메소드들 =====

    def update_mention_delay_block(self, blocker_id: int, blocked_id: int, blocked: bool) -> bool:
        """멘션 차단 설정을 업데이트합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO mention_delay_block (blocker_id, blocked_id, blocked)
                VALUES (?, ?, ?)
            """, (blocker_id, blocked_id, int(blocked)))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update mention delay block: {e}")
            return False

    def get_mention_delay_block(self, blocker_id: int, blocked_id: int) -> bool:
        """멘션 차단 상태를 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT blocked FROM mention_delay_block
                WHERE blocker_id = ? AND blocked_id = ?
            """, (blocker_id, blocked_id))
            result = c.fetchone()
            return bool(result[0]) if result else False
        except Exception as e:
            self.logger.error(f"Failed to get mention delay block: {e}")
            return False

    # ===== 격리 역할 관련 메소드들 =====

    def update_quarantine_role(self, server_id: int, quarantine_role: int) -> bool:
        """서버의 격리 역할을 설정합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO quarantine_role (server_id, role_id)
                VALUES (?, ?)
            """, (server_id, quarantine_role))
            return True
        except Exception as e:
            self.logger.error(f"Failed to update quarantine role: {e}")
            return False

    def get_quarantine_role(self, server_id: int) -> Optional[int]:
        """서버의 격리 역할을 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT role_id FROM quarantine_role WHERE server_id = ?", (server_id,))
            result = c.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get quarantine role: {e}")
            return None

    # ===== 자동 역할 관련 메소드들 =====

    def add_autorole(self, server_id: int, role_id: int, bot_user: str) -> Tuple[bool, str, Optional[int]]:
        """자동 역할을 추가합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            # 기존에 이미 있는 행인지 확인
            c.execute("SELECT id FROM autorole WHERE server_id = ? AND role_id = ?", (server_id, role_id))
            row = c.fetchone()
            if row:
                return False, "autorole_already_exists", None
            # 추가
            c.execute("INSERT INTO autorole (server_id, role_id, bot_user) VALUES (?, ?, ?)", (server_id, role_id, bot_user))
            autorole_id = c.lastrowid
            return True, "success", autorole_id
        except Exception as e:
            self.logger.error(f"Failed to add autorole: {e}")
            return False, str(e), None

    def remove_autorole(self, server_id: int, role_id: int) -> Tuple[bool, str, Optional[None]]:
        """자동 역할을 제거합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            # 있는지 확인
            c.execute("SELECT id FROM autorole WHERE server_id = ? AND role_id = ?", (server_id, role_id))
            row = c.fetchone()
            if not row:
                return False, "autorole_not_found", None
            # 제거
            c.execute("DELETE FROM autorole WHERE server_id = ? AND role_id = ?", (server_id, role_id))
            return True, "success", None
        except Exception as e:
            self.logger.error(f"Failed to remove autorole: {e}")
            return False, str(e), None

    def get_autorole(self, server_id: int) -> List[Dict[str, Any]]:
        """서버의 자동 역할 설정들을 조회합니다."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM autorole WHERE server_id = ?", (server_id,))
            rows = c.fetchall()
            autoroles = []
            for row in rows:
                autoroles.append({
                    "server_id": row[1],
                    "role_id": row[2],
                    "bot_user": row[3]
                })
            return autoroles
        except Exception as e:
            self.logger.error(f"Failed to get autoroles: {e}")
            return []


# 전역 데이터베이스 서비스 인스턴스
db_service = DatabaseService()


# 하위 호환성을 위한 함수들 (기존 코드와의 호환성 유지)
def init_db():
    """레거시 호환성을 위한 함수"""
    pass  # 이미 DatabaseService.__init__에서 처리됨


def add_mention_delay_user(user_id: int, sender_id: int, content: str, done: int, server_id: int, send_type: str):
    return db_service.add_mention_delay_user(user_id, sender_id, content, done, server_id, send_type)


def process_mention_relation(related_id: list):
    return db_service.process_mention_relation(related_id)


def done_mention_delay_user(mention_id: int):
    return db_service.done_mention_delay_user(mention_id)


def cancel_mention_delay_user(mention_id: int, admin: bool, trigger_user: int, trigger_server: int):
    return db_service.cancel_mention_delay_user(mention_id, admin, trigger_user, trigger_server)


def get_mention_delay_user(user_id: int, type: str = "all", server_id: int = None):
    return db_service.get_mention_delay_user(user_id, type, server_id)


def reset_gpt_chat_thread(user_id: int):
    return db_service.reset_gpt_chat_thread(user_id)


def update_gpt_chat_thread(user_id: int, thread_id: int):
    return db_service.update_gpt_chat_thread(user_id, thread_id)


def get_gpt_chat_thread(user_id: int):
    return db_service.get_gpt_chat_thread(user_id)


def get_all_xp_setting():
    return db_service.get_all_xp_setting()


def update_xp_setting(server_id: int, onoff: bool, chat_xp: int, chat_xp_cooldown: int, voice_xp: int, voice_xp_cooldown: int, unit: str):
    return db_service.update_xp_setting(server_id, onoff, chat_xp, chat_xp_cooldown, voice_xp, voice_xp_cooldown, unit)


def get_xp_setting_dict(server_id: int):
    return db_service.get_xp_setting_dict(server_id)


def get_xp_setting(server_id: int):
    return db_service.get_xp_setting(server_id)


def update_xp(server_id: int, user_id: int, xp: int):
    return db_service.update_xp(server_id, user_id, xp)


def get_all_xp(server_id: int):
    return db_service.get_all_xp(server_id)


def get_xp(server_id: int, user_id: int):
    return db_service.get_xp(server_id, user_id)


def update_user_join_route(user_id: int, join_route: str):
    return db_service.update_user_join_route(user_id, join_route)


def get_user_join_route(user_id: int):
    return db_service.get_user_join_route(user_id)


def update_mention_delay_block(blocker_id: int, blocked_id: int, blocked: bool):
    return db_service.update_mention_delay_block(blocker_id, blocked_id, blocked)


def get_mention_delay_block(blocker_id: int, blocked_id: int):
    return db_service.get_mention_delay_block(blocker_id, blocked_id)


def update_quarantine_role(server_id: int, quarantine_role: int):
    return db_service.update_quarantine_role(server_id, quarantine_role)


def get_quarantine_role(server_id: int):
    return db_service.get_quarantine_role(server_id)


def add_autorole(server_id: int, role_id: int, bot_user: str):
    return db_service.add_autorole(server_id, role_id, bot_user)


def remove_autorole(server_id: int, role_id: int):
    return db_service.remove_autorole(server_id, role_id)


def get_autorole(server_id: int):
    return db_service.get_autorole(server_id)