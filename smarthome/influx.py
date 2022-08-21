from distutils.command.config import config
from influxdb import InfluxDBClient
import json
import paho.mqtt.client as mqtt
from . import config

def write(influx, topic: str, value: dict):
    fields = influx[0]["fields"]
    for k in value.keys():
        v = value[k]
        if topic!="":
            name = topic + "." + k
        else:
            name = k
        if isinstance(v, int):
            fields[name] = float(v)
        elif isinstance(v, float) or isinstance(v, str) or isinstance(v, bool):
            fields[name] = v
        elif isinstance(v, dict):
            write(influx, name, v)

value = '{"temperature": 25.0, "battery": 100, "d":{"x":1}}'
def convert(topic:str, value:str, conv = lambda x: float(x)):
    influx = [
    {
        "measurement": topic,
        "tags": {
        },
        #"time": "2009-11-10T23:00:00Z",
        "fields": {
        }
    }
    ]

    js = None
    try:
        js = json.loads(value)
    except:
        pass
    try:
        value = conv(value)
    except:
        pass
    if js is not None:
        if isinstance(js, dict):
            write(influx, "", js)
        else:
            influx[0]["fields"]["value"] = value
    else:
        influx[0]["fields"]["value"] = value
    #print(influx)
    return influx

client = None

def on_message(c, userdata, msg):
    global client
    if msg.retain == 1:
        return
    try:
        payload = msg.payload.decode()
    except:
        return
    influx = convert(msg.topic, payload)
    try:
        client.write_points(influx)
    except Exception as e:
        print(influx)
        print(e)
        print("retry as string:")
        influx = convert(msg.topic, payload, lambda x: x)
        try:
            client.write_points(influx)
            print("OK")
        except Exception as e:
            print("failed:")
            print(influx)
            print(e)

def on_connect(client, userdata, flags, rc):
    #log.info("Connected with result code "+str(rc))
    client.subscribe("#")

def main():
    global client
    client = InfluxDBClient(config.INFLUX_HOST, config.INFLUX_PORT, config.INFLUX_USER, config.INFLUX_PASSWORD, config.INFLUX_DATABASE)

    #>>> client.write_points(json_body)

    #result = client.query('select last(*) from "zigbee2mqtt/Draussen/Garage/Thermometer/nr1";')

    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_message
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(config.MQTT_HOST, config.MQTT_PORT, 60)

    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
#    loop = asyncio.get_running_loop()
