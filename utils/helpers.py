"""
GarlicBot Helper Functions

공통으로 사용되는 유틸리티 함수들을 모아놓은 모듈입니다.
"""

import discord
from datetime import datetime, timedelta
from typing import Optional, Union, List
import re
import json
import os
from typing import Dict, Any

from .constants import BLOCKED_USERS_FILE


def format_duration(duration: Union[timedelta, int]) -> str:
    """
    시간 간격을 한국어 문자열로 포맷팅합니다.
    
    Args:
        duration: timedelta 객체 또는 초 단위 정수
    
    Returns:
        "1일 2시간 30분 45초" 형태의 한국어 문자열
    """
    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds()) + 2
    else:
        total_seconds = int(duration) + 2
    
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # 시간 형식 문자열 생성
    duration_parts = []
    
    # 24시간 이상인 경우에만 일수 표시
    if total_seconds >= 24 * 3600:
        duration_parts.append(f"{days}일")
        
    # 1시간 이상인 경우에만 시간 표시
    if total_seconds >= 3600:
        duration_parts.append(f"{hours}시간")
        
    # 1분 이상인 경우에만 분 표시
    if total_seconds >= 60:
        # 초 단위가 0이 아닐 때만 분 표시
        if seconds != 0 or minutes != 0:
            duration_parts.append(f"{minutes}분")
            
    # 초가 0이 아닐 때만 초 표시
    if seconds != 0:
        duration_parts.append(f"{seconds}초")
        
    return " ".join(duration_parts) if duration_parts else "0초"


def get_message_link(message: discord.Message) -> str:
    """
    Discord 메시지의 링크를 생성합니다.
    
    Args:
        message: Discord 메시지 객체
    
    Returns:
        메시지 링크 URL
    """
    return f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"


def print_time(seconds: int) -> str:
    """
    초 단위 시간을 읽기 쉬운 형태로 변환합니다.
    
    Args:
        seconds: 초 단위 시간
    
    Returns:
        "1일 2시간 30분 45초" 형태의 문자열
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")
    if secs > 0:
        parts.append(f"{secs}초")
    
    return " ".join(parts) if parts else "0초"


def is_spam(message: discord.Message) -> bool:
    """
    메시지가 스팸인지 간단히 판단합니다.
    
    Args:
        message: 검사할 Discord 메시지
    
    Returns:
        스팸이면 True, 아니면 False
    """
    content = message.content.lower()
    
    # 기본적인 스팸 패턴들
    spam_patterns = [
        r'(.)\1{10,}',  # 같은 문자 11개 이상 반복
        r'@everyone|@here',  # everyone/here 멘션
        r'discord\.gg/|discord\.com/invite/',  # 초대 링크
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URL (단순 검사)
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, content):
            return True
    
    # 메시지 길이 검사 (너무 길면 스팸으로 간주)
    if len(content) > 2000:
        return True
    
    return False


def truncate_text(text: str, max_length: int = 2000) -> str:
    """
    텍스트를 지정된 길이로 자릅니다.
    
    Args:
        text: 자를 텍스트
        max_length: 최대 길이
    
    Returns:
        잘린 텍스트
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def safe_mention(user_id: int) -> str:
    """
    안전한 사용자 멘션을 생성합니다.
    
    Args:
        user_id: 사용자 ID
    
    Returns:
        멘션 문자열
    """
    return f"<@{user_id}>"


def format_timestamp(dt: datetime, style: str = "f") -> str:
    """
    Discord 타임스탬프 포맷으로 변환합니다.
    
    Args:
        dt: datetime 객체
        style: 타임스탬프 스타일 (f, F, d, D, t, T, R)
    
    Returns:
        Discord 타임스탬프 문자열
    """
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:{style}>"


def get_korean_weekday(dt: datetime) -> str:
    """
    요일을 한국어로 반환합니다.
    
    Args:
        dt: datetime 객체
    
    Returns:
        한국어 요일
    """
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return weekdays[dt.weekday()]


def parse_time_string(time_str: str) -> Optional[datetime]:
    """
    다양한 형태의 시간 문자열을 파싱합니다.
    
    Args:
        time_str: 시간 문자열
    
    Returns:
        파싱된 datetime 객체 또는 None
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%m/%d %H:%M",
        "%H:%M:%S",
        "%H:%M"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    return None


def calculate_level_from_exp(exp: int) -> int:
    """
    경험치로부터 레벨을 계산합니다.
    
    Args:
        exp: 경험치
    
    Returns:
        레벨
    """
    # 기존 return_level 함수 로직 사용
    if exp >= 500000: return 33
    elif exp >= 350000: return 32
    elif exp >= 270000: return 31
    elif exp >= 220000: return 30
    elif exp >= 180000: return 29
    elif exp >= 150000: return 28
    elif exp >= 127000: return 27
    elif exp >= 109000: return 26
    elif exp >= 93000: return 25
    elif exp >= 79000: return 24
    elif exp >= 67000: return 23
    elif exp >= 57000: return 22
    elif exp >= 48000: return 21
    elif exp >= 40000: return 20
    elif exp >= 33000: return 19
    elif exp >= 27000: return 18
    elif exp >= 22000: return 17
    elif exp >= 18700: return 16
    elif exp >= 15700: return 15
    elif exp >= 13000: return 14
    elif exp >= 10500: return 13
    elif exp >= 8200: return 12
    elif exp >= 6500: return 11
    elif exp >= 5000: return 10
    elif exp >= 3700: return 9
    elif exp >= 2700: return 8
    elif exp >= 2000: return 7
    elif exp >= 1500: return 6
    elif exp >= 1000: return 5
    elif exp >= 500: return 4
    elif exp >= 300: return 3
    elif exp >= 150: return 2
    else: return 1


def sanitize_filename(filename: str) -> str:
    """
    파일명에서 안전하지 않은 문자를 제거합니다.
    
    Args:
        filename: 원본 파일명
    
    Returns:
        안전한 파일명
    """
    # 윈도우/리눅스에서 금지된 문자들
    invalid_chars = r'<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 윈도우 예약어 처리
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
    if filename.upper() in reserved_names:
        filename = f"_{filename}"
    
    return filename.strip('. ')


def chunk_text(text: str, max_length: int = 2000) -> List[str]:
    """
    긴 텍스트를 여러 청크로 나눕니다.
    
    Args:
        text: 나눌 텍스트
        max_length: 각 청크의 최대 길이
    
    Returns:
        텍스트 청크 리스트
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # 줄바꿈으로 나누어 처리
    lines = text.split('\n')
    
    for line in lines:
        # 현재 청크에 줄을 추가했을 때 길이 확인
        if len(current_chunk + line + '\n') <= max_length:
            current_chunk += line + '\n'
        else:
            # 현재 청크가 비어있지 않으면 저장
            if current_chunk:
                chunks.append(current_chunk.rstrip('\n'))
                current_chunk = ""
            
            # 줄 자체가 max_length보다 길면 강제로 자름
            if len(line) > max_length:
                while line:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
            else:
                current_chunk = line + '\n'
    
    # 마지막 청크 추가
    if current_chunk:
        chunks.append(current_chunk.rstrip('\n'))
    
    return chunks


def format_number(number: int) -> str:
    """
    숫자를 천 단위 쉼표가 있는 문자열로 포맷팅합니다.
    
    Args:
        number: 포맷팅할 숫자
    
    Returns:
        포맷팅된 문자열
    """
    return f"{number:,}"


def get_color_from_string(text: str) -> discord.Color:
    """
    문자열에서 일관된 색상을 생성합니다.
    
    Args:
        text: 색상을 생성할 문자열
    
    Returns:
        Discord Color 객체
    """
    # 문자열의 해시값을 이용해 색상 생성
    hash_value = hash(text) % 16777215  # 24비트 색상 범위
    return discord.Color(hash_value)


# ===== define.py에서 마이그레이션된 함수들 =====


def load_blocked_users2() -> Dict[str, Any]:
    """JSON 파일에서 차단된 사용자 정보를 불러오는 함수"""
    if not os.path.exists(BLOCKED_USERS_FILE):
        return {}
    with open(BLOCKED_USERS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # 파일 내용이 올바르지 않을 경우 빈 딕셔너리 반환
            data = {}
    return data


def save_blocked_users2(data: Dict[str, Any]) -> None:
    """JSON 파일에 차단된 사용자 정보를 저장하는 함수"""
    with open(BLOCKED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def is_blocked(user: discord.User) -> List[Union[bool, Optional[str], Optional[str]]]:
    """사용자가 차단되었는지 확인하는 함수

    Returns:
        [차단여부, 차단만료일, 차단사유]
    """
    data = load_blocked_users2()
    user_id = str(user.id)  # JSON 키로 사용하기 위해 문자열로 변환
    if user_id not in data:
        # 차단 정보가 없는 경우
        return [False, None, None]

    blocked_info = data[user_id]
    # "until" 필드의 날짜를 datetime 객체로 변환
    try:
        blocked_until = datetime.strptime(blocked_info.get("until", ""), "%Y-%m-%d").date()
    except ValueError:
        # 날짜 형식이 올바르지 않으면 차단 해제된 것으로 간주
        return [False, None, None]

    today = datetime.today().date()
    if today > blocked_until:
        # 차단 기간이 끝난 경우
        return [False, None, None]

    # 차단 기간이 아직 남아있는 경우
    return [True, blocked_info.get("until"), blocked_info.get("reason")]


def is_valid_time(time_str: str) -> bool:
    """시간 문자열이 유효한지 확인하는 함수"""
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


async def check_message(message, check_everyone_here_mention: bool = True,
                       check_role_mention: bool = True, check_user_mention: bool = True,
                       check_invite_link: bool = True) -> Dict[str, Any]:
    """봇이 메시지를 보내기 전에 보안 검사를 수행하는 함수

    Args:
        message: 보내려는 메시지 (str 또는 Embed 객체)
        check_everyone_here_mention: @everyone, @here 멘션 검사 여부
        check_role_mention: 역할 멘션 검사 여부
        check_user_mention: 사용자 멘션 검사 여부
        check_invite_link: 초대 링크 검사 여부

    Returns:
        보안 검사 결과 딕셔너리
    """
    from discord import Embed

    # 기본 반환값 구조
    result = {
        "original_message": message,
        "modified_message": message,
        "warnings": [],
        "blocked": False,
        "reason": None
    }

    # 메시지가 Embed인 경우 처리
    if isinstance(message, Embed):
        # Embed의 description, title, fields 등에서 위험 요소 검사
        embed_text = ""
        if message.title:
            embed_text += message.title + " "
        if message.description:
            embed_text += message.description + " "
        if message.fields:
            for field in message.fields:
                embed_text += field.name + " " + field.value + " "

        message_content = embed_text
    else:
        message_content = str(message)

    # 각 검사 항목 수행
    modified_content = message_content

    # @everyone, @here 멘션 검사
    if check_everyone_here_mention:
        if "@everyone" in message_content or "@here" in message_content:
            result["warnings"].append("@everyone 또는 @here 멘션이 포함되어 있습니다")

    # 역할 멘션 검사
    if check_role_mention:
        role_mentions = re.findall(r'<@&(\d+)>', message_content)
        if role_mentions:
            result["warnings"].append(f"역할 멘션 {len(role_mentions)}개가 포함되어 있습니다")

    # 사용자 멘션 검사
    if check_user_mention:
        user_mentions = re.findall(r'<@!?(\d+)>', message_content)
        if user_mentions:
            result["warnings"].append(f"사용자 멘션 {len(user_mentions)}개가 포함되어 있습니다")

    # 초대 링크 검사
    if check_invite_link:
        invite_links = re.findall(r'discord\.gg/[a-zA-Z0-9]+', message_content)
        if invite_links:
            result["warnings"].append(f"Discord 초대 링크 {len(invite_links)}개가 포함되어 있습니다")

    # 위험도가 높은 경우 차단
    if len(result["warnings"]) > 3:  # 임의의 임계값
        result["blocked"] = True
        result["reason"] = "너무 많은 위험 요소가 포함되어 있습니다"

    return result


def create_error_embed(title: str, description: str, color: discord.Color = discord.Color.red()) -> discord.Embed:
    """에러 임베드를 생성하는 함수"""
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


def create_success_embed(title: str, description: str, color: discord.Color = discord.Color.green()) -> discord.Embed:
    """성공 임베드를 생성하는 함수"""
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


def create_info_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """정보 임베드를 생성하는 함수"""
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


def has_permission(user: Union[discord.Member, discord.User], permission: str, guild: discord.Guild = None) -> bool:
    """사용자가 특정 권한을 가지고 있는지 확인하는 함수"""
    if isinstance(user, discord.User) and not isinstance(user, discord.Member):
        # User 객체인 경우 (DM 등)
        return False

    member = user  # Member 객체
    perm_map = {
        'administrator': 'administrator',
        'manage_roles': 'manage_roles',
        'manage_channels': 'manage_channels',
        'kick_members': 'kick_members',
        'ban_members': 'ban_members',
        'manage_messages': 'manage_messages',
        'view_audit_log': 'view_audit_log'
    }

    if permission in perm_map:
        return getattr(member.guild_permissions, perm_map[permission], False)

    return False


def get_user_display_name(user: Union[discord.Member, discord.User]) -> str:
    """사용자의 표시 이름을 반환하는 함수"""
    if isinstance(user, discord.Member):
        return user.display_name
    return user.name


def format_user_mention(user: Union[discord.Member, discord.User]) -> str:
    """사용자를 멘션할 수 있는 문자열을 반환하는 함수"""
    return f"<@{user.id}>"


def format_role_mention(role: discord.Role) -> str:
    """역할을 멘션할 수 있는 문자열을 반환하는 함수"""
    return f"<@&{role.id}>"


def format_channel_mention(channel: discord.abc.GuildChannel) -> str:
    """채널을 멘션할 수 있는 문자열을 반환하는 함수"""
    return f"<#{channel.id}>"