"""
GarlicBot - Discord Bot Main Entry Point

A modular Discord bot built with discord.py and Cog-based architecture.
Supports moderation, XP system, role management, security features, and AI commands.
"""

import discord
import os
import logging
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PRESENCE_INTERVAL = 30

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Bot configuration
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.reactions = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Add logger to bot instance for Cog compatibility
bot.logger = logging.getLogger('GarlicBot')

async def update_presence():
    """Update bot presence with rotating status messages."""
    status_messages = [
        lambda: f"{len(bot.guilds)}개의 서버에서 활동",
        lambda: f"{sum(len(guild.members) for guild in bot.guilds)}명의 사용자와 활동"
    ]

    current_index = 0

    while True:
        try:
            if callable(status_messages[current_index]):
                status_text = status_messages[current_index]()
            else:
                status_text = status_messages[current_index]

            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=status_text
                )
            )

            current_index = (current_index + 1) % len(status_messages)
            await asyncio.sleep(PRESENCE_INTERVAL)

        except Exception as e:
            logging.error(f'Failed to update presence: {e}')
            await asyncio.sleep(PRESENCE_INTERVAL)

# Bot event handlers
@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logging.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logging.info(f'Connected to {len(bot.guilds)} guilds')

    # Start presence update task
    bot.loop.create_task(update_presence())

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="권한 부족",
            description="이 명령어를 사용할 권한이 없습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="인자 부족",
            description="필요한 인자가 제공되지 않았습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    else:
        logging.error(f'Command error: {error}')
        embed = discord.Embed(
            title="오류",
            description="명령어 실행 중 오류가 발생했습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

async def load_cogs():
    """Load all Cog-based commands."""
    cogs = [
        'commands_v2.moderation',
        'commands_v2.mention_delay',
        'commands_v2.bulk_cancel',
        'commands_v2.xp',
        'commands_v2.roles',
        'commands_v2.remove_all_roles',
        'commands_v2.autorole',
        'commands_v2.security',
        'commands_v2.ai',
        'commands_v2.ping',
        'commands_v2.timestamp',
        'commands_v2.server_info',
        'commands_v2.weather',
        'events.moderation',
        'events.guild',
        'events.message',
        'events.member'
    ]

    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logging.info(f'Successfully loaded cog: {cog}')
        except Exception as e:
            logging.error(f'Failed to load cog {cog}: {e}')

async def main():
    """Main entry point for the bot."""
    # Load all cogs
    await load_cogs()

    # Get Discord token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logging.error('DISCORD_BOT_TOKEN environment variable not found!')
        return

    # Start the bot
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logging.info('Bot shutdown requested by user')
    except Exception as e:
        logging.error(f'Bot startup failed: {e}')
    finally:
        await bot.close()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
