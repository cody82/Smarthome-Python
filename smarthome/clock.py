import asyncio
from datetime import datetime
from datetime import timedelta
import logging
log = logging.getLogger(__name__)

async def wait_clock(h,m):
    now = datetime.now()
    
    target = datetime(now.year, now.month, now.day) + timedelta(hours=h, minutes=m)
    if target <= datetime.now():
        target = target + timedelta(days=1)

    diff = target - now
    log.info(f"Clock wait start for {target}, sleeping {diff}")
    await asyncio.sleep(diff.total_seconds())
    log.info(f"wait complete complete for {target}")

async def wait_time(target:datetime):
    log.info(f"wait for {target}")
    diff = target - datetime.now()
    seconds = diff.total_seconds()
    if seconds > 0:
        await asyncio.sleep(seconds)
