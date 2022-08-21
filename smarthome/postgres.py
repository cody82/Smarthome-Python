import asyncio
import asyncpg
import paho.mqtt.client as mqtt
import logging
from . import config
import threading

logging.basicConfig(encoding='utf-8', level=logging.DEBUG)#, format='%(levelname)s\t%(asctime)s\t%(name)s\t%(message)s')
#logging.getLogger().addHandler(logging.StreamHandler())
log = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

client = None
pg = None

async def on_message_async(client, userdata, msg):
    if msg.retain == 1:
        return

    payload = msg.payload.decode().replace('\x00','')
    topic = msg.topic.replace('\x00','')
    try:
        log.info(f"on_message {topic} {payload}")
        await pg.execute('''
            INSERT INTO mqtt(topic, msg) VALUES($1, $2)
        ''', topic, payload)
    except:
        log.exception("PG execute failed")
    

def on_message(client, userdata, msg):
    global loop
    asyncio.run_coroutine_threadsafe(on_message_async(client, userdata, msg), loop).result()

async def on_connect_async(client: mqtt.Client, userdata, flags, rc):
    log.info("Connected with result code "+str(rc))
    client.subscribe("#")
    

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global loop
    print("mqtt connected")
    print(threading.current_thread().ident)
    asyncio.run_coroutine_threadsafe(on_connect_async(client, userdata, flags, rc), loop).result()


async def run():
    global pg
    pg = await asyncpg.connect(user=config.POSTGRES_USER, password=config.POSTGRES_PASSWORD,
        database=config.POSTGRES_DATABASE, host=config.POSTGRES_HOST)
    print("pg connected")
    global client
    global loop
    client = mqtt.Client()


    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(config.MQTT_HOST, config.MQTT_PORT, 60)

def main():
    global client, loop
    #print(threading.current_thread().ident)
    loop.run_until_complete(run())
    client.loop_start()
    loop.run_forever()

if __name__ == "__main__":
    main()
