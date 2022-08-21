import asyncio
import json
from typing import Union, Optional
from . import mqtt
import logging
log = logging.getLogger(__name__)

async def is_open():
    topic = "zigbee2mqtt/Garage/Tor/Oeffner"
    subscription = mqtt.subscribe(topic)
    #mqtt.publish(topic + "/get", '{"garage_door_contact":""}')
    msg = (await subscription.get()).json()
    contact = msg["garage_door_contact"]
    return not contact


