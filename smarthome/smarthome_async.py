import asyncio
import json
from datetime import datetime
from datetime import timedelta
from dateutil import tz
from typing import Union, Optional
from . import mqtt
from . import weather
from . import clock
from . import sun
from . import bewaesserung
from . import web
from . import shutters
from . import light
from . import telegram_bot
from . import door
from . import console
from . import energy
from . import ups
from . import ebike
from wakeonlan import send_magic_packet

import logging
log = logging.getLogger(__name__)

def wake_komputer():
    send_magic_packet('BC-5F-F4-BA-FF-6D','BC-5F-F4-BA-FF-6A')
async def suspend_komputer():
    process = await asyncio.create_subprocess_exec("ssh", "komputer.fritz.box", "sudo", "systemctl", "suspend")
    await process.wait()
    
bla_running = False
async def bla():
    global bla_running
    if bla_running:
        log.info("already running")
        return
    bla_running = True
    try:
        while(True):
            mqtt.publish("zigbee2mqtt/Floalt-L1529-1/set", "TOGGLE")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log.info('cancel_me(): cancel sleep')
        raise
    finally:
        log.info('cancel_me(): after sleep')
        mqtt.publish("zigbee2mqtt/Floalt-L1529-1/set", "OFF")
        bla_running = False

async def doorbell():
    subscription = mqtt.subscribe("zigbee2mqtt/Erdgeschoss/Flur/Klingel")
    while True:
        msg = (await subscription.get()).json()
        if "action" in msg and msg["action"] in ["off", "brightness_move_down"]:
            log.info("Klingel!")
            telegram_bot.send_message("Klingel!")
            mqtt.publish([
                "zigbee2mqtt/Oben/Arbeitszimmer/Licht/nr1/set",
                "zigbee2mqtt/Oben/Flur/Licht/set",
                "zigbee2mqtt/Erdgeschoss/Flur/Licht/set",
                "zigbee2mqtt/Erdgeschoss/Wohnzimmer/Licht/nr1/set",
                "zigbee2mqtt/Keller/BadFlur/Licht/nr1/set",
                "zigbee2mqtt/Erdgeschoss/Arbeitszimmer/Licht/nr1/set",
                "zigbee2mqtt/Keller/Flur/Licht/nr1/set",
            ], '{"effect":"blink"}')

async def info():
    while True:
        log.info(f"{datetime.now()} Tasks:")
        for t in asyncio.all_tasks():
            log.info(t)
            try:
                e = t.exception()
                log.info(f"EXCEPTION: {e}")
            except Exception:
                pass
        await asyncio.sleep(1*60*60)  

async def ups_poll():
    while True:
        charge = await ups.get_ups_charge_async()
        status = await ups.get_ups_status_async()
        mqtt.publish("Keller/Serverraum/USV/battery.charge", str(charge))
        mqtt.publish("Keller/Serverraum/USV/ups.status", status)
        await asyncio.sleep(60)

async def main2():
    mqtt.start()
    await web.start()
    task = asyncio.create_task(info(), name = "info")

    # Licht Schlafzimmer
    task2 = asyncio.create_task(light.lightswitch(["zigbee2mqtt/Aqara-WXKG06LM-1", "zigbee2mqtt/ikea-e1810-1"], "zigbee2mqtt/Floalt-L1529-1"), name = "Licht Schlafzimmer")
    # Licht Arbeitszimmer
    asyncio.create_task(light.lightswitch("zigbee2mqtt/Oben/Arbeitszimmer/Lichtschalter/nr1", "zigbee2mqtt/Oben/Arbeitszimmer/Licht/nr1"), name = "Licht Arbeitszimmer")
    # Licht Treppenhaus
    task3 = asyncio.create_task(light.autolight(["zigbee2mqtt/Oben/Flur/BewegungLicht/nr1", "zigbee2mqtt/Erdgeschoss/Treppenhaus/Bewegung"], "zigbee2mqtt/Oben/Flur/Licht", night_only = True, on_payload = lambda: '{"brightness":1}' if 0 <= datetime.now().hour < 5 else '{"brightness":255}'), name = "Licht Treppenhaus")
    # Licht Flur Erdgeschoss
    #asyncio.create_task(light.autolight(["zigbee2mqtt/Erdgeschoss/Kellertreppe/Bewegung", "zigbee2mqtt/Erdgeschoss/Treppenhaus/Bewegung", "zigbee2mqtt/Erdgeschoss/Flur/Bewegung/nr1", "zigbee2mqtt/Erdgeschoss/Windfang/BewegungLicht"], "zigbee2mqtt/Erdgeschoss/Flur/Licht", night_only = True), name = "Licht Flur Erdgeschoss")
    # Licht Windfang
    asyncio.create_task(light.autolight(["zigbee2mqtt/Erdgeschoss/Windfang/BewegungLicht", "zigbee2mqtt/Erdgeschoss/Eingang/Kontakt"], "zigbee2mqtt/Erdgeschoss/Windfang/Licht", night_only = True), name = "Licht Windfang")
    # Licht Kellereingang
    asyncio.create_task(light.autolight(["zigbee2mqtt/Keller/Eingang/Kontakt", "zigbee2mqtt/Keller/Flur/Bewegung/nr1", "zigbee2mqtt/Keller/Treppe/Bewegung"], "zigbee2mqtt/Keller/Flur/Licht/nr1"), name = "Licht Kellereingang")
    # Licht Keller Badflur
    asyncio.create_task(light.autolight("zigbee2mqtt/Keller/BadFlur/Bewegung", "zigbee2mqtt/Keller/BadFlur/Licht/nr1"), name = "Licht Keller Badflur")
    # Licht Kellertreppe
    asyncio.create_task(light.autolight(["zigbee2mqtt/Erdgeschoss/Kellertreppe/Bewegung", "zigbee2mqtt/Keller/Treppe/Bewegung"], "zigbee2mqtt/Keller/Treppe/Licht"), name = "Licht Kellertreppe")
    # Licht Schlafzimmer 2
    asyncio.create_task(light.lightswitch("zigbee2mqtt/Oben/Schlafzimmer2/LichtSchalter/nr2", "zigbee2mqtt/Hue-Aurelle-1"), name = "Licht Schlafzimmer 2")
    # Licht Wintergarten
    asyncio.create_task(light.lightswitch("zigbee2mqtt/Erdgeschoss/Wintergarten/Lichtschalter/nr1", "zigbee2mqtt/Erdgeschoss/Wintergarten/Licht/nr1"), name = "Licht Wintergarten")
    # Licht Garage draußen
    asyncio.create_task(light.autolight("zigbee2mqtt/Draussen/Garage/BewegungLicht/nr1", "zigbee2mqtt/Draussen/Garage/Licht/nr1", night_only = True), name = "Licht Garage draußen")
    # Licht Garage
    asyncio.create_task(light.autolight("zigbee2mqtt/Garage/Bewegung/nr1", "zigbee2mqtt/ptvo-4relay-1", on_payload = '{"state_l2":"ON"}', off_payload = '{"state_l2":"OFF"}'), name = "Licht Garage")
    # Licht Wohnzimmer
    asyncio.create_task(light.lightswitch("zigbee2mqtt/Erdgeschoss/Wohnzimmer/Lichtschalter/nr1", "zigbee2mqtt/Erdgeschoss/Wohnzimmer/Licht/nr1"), name = "Licht Wohnzimmer")
    
    # Lüftung Bad
    asyncio.create_task(light.autolight("zigbee2mqtt/Vibration/nr1", "zigbee2mqtt/Sonoff-BASICZBR3-1"), name = "Lüftung Bad")
    
    # E-Bike
    asyncio.create_task(ebike.excess_charge2(), name = "E-Bike")

    # Klingel
    asyncio.create_task(doorbell(), name = "Klingel")

    # Offene Tür Warnung
    asyncio.create_task(door.door_warning("zigbee2mqtt/Keller/Eingang/Kontakt", "Kellertür offen gelassen!"), name = "Kellertür Warnung")
    asyncio.create_task(door.door_warning("zigbee2mqtt/Erdgeschoss/Eingang/Kontakt", "Kellertür offen gelassen!"), name = "Haustür Warnung")

    # Rolläden
    shutters.start()

    # Console
    task4 = asyncio.create_task(console.start(), name = "Console")

    # Bewässerung
    bewaesserung.start()

    # Solar
    asyncio.create_task(energy.calculate_w2kwh("zigbee2mqtt/Keller/Keller2/Solar"), name = "Solar")

    # USV
    asyncio.create_task(ups_poll(), name = "USV")

    light1 = light.Light("zigbee2mqtt/Oben/Arbeitszimmer/Licht/nr1")
    await asyncio.sleep(4)
    #light1.set_brightness(70)

    done, pending = await asyncio.wait({task4})

def main():
    logging.basicConfig(filename='smarthome.log', encoding='utf-8', level=logging.DEBUG, format='%(levelname)s\t%(asctime)s\t%(name)s\t%(message)s')
    logging.getLogger().addHandler(logging.StreamHandler())

    mqtt.load()
    try:
        asyncio.run(main2())
    finally:
        mqtt.save()

if __name__ == "__main__":
    main()