# 경고

본 프로젝트의 저작권은 garlicfood1234에게 있습니다.  
무단 복제, 수정, 배포, 사용을 금지합니다.  
작성자의 명시적 허가 없이 본 코드 또는 저장소의 일부를 사용하는 것은 금지됩니다.

Copyright (c) 2025 garlicfood1234  
All rights reserved.  
Unauthorized copying, modification, distribution, or use of this code or any part of this repository is strictly prohibited without explicit permission from the author.

# 마늘봇 소개

마늘봇으로 서버를 더 편하게 관리하고, 더 편하게 채팅해보세요.

자세한 사항은 [여기](https://asdfasdfqwer.notion.site/1aa4a653ce018010ba92e5741e6ac72a?source=copy_link)를 참고해 주세요.

## 아키텍처

마늘봇은 **모듈형 Cog 기반 아키텍처**를 사용하여 구축되었습니다.

### 구조

```
garlicbot/
├── main.py                 # 봇 시작점 및 Cog 로더 (133라인, 9600+ → 133라인 최적화)
├── commands_v2/           # 명령어 Cog 모듈들 (27개 파일 마이그레이션 완료)
│   ├── advice.py         # 조언 명령어
│   ├── ai.py             # AI 관련 명령어
│   ├── anti_raid.py      # 레이드 방지
│   ├── autorole.py       # 자동 역할 부여
│   ├── bulk_cancel.py    # 대량 취소
│   ├── chat_time.py      # 채팅 시간
│   ├── close_threads.py  # 스레드 닫기
│   ├── encode.py         # 암호화/복호화
│   ├── fuction_collect_message.py  # 메시지 수집
│   ├── invite_log_check.py # 초대 로그 확인
│   ├── manage_timeout.py # 타임아웃 관리
│   ├── mention_delay.py  # 멘션 지연
│   ├── moderation.py     # 관리 명령어 (slowmode 포함)
│   ├── phrase.py         # 구문 명령어
│   ├── ping.py           # 핑 명령어
│   ├── remove_all_roles.py # 모든 역할 제거
│   ├── return_level.py   # 레벨 반환
│   ├── roles.py          # 역할 관리
│   ├── rules.py          # 규칙 명령어
│   ├── security.py       # 보안 명령어
│   ├── server_info.py    # 서버 정보
│   ├── suggest_random.py # 랜덤 제안
│   ├── summarize.py      # 요약 명령어
│   ├── timestamp.py      # 시간 관련
│   ├── train.py          # 기차 정보
│   ├── turn_off.py       # 종료 명령어
│   ├── weather.py        # 날씨 명령어
│   └── xp.py             # 경험치 시스템
├── events/               # 이벤트 핸들러 Cog 모듈들
│   ├── guild.py          # 서버 이벤트
│   ├── member.py         # 멤버 이벤트
│   ├── message.py        # 메시지 이벤트
│   └── moderation.py     # 관리 이벤트
├── config/               # 설정 파일들
├── utils/                # 유틸리티 함수들
└── services/             # 외부 서비스 연동
```

## 개발자 가이드

### 새로운 Cog 추가

1. `commands_v2/` 또는 `events/` 디렉토리에 새 파일 생성
2. `commands.Cog`를 상속받는 클래스 생성
3. `main.py`의 `load_cogs()` 함수에 Cog 경로 추가
4. 봇 재시작

### 기존 Cog 수정

- 각 Cog는 독립적으로 수정 가능
- 변경 후 봇 재시작 필요
- 테스트 환경에서 충분히 검증 후 배포

## 라이선스

Copyright (c) 2025 garlicfood1234. All rights reserved.

Refactored by vientorepublic
