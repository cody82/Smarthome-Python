import asyncio
from datetime import datetime
from datetime import timedelta
import logging
from . import mqtt
from . import telegram_bot

log = logging.getLogger(__name__)


def filter_queue(in_queue: asyncio.Queue, filter_func) -> asyncio.Queue:
    out_queue = asyncio.Queue(1)
    filter_task = asyncio.create_task(filter(in_queue, out_queue, filter_func), name = "filter_queue")
    return out_queue


async def filter(q1: asyncio.Queue, q2: asyncio.Queue, filter_func):
    while True:
        item = await q1.get()
        if filter_func(item):
            await q2.put(item)


async def report_by_exception_json(q1: asyncio.Queue, q2: asyncio.Queue, property: str):
    last_value = None
    while True:
        item = (await q1.get()).json()
        log.info(str(item))
        is_new = False
        if last_value is not None:
            if property in item:
                new_value = item[property]
                if new_value != last_value:
                    is_new = True
        else:
            is_new = property in item
        
        last_value = item[property] if property in item else None
        if is_new:
            await q2.put(item)

def filter_queue_coro(in_queue: asyncio.Queue, coro) -> asyncio.Queue:
    out_queue = asyncio.Queue(1)
    filter_task = asyncio.create_task(coro, name = "filter_queue_coro")
    return out_queue

async def door_warning(topic: str, warning_text: str):
    subscription = mqtt.subscribe(topic)
    filtered = asyncio.Queue(1)
    filter_task = asyncio.create_task(report_by_exception_json(subscription, filtered, "contact"), name = "Tür Warnung")
    log.info("Wait for door info...")
    msg = await filtered.get()
    log.info(str(msg))
    contact = msg["contact"]
    log.info(f"First door info: {contact}")
    while True:
        while not contact:
            log.info("Door is open: Wait with timeout...")
            try:
                msg = await asyncio.wait_for(filtered.get(), 10 * 60)
                contact = msg["contact"]
                log.info(f"Door was closed: {contact}")
            except asyncio.TimeoutError:
                log.info("Warning: Door still open!")
                await telegram_bot.send_message(warning_text)
        log.info("Door is closed, waiting to open...")
        msg = await filtered.get()
        contact = msg["contact"]

