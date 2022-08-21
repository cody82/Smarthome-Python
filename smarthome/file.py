import paho.mqtt.client as mqtt
import logging
import os
from pathlib import Path
from . import config

log = logging.getLogger(__name__)
home = str(Path.home())
BASEDIR = home + "/node-red-storage"

def on_message(c, userdata, msg):
    if msg.retain == 1:
        return
    
    path = f"{BASEDIR}/{msg.topic}.txt"
    
    log.info(f">> {path}")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(msg.payload)
        

def on_connect(client, userdata, flags, rc):
    log.info("Connected with result code "+str(rc))
    client.subscribe("#")

def main():
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG, format='%(message)s')
    #logging.getLogger().addHandler(logging.StreamHandler())

    mqtt_client = mqtt.Client()
    #    loop = asyncio.get_running_loop()
    mqtt_client.on_message = on_message
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(config.MQTT_HOST, config.MQTT_PORT, 60)

    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
