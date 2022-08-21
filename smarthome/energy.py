import asyncio
import json
from datetime import datetime
from datetime import timedelta
import logging
from . import mqtt
from pathlib import Path
import typing
from . import mqtt

log = logging.getLogger(__name__)

HOME = str(Path.home())
FILE = HOME + "/.smarthome.energy.json"


def ws2kwh(ws):
    return round(ws / 60 / 60 / 1000, 3)

def load():
    try:
        with open(FILE, "r") as f:
            js = json.loads(f.read())
            return (js["energy_ws"], js["energy_ws_yesterday"], js["energy_ws_today"])
    except:
        log.exception(f"Failed to load energy from {FILE}")
        return (0, 0, 0)

def save(energy_ws, energy_ws_yesterday, energy_ws_today):
    with open(FILE, "w") as f:
        js = json.dumps({"energy_ws": energy_ws, "energy_ws_yesterday": energy_ws_yesterday, "energy_ws_today": energy_ws_today})
        f.write(js)

async def calculate_w2kwh(sensor_topic: str):
    log.info(f"Solar start")
    subscription = mqtt.subscribe(sensor_topic)

    energy_ws, energy_ws_yesterday, energy_ws_today = load()

    last_time = datetime.now()
    last_power = 0
    try:
        while(True):
            msg = (await subscription.get()).json()
            now = datetime.now()
            power = float(msg["power"])
            watt_seconds = power * (now - last_time).total_seconds()
            if watt_seconds != 0 or (now - last_time) > timedelta(minutes=10) or last_time.day != now.day:
                energy_ws += watt_seconds
                energy_ws_today += watt_seconds
                energy_kWh = ws2kwh(energy_ws)
                yesterday_kWh = ws2kwh(energy_ws_yesterday)
                today_kWh = ws2kwh(energy_ws_today)
                if last_time.day != now.day:
                    energy_ws_yesterday = energy_ws_today
                    energy_ws_today = 0
                #log.info(f"{sensor_topic} energy: {energy_kWh} power: {power}")
                mqtt.publish(f"virtual/{sensor_topic}/energy", json.dumps({"total": energy_kWh, "yesterday": yesterday_kWh, "today": today_kWh}))

            last_time = now
            last_power = power
    except asyncio.CancelledError:
        log.info('energy cancel')
        raise
    finally:
        save(energy_ws, energy_ws_yesterday, energy_ws_today)
        log.info('energy stop')

async def get_in_out() -> typing.List[float]:
    subscription = mqtt.subscribe("tele/smartmeter/SENSOR")
    msg = (await subscription.get()).json()
    return [msg["MT681"]["Total_in"], msg["MT681"]["Total_out"]]


loop = asyncio.get_event_loop()

async def run():
    mqtt.start()
    print(await get_in_out())

def main():
    loop.run_until_complete(run())

if __name__ == "__main__":
    main()