import asyncio
import json
from datetime import datetime
from datetime import timedelta
from functools import reduce
import httpx
from .config import LATITUDE, LONGITUDE
import logging
log = logging.getLogger(__name__)

async def brightsky(date:datetime):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.brightsky.dev/weather?lat={LATITUDE}&lon={LONGITUDE}&date={date.year}-{date.month:02d}-{date.day:02d}")
    js = json.loads(response.text)
    weather = js["weather"]
    return weather

def precipitation(w):
    precipitation = reduce(lambda x,y: x+y, map(lambda x: x["precipitation"], w))
    return precipitation

async def bewaesserung() -> bool:
    try:
        today = await brightsky(datetime.now())
        yesterday = await brightsky(datetime.now()-timedelta(days=1))
        p_today = precipitation(today)
        p_yesterday = precipitation(yesterday)
        log.info(f"Niederschlag gestern: {p_yesterday}, heute: {p_today}")
        return precipitation(today) + precipitation(yesterday) <= 3
    except BaseException as e:
        log.info(e)
        return False
