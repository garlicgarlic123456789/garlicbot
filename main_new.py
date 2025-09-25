"""
GarlicBot 2.0 - Main Entry Point
"""

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.bot import get_bot
from core.exceptions import GarlicBotException
from config import settings


def setup_logging():
    """로깅 시스템 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('garlicbot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Discord.py 로깅 레벨 조정
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)


async def main():
    """메인 실행 함수"""
    # 로깅 설정
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("GarlicBot 2.0 Starting...")
    logger.info("=" * 50)
    
    try:
        # 봇 인스턴스 생성
        bot = get_bot()
        
        # 봇 시작
        logger.info("Starting bot...")
        await bot.start(settings.DISCORD_TOKEN)
        
    except GarlicBotException as e:
        logger.error(f"GarlicBot error: {e}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        if 'bot' in locals():
            await bot.close()
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if 'bot' in locals():
            await bot.close()
        sys.exit(1)
    
    finally:
        logger.info("GarlicBot shutdown complete")


if __name__ == "__main__":
    """
    봇 실행 진입점
    
    이제 main.py는 단순히 봇을 시작하는 역할만 합니다.
    모든 복잡한 로직은 적절한 모듈로 분리되었습니다.
    """
    
    # 환경 확인
    if not settings.DISCORD_TOKEN:
        print("DISCORD_TOKEN이 설정되지 않았습니다!")
        print("   .env 파일에 DISCORD_TOKEN을 추가해주세요.")
        sys.exit(1)
    
    # 봇 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGarlicBot을 종료합니다...")
    except Exception as e:
        print(f"치명적 오류: {e}")
        sys.exit(1)