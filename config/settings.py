"""
GarlicBot Settings Configuration

This module contains all configuration settings for the GarlicBot.
All hardcoded values from main.py are centralized here.
"""

import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()


class Settings:
    """Main settings configuration class"""
    
    def __init__(self):
        self._load_environment_variables()
        self._load_channel_settings()
        self._load_role_settings()
        self._load_user_settings()
        self._load_feature_settings()
        self._load_api_settings()
        self._load_file_settings()
    
    def _load_environment_variables(self):
        """환경변수 로드"""
        # API Keys
        self.WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
        self.GEMENI_API_KEY = os.getenv("GEMENI_API_KEY")
        self.EMAIL = os.getenv("EMAIL")
        self.PASSWORD = os.getenv("PASSWORD")
        self.TRAIN_TIMETABLE_API = os.getenv("train_timetable_api")
        self.TRAIN_ARRIVALS_API = os.getenv("train_arrivals_api")
        
        # Discord Bot Token
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    
    def _load_channel_settings(self):
        """채널 ID 설정"""
        # 주요 채널
        self.TICKET_CHANNEL_ID = 1325041620084850708
        self.NORMAL_CHANNEL_ID = 1320303102703702042
        self.GREETING_CHANNEL_ID = 1325008603425280010
        self.BYEBYE_CHANNEL_ID = 1325008603425280010
        self.GET_EXP_NOTIFY_CHANNEL_ID = 1342040521299984435
        
        # 로그 채널
        self.LOG_CHANNEL_ID = 1394228444673605754
        self.ANONYMOUS_LOG_CHANNEL_ID = 1340681195058364509
        self.AUTOMOD_LOG_CHANNEL_ID = 1316575398607327282
        self.XP_LOG_CHANNEL_ID = 1325006023064293417
        self.OWNER_NOTIFY_CHANNEL_ID = 1329296309164834897
        
        # 로그 제외 채널 목록
        self.NO_LOG_CHANNELS = [
            1389207728731328532, 1386969642177794048, 1381920954309148723,
            1370303621018681414, 1368036520610500638, 1367046339845820426,
            1360922829268455464, 1320978400508379176, 1328988763136983040,
            1329296309164834897, 1337798090454995077, 1339463794526785607,
            1344487509782036632, 1347108350671978577, 1360239547270697000
        ]
        
        # 포럼 채널
        self.FORUM_CHANNEL_ID = 0
    
    def _load_role_settings(self):
        """역할 ID 설정"""
        # 기본 역할
        self.VERIFY_ROLE_ID = 1320303229954953247
        self.TRUST_ROLE_ID = 1316575227253100654
        self.ROLE_ID_TO_REMOVE = 1320303229954953247
        
        # 관리 역할
        self.OWNER_ID = 1320308043350675497
        self.SUPER_ADMIN_ROLE_ID = 1325762715867943004
        self.ADMIN_ROLE_ID = 1320303818004496430
        self.SERVER_BOOSTER_ROLE_ID = 1326166759778029600
        
        # 특수 역할
        self.EMAIL_ROLE_ID = [1320308502723563560]
        
        # 멘션 허용 역할
        self.DO_MENTION_ROLES = [
            1378253467940028498, 1375687128708677682, 1378256091070074900,
            1400872501378158764, 1416704481382502470, 1418480822255616053,
            1418481318806683678, 1418480277155614781, 1418481446380765289,
            1418481595945586709, 1418481673909043210, 1418481752015503360,
            1418481816276439163
        ]
        
        # 도배 방지 화이트리스트 역할
        self.SPAMMING_FILTER_WHITELIST = [1325846757636047030, 1329825168435970100]
        
        # 안티 누크 화이트리스트 역할
        self.ANTI_NUKE_WHITELIST = [1331147542536126515]
    
    def _load_user_settings(self):
        """사용자 ID 설정"""
        # 특별 멘션 경고 제외 사용자
        self.MANUAL_MENTION_NO_WARN = [
            1367416348048621568, 1389857898745823334, 1355698620606709902,
            1139867278486274110, 1076065874596864041, 1306030639677444197,
            1305492487137267722, 1359149837081116863, 1204425981033451613,
            717241733011996682, 351743982474362910, 823346807350231060,
            1072311823212228748, 644432352457523200, 920629772684505108,
            1063676895000018944, 873128084193296406, 1326817332592513045,
            1137207376869609513, 1312760049105506376, 1181084142969032848,
            1266655535696969758
        ]
        
        # 소유자
        self.OWNERS = [1305492487137267722]
        
        # 최고 관리자
        self.SUPER_ADMINS = [
            1063676895000018944, 1305492487137267722, 1181084142969032848,
            717241733011996682, 1342044882080108564
        ]
        
        # 관리자
        self.ADMINS = [
            1137207376869609513, 823346807350231060, 1326817332592513045,
            1076065874596864041, 1063676895000018944, 1305492487137267722,
            1181084142969032848, 717241733011996682, 1342044882080108564
        ]
        
        # 친한 사용자 목록
        self.FRIENDLY_LIST = [
            1355698620606709902, 1305492487137267722, 873128084193296406,
            1238750780459188225, 1350460211739103305, 1063676895000018944
        ]
        
        # 자동 인증 제외
        self.NO_AUTO_VERIFY = [
            1360093367463055411, 1343462321044979815, 1142740632314597467,
            1207080506328485976, 1345697924847505429, 1297882025121812502,
            1341739833499979846, 1325010425376538697
        ]
    
    def _load_feature_settings(self):
        """기능 설정"""
        # 기본 설정
        self.AUTO_VERIFY = True
        self.RESPONDING = False
        
        # 검색 및 메시지 설정
        self.MESSAGE_CHECK_INTERVAL = 5  # seconds
        self.MESSAGE_TRACKER_MAX_LEN = 20
        self.BAN_NUKE_COUNT = 3
        
        # 경험치 설정
        self.EXP_GAIN = 100
        self.EXP_COOLDOWN = 60  # seconds
        self.PAGE_SIZE = 20  # 경험치 순위 페이지네이션
        
        # 호출 제한
        self.MAX_CALLS_PER_DAY = 50
        
        # 쿨다운 시간
        self.COOLDOWN_TIME = 60  # 1 minute
        
        # 이메일 설정
        self.EMAIL_ROLE_LIMIT = True
        
        # 메시지 개수
        self.MESSAGE_COUNT = 0
        self.MAIN_CHANNEL_ID = 1320303102703702042
    
    def _load_api_settings(self):
        """API 관련 설정"""
        # IMAP 서버 설정
        self.IMAP_SERVER = 'imap.gmail.com'
        
        # Gemini API URL
        self.GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={self.GEMENI_API_KEY}"
    
    def _load_file_settings(self):
        """파일 경로 설정"""
        # 백업 폴더
        self.BACKUP_FOLDER = "backups"
        
        # JSON 파일들
        self.WARNINGS_FILE = "warnings.json"
        self.LIKEABILITY_FILE = "likeability.json"
        self.EXP_FILE = "exp.json"
        self.MENTION_FILE = "mentions.json"
        
        # 텍스트 파일들
        self.BLOCKLIST_FILE = "block.txt"
        self.DENIAL_LIST_FILE = 'soMyungGeoBuList.txt'
        self.SECRET_FILE_NAME = "기밀메시지.txt"
        self.AUTO_VERIFY_FILE = "auto_verify.txt"
        self.DELETING_KEYWORD_FILE = 'keywords.txt'
        
        # 엑셀 파일들
        self.SUBWAY_LIST_FILE = 'subway_list.xlsx'
        self.TRANSFER_INFO_FILES = [
            '서교공_환승정보.xlsx',
            '서교공_환승정보2.xlsx',
            '코레일_환승정보.xlsx'
        ]
        self.TRANSFER_INFO_CSV = '환승정보.csv'


# 글로벌 설정 인스턴스
settings = Settings()