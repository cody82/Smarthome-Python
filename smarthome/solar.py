import asyncio
from dataclasses import dataclass
from . import mqtt

class Inverter:
    def __init__(self, serial: str, max_power: int) -> None:
        self.serial = serial
        self.max_power = max_power
        self.power_limit = max_power
        self.power = 0
        self.producing = False

        self.subscription = mqtt.subscribe([
            self.current_power_limit_absolute_topic(),
            self.power_topic(),
            self.producing_topic(),
        ])

        self.task = asyncio.create_task(self.worker())
        self.event = None

    async def worker(self):
        while True:
            msg = await self.subscription.get()
            if msg.topic == self.power_topic():
                self.power = int(float(msg.payload))
            if msg.topic == self.current_power_limit_absolute_topic():
                self.power_limit = int(float(msg.payload))
            if msg.topic == self.producing_topic():
                self.producing = int(msg.payload) == 1
            if self.event:
                self.event.set()

    def producing_topic(self) -> str:
        return f"opendtu/{self.serial}/status/producing"

    def current_power_limit_absolute_topic(self) -> str:
        return f"opendtu/{self.serial}/status/limit_absolute"
    def power_topic(self) -> str:
        return f"opendtu/{self.serial}/0/power"
    
    def set_power_limit(self, power_limit: int):
        power_limit = min(power_limit, self.max_power)
        power_limit = max(power_limit, 10)
        if self.power_limit != power_limit:
            mqtt.publish(f"opendtu/{self.serial}/cmd/limit_nonpersistent_absolute", str(power_limit))
        #self.power_limit = power_limit

    def load(self) -> float:
        if self.power_limit <= 10:
            return 1
        return self.power / self.power_limit

    def is_limited(self) -> bool:
        return self.load() > 0.8
        #if self.power_limit <= 10:
            #return False
        #return self.power_limit - self.power < self.max_power * 0.05

class Smartmeter:
    def __init__(self) -> None:
        self.topic = "tele/smartmeter/SENSOR"
        self.subscription = mqtt.subscribe(self.topic)
        self.task = asyncio.create_task(self.worker())
        self.event = None
        self.power = 0

    async def worker(self):
        while True:
            msg = (await self.subscription.get()).json()
            self.power = int(float(msg["MT681"]["Power_cur"]))
            if self.event:
                self.event.set()

def limit(inverters: list[Inverter], grid: Smartmeter):
    if not all([i.producing for i in inverters]):
        print("inverters offline")
        return
    power = inverters[0].power + inverters[1].power
    max_power = inverters[0].max_power + inverters[1].max_power
    limit = inverters[0].power_limit + inverters[1].power_limit
    #if power != last_power or :
    print(f"solar: {power}/{limit}W, grid: {grid.power}W")
    correction = grid.power + 50
    wanted_power = power + correction
    power_limit = [300,300] #fallback
    load_sum = sum([i.load() for i in inverters])
    print(f"correction: {correction}, wanted: {wanted_power}")
    if wanted_power >= max_power:
        power_limit = [i.max_power for i in inverters]
    else:
        if correction < 20:
            # too much power
            power_limit = [i.power + (i.power / power * correction) for i in inverters]
        elif correction > 20:
            if all([i.load() < 0.5 and i.power_limit > 100 for i in inverters]):
                print("no sun")
                power_limit = None
            else:
                # need more power
                power_limit = [i.power + (i.load() / load_sum * correction) for i in inverters]
                print(power_limit)
                excess = [max(power_limit[i] - inverters[i].max_power, 0) for i in range(len(power_limit))]
                power_limit = [power_limit[i] - excess[i] for i in range(len(power_limit))]
                print(power_limit)
                print(f"excess: {excess}")
                excess = sum(excess)
                free = [inverters[i].max_power - power_limit[i] for i in range(len(power_limit))]
                print(f"free: {free}")
                power_limit = [power_limit[i] + excess * free[i] / sum(free) for i in range(len(power_limit))]

        else:
            power_limit = None

    if power_limit:
        power_limit = [int(p) for p in power_limit]
        for i in range(len(inverters)):
            inverters[i].set_power_limit(power_limit[i])
        print(f"new limits: {power_limit}")

async def main_async():
    mqtt.start()
    inverters = [
        Inverter("114181013675", 800),
        Inverter("116183073567", 1500),
    ]
    grid = Smartmeter()
    event = asyncio.Event()
    for i in inverters:
        i.event = event
    grid.event = event
    while True:
        #await event.wait()
        #event.clear()
        await asyncio.sleep(10)
        limit(inverters, grid)


def main():
    #mqtt.load()
    #try:
    asyncio.run(main_async())
    #finally:
        #mqtt.save()

if __name__ == "__main__":
    main()
