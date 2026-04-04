# 경고
본 프로젝트의 저작권은 garlicfood1234에게 있습니다.  
무단 복제, 수정, 배포, 사용을 금지합니다.  
작성자의 명시적 허가 없이 본 코드 또는 저장소의 일부를 사용하는 것은 금지됩니다.

Copyright (c) 2025 garlicfood1234  
All rights reserved.  
Unauthorized copying, modification, distribution, or use of this code or any part of this repository is strictly prohibited without explicit permission from the author.

예외적 사용 허가 조건: 위의 엄격한 금지 규정에도 불구하고, 다음의 모든 조건을 충족하는 경우에 한하여 예외적으로 본 코드의 사용을 허가합니다.

1.  사용 범위: 단 1곳의 디스코드 서버 내에서 봇을 구동할 목적으로만 사용할 수 있습니다.
    * 디스코드 개발자 포털을 통해 봇 계정을 구성할 때, 1곳의 서버 외에는 봇을 추가할 수 없도록 제한해야 합니다.
2.  수정 및 재배포 금지: 제공되는 코드를 수정 없이 있는 그대로(As-is) 사용해야 하며, 어떠한 형태로든 제3자에게 재배포할 수 없습니다.
3.  출처 표기 의무: 본 코드를 사용하여 구동되는 디스코드 봇 계정 프로필의 '내 소개(About Me)' 최상단에 아래 내용을 반드시 포함해야 합니다.
    * GitHub 저장소 링크: `https://github.com/garlicfood1234/garlicbot`
    * 개발자 정보: `마늘요리 (asdfasdf_123456789, 1305492487137267722)`
4.  책임 제한: 본 코드의 사용으로 인해 발생하는 모든 문제나 손해에 대한 책임은 사용자에게 있으며, 원작자(`garlicfood1234`)는 어떠한 법적 책임도 지지 않습니다.

Exceptional Permitted Use: Notwithstanding the above restrictions, use of this code is exceptionally permitted only if **all** of the following conditions are met:

1.  Scope of Use: Limited to running a bot on one single Discord server.
    * The bot must be configured through the Discord Developer Portal to restrict its installation to a single server only.
2.  No Modification & Redistribution: The code must be used "as-is" without any modifications. Redistribution to any third party is strictly prohibited.
3.  Attribution Requirement: The following information must be displayed at the very top of the "About Me" section of the Discord bot account profile:
    * GitHub Repository: `https://github.com/garlicfood1234/garlicbot`
    * Developer: `마늘요리 (asdfasdf_123456789, 1305492487137267722)`
4.  Disclaimer of Liability: The user assumes all responsibility for any issues or damages arising from the use of this code. The original author (`garlicfood1234`) shall not be held liable under any circumstances.

# 프로젝트 기여

본 프로젝트는 코드 개선 및 기능 추가를 위한 Pull Request를 진심으로 환영합니다.

위에서 명시한 '수정 금지' 조항에도 불구하고, 본 저장소에 기여하기 위한 목적의 코드 수정 및 테스트는 예외적으로 허용됩니다.

제출된 PR은 검토 후 메인 코드에 반영될 수 있으며, 반영된 코드의 저작권 역시 본 라이선스 정책을 따릅니다.

We sincerely welcome Pull Requests for code improvements and new features.

Notwithstanding the 'No Modification' clause mentioned above, code modification and testing are exceptionally permitted solely for the purpose of contributing to this repository.

Submitted PRs will be reviewed for potential integration into the main codebase. Once merged, the contributed code will also be governed by this license policy.

# 마늘봇 소개
마늘봇으로 서버를 더 편하게 관리하고, 더 편하게 채팅해보세요.

자세한 사항은 [여기](https://asdfasdfqwer.notion.site/1aa4a653ce018010ba92e5741e6ac72a?source=copy_link)를 참고해 주세요.

# 중요!
google-genai 라이브러리로 개발한 코드와 google-generativeai 라이브러리로 개발한 코드가 혼용되어 있습니다. 두 라이브러리를 requirements.txt를 통해 한번에 설치하였는데 `GenerativeModel.__init__() got an unexpected keyword argument 'system_instruction'`와 같은 오류가 발생한다면, 두 라이브러리 모두 pip uninstall 후, google-generativeai 라이브러리 설치 -> google-genai 라이브러리 설치 순서로 다시 설치해주세요.
