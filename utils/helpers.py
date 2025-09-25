"""
GarlicBot Helper Functions

공통으로 사용되는 유틸리티 함수들을 모아놓은 모듈입니다.
"""

import discord
from datetime import datetime, timedelta
from typing import Optional, Union, List
import re


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


def is_valid_time(time_str: str) -> bool:
    """
    시간 문자열이 올바른 형식인지 확인합니다.
    
    Args:
        time_str: 확인할 시간 문자열
    
    Returns:
        올바른 형식이면 True, 아니면 False
    """
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
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