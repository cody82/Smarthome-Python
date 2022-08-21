import asyncio
from email import message
import paho.mqtt.client as mqtt
from datetime import datetime
from datetime import timedelta
from . import config
import json
from typing import Union
import pickle
import logging
log = logging.getLogger(__name__)

client = None

subscriptions = []
#queues = {}
loop = None
waiters={}

class Message():
    def __init__(self, message) -> None:
        self._message = message

    @property
    def topic(self) -> str:
        return self._message.topic
    
    @property
    def payload(self) -> str:
        return self._message.payload.decode()

    def json(self):
        return json.loads(self._message.payload.decode())

class State():
    def __init__(self, topic:str, payload:str, timestamp:datetime) -> None:
        self.topic = topic
        self.payload = payload
        self.timestamp = timestamp

    def json(self):
        return json.loads(self.payload.decode())

states: dict[str, State] = {}
def save():
    log.info("saving states...")
    file = open('smarthome.pickle', 'wb')
    pickle.dump(states, file)
    file.close()

def load():
    try:
        file = open('smarthome.pickle', 'rb')
    except FileNotFoundError:
        return
    states = pickle.load(file)
    file.close()

def changed_json(topic: str, new_message, index: str):
    if topic in states:
        old_message = states[topic].json()
        if index in old_message and index in new_message:
            return new_message[index] != old_message[index]
    return True
    
def changed(topic: str, new_payload: str):
    if topic in states:
        old_payload = states[topic].payload
        return new_payload != old_payload
    return True

def create_queue(topic: Union[str, list[str]]) -> asyncio.Queue:
    global waiters
    q = asyncio.Queue(10)
    if isinstance(topic, str):
        topic = [topic]
    for t in topic:
        if t in waiters:
            waiters[t].append(q)
        else:
            waiters[t] = [q]
    return q

def subscribe(topic: Union[str, list[str]]) -> asyncio.Queue[Message]:
    global client
    global subscriptions
    if isinstance(topic, str):
        topic = [topic]
    #global queues
    #queues[topic] = asyncio.Queue()
    log.info(f"subscribe {topic}")
    for t in topic:
        if t not in subscriptions:
            subscriptions.append(t)
            client.subscribe(t)
    return create_queue(topic)

def publish(topic: Union[str, list[str]], message):
    global client
    #log.info(f"publish: {topic}")
    if isinstance(topic, str):
        topic = [topic]
    for t in topic:
        log.info(f"MQTT>> {t} {message}")
        client.publish(t, message)

async def on_connect_async(client, userdata, flags, rc):
    log.info("Connected with result code "+str(rc))

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global loop
    asyncio.run_coroutine_threadsafe(on_connect_async(client, userdata, flags, rc), loop)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe("$SYS/#")


async def on_message_async(client, userdata, msg):
    log.info(f"on_message {msg.topic} {msg.payload.decode()}")
    message = Message(msg)
    states[msg.topic] = State(msg.topic, message.payload, datetime.now())
    if msg.topic in waiters:
        queues = waiters[msg.topic]
        for q in queues:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                log.info(f"Queue full for topic {msg.topic}, message dropped.")
    from . import web
    await web.websocket_write(message.topic + " " + message.payload)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global loop
    asyncio.run_coroutine_threadsafe(on_message_async(client, userdata, msg), loop)


def start():
    global client
    global loop
    loop = asyncio.get_running_loop()
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(config.MQTT_HOST, 1883, 60)
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    #client.loop_forever()
    client.loop_start()
