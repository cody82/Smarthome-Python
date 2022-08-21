import asyncio
import json
from datetime import datetime
from datetime import timedelta
import logging
from . import mqtt

log = logging.getLogger(__name__)

def charge(on):
    mqtt.publish(CHARGER_TOPIC + "/set", "ON" if on else "OFF")

METER_TOPIC = "tele/smartmeter/SENSOR"
CHARGER_TOPIC = "zigbee2mqtt/Garage/Fahrrad/Steckdose"

async def excess_charge():
    subscription = mqtt.subscribe([METER_TOPIC, CHARGER_TOPIC])
    time = datetime.now()
    charging = False
    net_power = None
    charge_power = None
    charge_start = None
    try:
        while(True):
            msg = (await subscription.get())
            js = msg.json()
            now = datetime.now()
            delta = now - time
            if msg.topic == METER_TOPIC:
                net_power = js["MT681"]["Power_cur"]
                if net_power < -50:
                    if delta > timedelta(minutes = 30) and not charging:
                        charge(True)
                        charging = True
                        charge_start = now
                else:
                    if not charging:
                        time = now
                    elif net_power > 60:
                        if delta > timedelta(minutes = 10):
                            charge_start = None
                            charge(False)
                            charging = False
                            time = now
            elif msg.topic == CHARGER_TOPIC:
                charge_power = js["power"]
                if charge_power < 40 and charge_start is not None and now - charge_start > timedelta(minutes = 1):
                    charge_start = None
                    charge(False)
                    charging = False
                    time = now
    except asyncio.CancelledError:
        log.info('smartmeter cancel')
        raise
    finally:
        log.info('smartmeter stop')


async def wait_for_excess(meter_subscription, min = -10000000, max = 10000000, delta = timedelta(minutes = 1)):
    start_time = datetime.now()
    while(True):
        msg = (await meter_subscription.get())
        js = msg.json()
        now = datetime.now()
        net_power = js["MT681"]["Power_cur"]
        if min <= net_power <= max:
            if now - start_time > delta:
                return
        else:
            start_time = now

def queue_clear(q):
    while not q.empty():
        q.get_nowait()

async def excess_charge2():
    meter_subscription = mqtt.subscribe(METER_TOPIC)
    while(True):
        queue_clear(meter_subscription)
        log.info("E-Bike: Wait for excess power...")
        await wait_for_excess(meter_subscription, max = -50)
        log.info("E-Bike: Start charging.")
        charge(True)
        await wait_for_excess(meter_subscription, min = 10, delta = timedelta(minutes = 1))
        log.info("E-Bike: Stop charging.")
        charge(False)