
#from quart import Quart, render_template, websocket
from . import mqtt
import json
import logging
log = logging.getLogger(__name__)

""" app = Quart(__name__)
@app.route("/")
async def hello():
    return await render_template("index.html")

@app.route("/api")
async def json():
    return {"hello": "world"}

@app.websocket("/ws")
async def ws():
    while True:
        await websocket.send("hello")
        await websocket.send_json({"hello": "world"}) """

import aiohttp
from aiohttp import web

async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    mqtt.publish("zigbee2mqtt/Oben/Arbeitszimmer/Licht/nr1/set", "TOGGLE")
    return web.Response(text=text)

writers = []
async def wshandle(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    global writers
    writers.append(ws)

    async for msg in ws:
        if msg.type == web.WSMsgType.text:
            js = json.loads(msg.data)
            payload = js["payload"]
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            mqtt.publish(js["topic"], payload)
            #await ws.send_str("Hello, {}".format(msg.data))
        elif msg.type == web.WSMsgType.binary:
            ...
            #await ws.send_bytes(msg.data)
        elif msg.type == web.WSMsgType.close:
            writers.remove(ws)
            break

    return ws

async def websocket_write(message: str):
    #log.info(f"send websocket: {message}")
    global writers
    for w in writers:
        try:
            await w.send_str(message)
        except:
            pass

app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/echo', wshandle),
                web.get('/api/{name}', handle)])

app.router.add_static('/static/',
                          path='static',
                          name='static')

async def start():
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=5000)
    await site.start()