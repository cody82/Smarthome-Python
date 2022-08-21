import asyncio
import json
from . import mqtt
from . import sun
from typing import Union, Optional
from datetime import datetime, timedelta
import logging
log = logging.getLogger(__name__)

async def lightswitch(switch_topic, light_topic):
    if isinstance(switch_topic, str):
        switch_topic = [switch_topic]

    subscription = mqtt.subscribe(switch_topic)
    light_topic_set = light_topic + "/set"
    try:
        while(True):
            #log.info("Switch wait")
            msg = (await subscription.get()).json()
            if "action" in msg and msg["action"] in ["toggle", "single", "press_3"]:
                #log.info("Switch publish")
                mqtt.publish(light_topic_set, "TOGGLE")
    except asyncio.CancelledError:
        log.info('switch abgebrochen')
        raise
    finally:
        log.info('switch beendet')
        #mqtt.publish(light_topic_set, json.dumps({"state": "OFF"}))


async def filter(q1: asyncio.Queue, q2: asyncio.Queue, filter_func):
    while True:
        item = await q1.get()
        if filter_func(item):
            await q2.put(item)

def filter_queue(in_queue: asyncio.Queue, filter_func) -> asyncio.Queue:
    out_queue = asyncio.Queue(1)
    filter_task = asyncio.create_task(filter(in_queue, out_queue, filter_func), name = "filter_queue")
    return out_queue

def changed_json(old_message, new_message, index: str):
    if old_message is None:
        return True
        
    if index in old_message and index in new_message:
        return new_message[index] != old_message[index]

    return True
    
#def changed(topic: str, new_payload: str):
#    if topic in states:
#        old_payload = states[topic].payload
#        return new_payload != old_payload
#    return True

class Light:
    EFFECT_BLINK = "blink"
    EFFECT_BREATHE = "breathe"
    EFFECT_OKAY = "okay"

    def __init__(self, topic: str) -> None:
        self.subscription = None
        self.topic = topic
        self.state = None
        self.task = asyncio.create_task(self.run(), name = f"Light {topic}")

    async def run(self):
        self.subscription = mqtt.subscribe(self.topic)
        log.info(f"Light task run")
        while True:
            self.state = (await self.subscription.get()).json()
            log.info(f"Light {self.topic} state: {self.state}")
    def toggle(self):
        mqtt.publish(self.topic + "/set", "TOGGLE")
    def set_brightness(self, brightness:int):
        mqtt.publish(self.topic + "/set", json.dumps({"brightness":brightness}))
    def effect(self, effect:str):
        mqtt.publish(self.topic + "/set", json.dumps({"effect":effect}))


async def autolight(sensor_topic: Union[str, list[str]], light_topic: Union[str, list[str]], night_only: bool = False, on_payload: str = "ON", off_payload: str = "OFF"):
    last_state = None
    
    if isinstance(sensor_topic, str):
        sensor_topic = [sensor_topic]
    if isinstance(light_topic, str):
        light_topic = [light_topic]

    light_topic_set = [t + "/set" for t in light_topic]

    subscription = mqtt.subscribe(sensor_topic)
    def filter(msg):
        msg = msg.json()
        
        #if "occupancy" in msg:
        #    if not changed_json(last_state, msg, "occupancy"):
        #        return False
        #elif "contact" in msg:
        #    if not changed_json(last_state, msg, "occupancy"):
        #        return False

        #if last_state is not None and not mqtt.changed_json()
        #last_state = msg
        occupancy = "occupancy" in msg and msg["occupancy"] == True
        contact = "contact" in msg and msg["contact"] == False
        vibration = "action" in msg and msg["action"] == "vibration"
        tilt = "action" in msg and msg["action"] == "tilt"
        drop = "action" in msg and msg["action"] == "drop"
        
        switch_on = occupancy or contact or vibration or tilt or drop
        if not switch_on:
            return False

        if night_only:
            sunrise = sun.get_sunrise_time()
            sunset = sun.get_sunset_time()
            if sunrise < datetime.now() < sunset:
                log.info("Dont switch light on during day.")
                return False
        return True

    filtered_subscription = filter_queue(subscription, filter)

    last_payload = None
    last_publish = None
    while(True):
        #log.info("autolight wait")
        payload = None
        try:
            msg = (await asyncio.wait_for(filtered_subscription.get(), 5 * 60)).json()
            #log.info("autolight on")
            if not isinstance(on_payload, str):
                payload = on_payload()
            else:
                payload = on_payload
            #mqtt.publish(light_topic_set, on_payload)
        except asyncio.TimeoutError:
            #log.info("autolight off")
            payload = off_payload
        if last_payload != payload or datetime.now() - last_publish > timedelta(minutes=30):
            mqtt.publish(light_topic_set, payload)
        else:
            log.info(f"publish canceled: {light_topic_set} {payload}")
        last_payload = payload
        last_publish = datetime.now()
        

#class Light:
#    def __init__(self, topic) -> None:
#        self.topic = topic
#    def toggle(self):
