import asyncio
from datetime import datetime
from datetime import timedelta
from os import times_result
from typing import Optional
from suntime import Sun, SunTimeException

from .config import LATITUDE, LONGITUDE
from . import clock
import logging
log = logging.getLogger(__name__)

sun = Sun(LATITUDE, LONGITUDE)

def get_sunrise_time(now: Optional[datetime] = None) -> datetime:
    if now is None:
        now = datetime.now()
    time = sun.get_local_sunrise_time(now)
    time = time.replace(tzinfo=None)
    return time
    
def get_sunset_time(now: Optional[datetime] = None) -> datetime:
    if now is None:
        now = datetime.now()
    time = sun.get_local_sunset_time(now)
    time = time.replace(tzinfo=None)
    return time

async def wait_sunrise(offset:int = 0):
    log.info("wait for sunrise")
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    while(True):
        time = sun.get_local_sunrise_time(today) + timedelta(minutes = offset)
        time = time.replace(tzinfo=None)
        if time > now:
            break
        today = now + timedelta(days=1)
        
    await clock.wait_time(time)

async def wait_sunset(offset:int = 0):
    log.info("wait for sunset")
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    while(True):
        time = sun.get_local_sunset_time(today) + timedelta(minutes = offset)
        time = time.replace(tzinfo=None)
        if time > now:
            break
        today = now + timedelta(days=1)

    await clock.wait_time(time)
