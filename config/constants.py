"""
GarlicBot Constants Configuration

This module contains all constant values used throughout the bot.
"""

from typing import Dict, List
import pytz


class Constants:
    """Constants configuration class"""
    
    def __init__(self):
        self._load_permission_mappings()
        self._load_automod_settings()
        self._load_shop_items()
        self._load_type_mappings()
        self._load_warning_messages()
    
    def _load_permission_mappings(self):
        """권한 매핑 설정"""
        self.PERMISSION_MAP = {
            "create_instant_invite": "초대 링크 생성하기",
            "kick_members": "멤버 추방하기", 
            "ban_members": "멤버 차단하기",
            "administrator": "관리자",
            "manage_channels": "채널 관리하기",
            "manage_guild": "서버 관리하기",
            "add_reactions": "반응 추가하기",
            "view_audit_log": "감사 로그 보기",
            "priority_speaker": "발언 우선권",
            "stream": "stream",
            "view_channel": "채널 보기", 
            "send_messages": "메시지 보내기",
            "send_tts_messages": "텍스트 음성 변환 메시지 전송",
            "manage_messages": "메시지 삭제/고정",
            "embed_links": "링크 첨부",
            "attach_files": "파일 첨부",
            "read_message_history": "메시지 기록 보기",
            "mention_everyone": "`@everyone`, `@here`, 모든 역할 멘션",
            "use_external_emojis": "외부 이모지 사용",
            "view_guild_insights": "서버 인사이트 보기",
            "connect": "연결",
            "speak": "말하기",
            "mute_members": "멤버들의 마이크 음소거하기",
            "deafen_members": "deafen members",
            "move_members": "멤버 이동하기",
            "use_vad": "use vad",
            "change_nickname": "별명 변경하기",
            "manage_nicknames": "별명 관리하기",
            "manage_roles": "역할 관리하기",
            "manage_webhooks": "웹후크 관리하기",
            "manage_guild_expressions": "표현 관리하기",
            "use_application_commands": "애플리케이션 명령어 사용",
            "request_to_speak": "발언권 요청",
            "manage_events": "이벤트 관리하기",
            "manage_threads": "스레드 관리하기",
            "create_public_threads": "공개 스레드 만들기",
            "create_private_threads": "비공개 스레드 만들기",
            "use_external_stickers": "외부 스티커 사용",
            "send_messages_in_threads": "스레드에서 메시지 보내기",
            "use_embedded_activities": "use embedded activites",
            "moderate_members": "타임아웃 멤버",
            "view_creator_monetization_analytics": "view creator monetization analytics",
            "use_soundboard": "사운드보드 사용",
            "create_guild_expressions": "표현 생성하기",
            "create_events": "이벤트 생성하기",
            "use_external_sounds": "use external sounds",
            "send_voice_messages": "음성 메시지 보내기",
            "send_polls": "투표 만들기",
            "use_external_apps": "외부 앱 사용",
        }
    
    def _load_automod_settings(self):
        """자동 조치 관련 설정"""
        # 조치 사유
        self.AUTOMOD_REASONS = {
            "POLITICS": "정치 관련 대화",
            "INAPPROPRIATE": "부적절한 표현 사용", 
            "SCAM_SPAM": "사기 또는 스팸으로 의심되는 활동",
            "ABNORMAL_MENTION": "비정상적인 방법으로 멘션 시도",
            "SEXUAL": "성적인 발언",
            "MENTION_ATTEMPT": "멘션 시도",
            "UNPLEASANT": "불쾌한 언급 (서버 주인이 불쾌하다고 언급했었음)",
            "REGIONAL_DISCRIMINATION": "지역 차별적인 발언",
            "FAMILY_INSULT": "패드립",
            "WIKI_RELATED": "위키 관련 대화",
            "SPAM_ACTIVITY": "스팸으로 의심되는 활동"
        }
        
        # 키워드 목록들
        self.AUTOMOD_KEYWORDS = {
            "POLITICS": [
                "자민당", "박원순", "자유민주당", "일본제국", "조선족", "리선족",
                "광주는폭동", "야기분좋다", "부끄러운줄알아야지", "운지", "부엉이바위",
                "괴벨스", "힘러", "사회주의", "스탈린", "레닌", "푸틴", "김정은",
                "김정일", "김일성", "트럼프", "도람푸", "바이든", "무솔리니",
                "파시스트", "국가사회주의", "공산당", "마오쩌둥", "시진핑", "모택동",
                "습근평", "푸른드럼통", "계양의드럼통", "드럼통", "사과박스", "박카스박스",
                "윤핵관", "스탈린그라드", "썩열이", "썩열이형", "국K사단", "국회",
                "계엄", "비상계엄", "긴급계엄", "계엄군", "부정선거", "구케의원",
                "국케위원", "체육관선거", "유신헌법", "티엔안먼", "Tiananmen", "tiananmen",
                "안철수", "낫과망치", "낫과 망치", "낫치", "nomu", "천안문", "톈안문",
                "텐안문", "톈안먼", "천안먼", "텐안먼", "이동환", "절라도", "이기야",
                "이기이기", "부엉이절벽", "일베", "공화당", "일간베스트", "일베충",
                "일베새끼", "북괴", "빨갱이", "북조선", "조선민주주의인민공화국",
                "부엉이 절벽", "국가재건", "히틀러", "홍준표", "노운지", "윤통",
                "주사파", "종북", "김종필", "자유당", "자유선진당", "지역정당",
                "신한국당", "한국당", "자유한국당", "한나라당", "새누리당", "정의당",
                "이시영", "석열이", "재명이", "1찍", "이명박", "전두환", "최상목",
                "한덕수", "최규하", "윤보선", "박정희", "한동훈", "노태우", "김영삼",
                "김대중", "박통", "이회창", "온갖음해", "온갖 음해", "국힘", "민주당",
                "국민의 힘", "국민의힘", "문재인", "이재명", "박근혜", "노무노무",
                "노무현", "노무", "MC무현", "MC 무현", "찢재명", "문재앙", "윤석열",
                "김건희", "서울의 봄", "서울의봄", "운지나", "운지하세요", "운지해",
                "부엉이바위", "부엉이 바위", "이승만", "응디", "우흥", "노알라",
                "좌파", "우파", "2찍", "빨간당", "파란당", "무현"
            ],
            "INAPPROPRIATE": ["정좆", "jeongjot"],
            "SCAM_SPAM": ["50$ for steam", "$ for steam", "nude", "steamcommunity.com/gift"],
            "ABNORMAL_MENTION": [
                "!번역 @모든사람", "!번역 @모든 사람", "!번역 @여기", "@모든사람",
                "@여기", "@이곳", "!번역 @모두"
            ],
            "SEXUAL": [
                "따먹", "쇼타", "로리", "촉수", "창녀", "오고곳", "통구이", "전라디언",
                "쟈지", "보지구멍", "씹구녕", "찌찌", "으럇으럇", "자지푸딩", "쟈지푸딩",
                "섹스", "부랄", "헤으응", "해으응", "헤응", "헤으읏", "하응", "하으응",
                "색스", "SEX", "sex", "Sex", "SEx", "sEX", "seX", "sEx", "불알",
                "강간", "응기잇", "오고곡", "응긱", "응깃", "야스", "YAS", "응긋",
                "가버렷", "빠구리"
            ],
            "MENTION_ATTEMPT": ["@everyone", "@here", "<@&"],
            "REGIONAL_DISCRIMINATION": ["통구이", "쥐포", "홍어색"],
            "FAMILY_INSULT": ["니애미", "니기미", "니애비", "ㄴㄱㅁ", "느금마", "ㄴㅇㅁ"],
            "SPAM_ACTIVITY": [
                "https://temu.com/s/L5KUJI0PgTBAw", "temu.com/s/", "lite.tiktok.com"
            ]
        }
        
        # 개인정보 키워드
        self.PERSONAL_INFO_KEYWORDS = [
            "생년월일", "생일", "나이", "실명", "본명", "이름", "학교", "거주지"
        ]
    
    def _load_shop_items(self):
        """경험치 상점 아이템"""
        self.EXP_SHOP = [
            {
                "item": "파일 첨부 권한",
                "description": "파일 첨부를 위해 구입해야 하는 권한입니다.",
                "price": 5000,
                "role": 1333390128072232980
            },
            {
                "item": "투표 생성 권한",
                "description": "투표 생성을 위해 구입해야 하는 권한입니다.",
                "price": 7000,
                "role": 1320315949005537310
            },
            {
                "item": "비공개 스레드 생성 권한",
                "description": "비공개 스레드 생성을 위해 구입해야 하는 권한입니다.",
                "price": 7000,
                "role": 1320600850082693172
            },
            {
                "item": "마늘이 답변 추가권",
                "description": "`마늘아 <할 말>`에 대한 답변을 추가해주는 상품입니다. " +
                            "<#1327116951805493279>에서 자세히 알아보세요.",
                "price": 30000,
                "role": 0
            },
            {
                "item": "경고 차감권", 
                "description": "경고 1개를 차감해주는 상품입니다. " +
                            "<#1327116951805493279>에서 자세히 알아보세요.",
                "price": 50000,
                "role": 0
            },
            {
                "item": "메시지 고정권",
                "description": "채팅 채널에 특정 메시지를 고정해주는 상품입니다. " +
                            "<#1327116951805493279>에서 자세히 알아보세요.",
                "price": 100000,
                "role": 0
            }
        ]
    
    def _load_type_mappings(self):
        """타입 매핑"""
        self.TYPE_MAPPING = {
            "warn": "경고",
            "unwarn": "경고 차감",
            "timeout": "타임아웃",
            "untimeout": "타임아웃 해제",
            "kick": "추방",
            "ban": "차단",
            "unban": "차단 해제"
        }
    
    def _load_warning_messages(self):
        """경고 메시지"""
        self.WARN_LAW = (
            "**[경고!]** 본 자료는 법적 조언이 아닌 일반적인 정보 제공 목적만을 가지고 있습니다. "
            "특정 상황에 대해 결정하시기 전, 반드시 법률 전문가와 상의하시기 바랍니다. "
            "본 자료를 신뢰하여 생기는 손해나 피해에 대한 책임은 사용자의 판단에 따라 "
            "전적으로 사용자에게 있습니다."
        )
        
        self.WARN_SECRET = (
            "**[경고!]** 이 문서에는 기밀 정보가 포함되어 있습니다. "
            "다른 사람(사용자)에게 유출되지 않도록 주의가 필요합니다."
        )

    def _load_weather_data(self):
        """날씨 관련 상수"""
        # 지역 좌표 데이터
        self.REGION_COORDS = {
            '서울': {'lat': 37.5665, 'lon': 126.9780},
            '부산': {'lat': 35.1796, 'lon': 129.0756},
            '대구': {'lat': 35.8714, 'lon': 128.6014},
            '인천': {'lat': 37.4563, 'lon': 126.7052},
            '광주': {'lat': 35.1595, 'lon': 126.8526},
            '제주': {'lat': 33.4996, 'lon': 126.5312},
            '백령도': {'lat': 37.9796, 'lon': 124.6276},
            '춘천': {'lat': 37.8800, 'lon': 127.7253},
            '수원': {'lat': 37.2636, 'lon': 127.0286},
            '천안': {'lat': 36.8151, 'lon': 127.1139},
            '청주': {'lat': 36.6359, 'lon': 127.4912},
            '강릉': {'lat': 37.7513, 'lon': 128.8760},
            '전주': {'lat': 35.8205, 'lon': 127.1509},
            '대전': {'lat': 36.3504, 'lon': 127.3845},
            '안동': {'lat': 36.5662, 'lon': 128.7201},
            '울릉도/독도': {'lat': 37.4138, 'lon': 131.8694},
            '목포': {'lat': 34.8128, 'lon': 126.3917},
            '여수': {'lat': 34.7608, 'lon': 127.6622},
            '울산': {'lat': 35.5384, 'lon': 129.3114},
            '익산': {'lat': 35.9402, 'lon': 126.9463},
        }

        # 날씨 이모지 매핑
        self.WEATHER_EMOJIS = {
            "맑음": "☀️",
            "구름": "⛅",
            "비": "🌧️",
            "눈": "❄️",
            "천둥": "⛈️",
        }

    def _load_server_config(self):
        """서버 설정 상수"""
        # 서버별 설정 (define.py에서 가져옴)
        self.USING_SERVER = 1320303102703702037  # 메인 서버 ID
        self.RECORD_CHANNEL = 1320304892992028785  # 제재 내역 채널 ID
        self.MESSAGE_LOG = 1394228444673605754  # 메시지 로그 채널 ID
        
        # 시간대 설정
        self.KST = pytz.timezone('Asia/Seoul')


# 글로벌 상수 인스턴스
constants = Constants()