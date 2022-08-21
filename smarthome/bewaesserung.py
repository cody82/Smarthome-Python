import asyncio
import json
from . import mqtt
from . import clock
from . import weather
import logging
log = logging.getLogger(__name__)

auto_enabled = True


async def watering_set():
    global auto_enabled
    subscription = mqtt.subscribe("virtual/watering/set")
    while True:
        try:
            msg = (await subscription.get()).json()
            publish = False
            if "auto" in msg:
                auto_enabled = msg["auto"]
                publish = True
        except:
            log.exception("Failed to parse json.")
            continue
        if publish:
            params_publish()

def params_publish():
    mqtt.publish("virtual/watering", json.dumps({"auto": auto_enabled}))

async def bewaesserung_auto():
    while(True):
        log.info("Automatische Bewässerung: Warte auf 5:00")
        await clock.wait_clock(5, 0)
        log.info("Automatische Bewässerung: Wetter prüfen")
        on = await weather.bewaesserung()
        if on:
            log.info("Automatische Bewässerung: Wetter OK")
            if auto_enabled:
                await bewaesserung()
            else:
                log.info("Automatische Bewässerung: Aus")
        else:
            log.info("Automatische Bewässerung: Keine Bewässerung wegen Wetter")


bewaesserung_running = False
async def bewaesserung():
    global bewaesserung_running
    if bewaesserung_running:
        log.info("already running")
        return
    bewaesserung_running = True
    factor = 60
    log.info('Bewaesserung gestartet')
    try:
        # rasen hinten an
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l1": "ON"}))
        # vorne an
        mqtt.publish("zigbee2mqtt/Draussen/Vorne/Bewaesserung/set", json.dumps({"state": "ON"}))
        # 20 min warten
        await asyncio.sleep(20 * factor)
        # vorne aus
        mqtt.publish("zigbee2mqtt/Draussen/Vorne/Bewaesserung/set", json.dumps({"state": "OFF"}))
        # kellereingang an
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l2": "ON"}))
        # 10 min warten
        await asyncio.sleep(10 * factor)
        # kellereingang aus
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l2": "OFF"}))
        # beete an
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l3": "ON"}))
        # 60 min warten
        await asyncio.sleep(60 * factor)
        # beete aus
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l3": "OFF"}))
        # tanne an
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l4": "ON"}))
        # 30 min warten
        await asyncio.sleep(30 * factor)
        # tanne aus
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l4": "OFF"}))

    except asyncio.CancelledError:
        log.info('Bewaesserung abgebrochen')
        raise
    finally:
        log.info('Bewaesserung beendet')
        mqtt.publish("zigbee2mqtt/Draussen/Vorne/Bewaesserung/set", json.dumps({"state": "OFF"}))
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l1": "OFF"}))
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l2": "OFF"}))
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l3": "OFF"}))
        mqtt.publish("zigbee2mqtt/Draussen/Hinten/Bewaesserung/set", json.dumps({"state_l4": "OFF"}))
        bewaesserung_running = False

def start():
    asyncio.create_task(watering_set(), name = "watering.watering_set")
    asyncio.create_task(bewaesserung_auto(), name = "watering.bewaesserung_auto")
    params_publish()
