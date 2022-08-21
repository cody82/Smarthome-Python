import asyncio
import json
from . import sun
from . import mqtt
from . import clock
from datetime import datetime
import logging
log = logging.getLogger(__name__)

vacation: bool = True
cooling: bool = True

def start():
    task1 = asyncio.create_task(auto_sunset(), name = "shutters.sunset")
    task2 = asyncio.create_task(auto_sunrise(), name = "shutters.sunrise")
    task3 = asyncio.create_task(auto_clock_23(), name = "shutters.clock23")
    task4 = asyncio.create_task(auto_clock_night_open(), name = "shutters.night_open")
    task5 = asyncio.create_task(auto_clock_morning_open(), name = "shutters.morning_open")
    task6 = asyncio.create_task(vacation_set(), name = "shutters.vacation_set")
    params_publish()

async def vacation_set():
    global vacation, cooling
    subscription = mqtt.subscribe("virtual/shutters/set")
    while True:
        try:
            msg = (await subscription.get()).json()
            publish = False
            if "vacation" in msg:
                vacation = msg["vacation"]
                publish = True
            if "cooling" in msg:
                cooling = msg["cooling"]
                publish = True
        except:
            log.error("Failed to parse json.")
            continue
        if publish:
            params_publish()

def params_publish():
    mqtt.publish("virtual/shutters", json.dumps({"vacation": vacation, "cooling": cooling}))


async def auto_sunset():
    while(True):
        await sun.wait_sunset()
        # Erdgeschoss
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Kueche/Rollo/neu/set", json.dumps({"position": 20 if cooling else 0}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Rollo/nr1-neu/set", json.dumps({"position": 20 if cooling else 0}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Rollo/nr2-neu/set", json.dumps({"position": 20 if cooling else 0}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Arbeitszimmer/Rollo/neu/set", json.dumps({"position": 20 if cooling else 0}))
        # Oben
        if not cooling:
            #mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu1/set", json.dumps({"position": 20}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu2/set", json.dumps({"position": 0}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu3/set", json.dumps({"position": 0}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/nr1/set", json.dumps({"position": 0}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/neu2/set", json.dumps({"position": 0}))

async def auto_sunrise():
    while(True):
        await sun.wait_sunrise(-60)
        # close
        mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu1/set", json.dumps({"position": 0}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu2/set", json.dumps({"position": 0}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu3/set", json.dumps({"position": 0}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/nr1/set", json.dumps({"position": 0}))
        await asyncio.sleep(60)

        await asyncio.sleep((60-4)*60)
        #open
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Kueche/Rollo/neu/set", json.dumps({"position": 50 if cooling else 100}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Rollo/nr1-neu/set", json.dumps({"position": 50 if cooling else 100}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Rollo/nr2-neu/set", json.dumps({"position": 50 if cooling else 100}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Erdgeschoss/Arbeitszimmer/Rollo/neu/set", json.dumps({"position": 50 if cooling else 100}))

async def auto_clock_23():
    while(True):
        await clock.wait_clock(23, 0)
        if cooling:
            #mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu1/set", json.dumps({"position": 20}))
            #await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu2/set", json.dumps({"position": 20}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu3/set", json.dumps({"position": 20}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/nr1/set", json.dumps({"position": 20}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/neu2/set", json.dumps({"position": 20}))

async def auto_clock_night_open():
    while(True):
        await clock.wait_clock(3, 0)
        # open at night for cooling
        if cooling:
            mqtt.publish("zigbee2mqtt/Erdgeschoss/Kueche/Rollo/neu/set", json.dumps({"position": 100}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Rollo/nr1-neu/set", json.dumps({"position": 100}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Rollo/nr2-neu/set", json.dumps({"position": 100}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Erdgeschoss/Arbeitszimmer/Rollo/neu/set", json.dumps({"position": 100}))
            await asyncio.sleep(60)
            mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu1/set", json.dumps({"position": 100}))

def is_workday():
    return (not vacation) and datetime.now().weekday() < 5
    #return datetime.now().weekday() < 5

async def auto_clock_morning_open():
    while(True):
        log.info("Wait for morning")
        await clock.wait_clock(3, 0)
        work = is_workday()
        # open at morning
        if work:
            log.info("Wait for workday open")
            await clock.wait_clock(7, 30)
        else:
            log.info("Wait for vacation open")
            await clock.wait_clock(9, 30)

        # schlafzimmer
        mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/nr1/set", json.dumps({"position": 50 if cooling else 100}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Oben/Schlafzimmer/Rollo/neu2/set", json.dumps({"position": 50 if cooling else 100}))
        await asyncio.sleep(15 * 60)
        # arbeitszimmer
        mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu1/set", json.dumps({"position": 40 if cooling else 100}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu2/set", json.dumps({"position": 30 if cooling else 100}))
        await asyncio.sleep(60)
        mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Rollo/neu3/set", json.dumps({"position": 50 if cooling else 100}))
        await asyncio.sleep(60)
