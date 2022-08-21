import asyncio
import telegram
import logging
log = logging.getLogger(__name__)
from . import config

bot = telegram.Bot(config.TELEGRAM_TOKEN)

async def send_message(message: str):
    async with bot:
        await bot.send_message(config.TELEGRAM_CHAT, message)
        #print(await bot.get_me())


if __name__ == '__main__':
    asyncio.run(send_message("test"))