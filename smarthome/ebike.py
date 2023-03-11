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
        try:
            js = msg.json()
            net_power = js["MT681"]["Power_cur"]
        except:
            continue
        now = datetime.now()
        if min <= net_power <= max:
            if now - start_time > delta:
                return
        else:
            start_time = now

CHARGE_FINISH = 1
NO_EXCESS = 2
async def wait_for_excess_or_charge_finish(meter_subscription, min = -10000000, max = 10000000, delta = timedelta(minutes = 1)):
    start_time = datetime.now()
    charge_start = datetime.now()
    charge_power = net_power = None
    while(True):
        msg = (await meter_subscription.get())
        try:
            js = msg.json()
        except:
            continue
        now = datetime.now()
        if "MT681" in js:
            net_power = js["MT681"]["Power_cur"]
        elif "power" in js:
            charge_power = js["power"]

        if net_power is not None:
            if min <= net_power <= max:
                if now - start_time > delta:
                    return NO_EXCESS
            else:
                    start_time = now

        if charge_power is not None:
            if charge_power < 60:
                if now - charge_start > delta:
                    return CHARGE_FINISH
            else:
                charge_start = now

def queue_clear(q):
    while not q.empty():
        q.get_nowait()

async def excess_charge2():
    subscription = mqtt.subscribe([METER_TOPIC, CHARGER_TOPIC])
    while(True):
        queue_clear(subscription)
        log.info("E-Bike: Wait for excess power...")
        await wait_for_excess(subscription, max = -80)
        log.info("E-Bike: Start charging.")
        charge(True)
        ret = await wait_for_excess_or_charge_finish(subscription, min = 10, delta = timedelta(minutes = 1))
        log.info(f"E-Bike: Stop charging: {ret}")
        charge(False)
        if ret == CHARGE_FINISH:
            log.info("E-Bike: Battery full, waiting 24h...")
            await asyncio.sleep(24*60*60)
