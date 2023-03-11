import asyncio
import asyncpg
import paho.mqtt.client as mqtt
import logging
from . import config
import threading
from dateutil import tz
from zoneinfo import ZoneInfo
from datetime import datetime
from datetime import timedelta
from datetime import date
from dataclasses import dataclass
from typing import List
from statistics import mean

loop = asyncio.get_event_loop()

@dataclass
class OilState:
    state: bool
    duration: timedelta
    start: datetime
    end: datetime

oil_efficiency = 0.85
oil_price = 1.5
#oil_price = 1.2
electric_price = 0.25
#electric_price = 0.4

def duration_to_oil(duration: timedelta):
    return duration.total_seconds() / 3600.0 * 2.1 #liters per hour

def liter_to_euro(liter: float):
    return round(liter * oil_price, 2)

def duration_to_energy(duration: timedelta):
    return duration.total_seconds() / 3600.0 * 21.0 * oil_efficiency#kW

def duration_to_duty(duration: timedelta, total: timedelta):
    return duration / total

@dataclass
class Day:
    oil_duration: timedelta
    climate_energy: float
    temperature: float
    temperature_min: float
    temperature_max: float

    def oil_duty(self):
        return int(round((self.oil_duration / timedelta(days=1)) * 100,0))

    def oil_euro(self):
        return round(liter_to_euro(self.oil_liter()),2)

    def oil_liter(self):
        return duration_to_oil(self.oil_duration)

    def oil_power(self):
        return self.oil_duration / timedelta(days=1) * 21.0 * oil_efficiency

    def oil_energy(self):
        return duration_to_energy(self.oil_duration)

    def climate_euro(self):
        return round(self.climate_energy * electric_price,2)

    def efficiency(self):
        return (18.0 - self.temperature) / self.total()
    
    COP = [
        (-15, 2.0),
        (-7, 3.1),
        (2, 4.8),
        (7, 6.2),
        (12, 7),
    ]
    def cop(self):
        if self.temperature < self.COP[0][0]:
            return 3
        if self.temperature > self.COP[-1][0]:
            return self.COP[-1][1]
        for i in range(len(self.COP) - 1):
            if self.temperature < self.COP[i+1][0]:
                alpha = (self.temperature - self.COP[i][0]) / (self.COP[i + 1][0] - self.COP[i][0])
                return (alpha * self.COP[i + 1][1]) + ((1-alpha) * self.COP[i][1])
    def climate_heat(self):
        return self.cop() * self.climate_energy

    def total(self):
        return round((self.oil_euro() + self.climate_euro()),2)

    def total_heat_energy(self):
        return round(self.oil_energy() + self.climate_energy * self.cop(),1)
    
    def __repr__(self) -> str:
        return f"T: {round(self.temperature_min,1)} {round(self.temperature,1)} {round(self.temperature_max,1)}°C\tÖl: {self.oil_minutes()}min\t{round(self.oil_liter(),1)}L\t{self.oil_duty()}%\t{round(self.oil_power(),1)}kW\t{round(self.oil_energy(),1)}kWh\t{self.oil_euro()}€\tKlima: COP={round(self.cop(),1)}\t{round(self.climate_energy,1)}kWh\t{self.climate_euro()}€\t{round(self.climate_heat(),1)}kWh\tTotal: {self.total()}€ {self.total_heat_energy()}kWh"

    def oil_minutes(self):
        return int(round(self.oil_duration.total_seconds()/60,0))

start = datetime(2022, 11, 1)
end = datetime.now()+timedelta(days=1)

async def avg_temp():
    print("Außen:")
    result = await pg.fetch(f"SELECT DATE_TRUNC('day', time) AS day, AVG((msg::json->>'temperature')::numeric) AS temperature FROM mqtt WHERE topic = 'zigbee2mqtt/Draussen/Garage/Thermometer/nr1' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' GROUP BY 1 ORDER BY 1")
    
    for row in result:
        print(f"{row['day'].astimezone(ZoneInfo('localtime')).date()}\t{round(row['temperature'],1)}°C")

    print("Vorlauf:")
    result = await pg.fetch(f"SELECT DATE_TRUNC('day', time) AS day, AVG((msg::json->'DS18B20-2'->>'Temperature')::numeric) AS temperature FROM mqtt WHERE topic = 'tele/smartmeter/SENSOR' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' GROUP BY 1 ORDER BY 1")

    for row in result:
        print(f"{row['day'].astimezone(ZoneInfo('localtime')).date()}\t{round(row['temperature'],1)}°C")

async def strom():
    
    start = datetime(2022, 11, 29)
    end = datetime(2022, 11, 30)

    result = await pg.fetch(f"SELECT time, msg, (msg::json->'MT681'->>'Total_in')::numeric AS energy FROM mqtt WHERE topic = 'tele/smartmeter/SENSOR' AND time >= TIMESTAMP '{start}' ORDER BY time LIMIT 1")
    energy1 = result[0]["energy"]
    result = await pg.fetch(f"SELECT time, msg, (msg::json->'MT681'->>'Total_in')::numeric AS energy FROM mqtt WHERE topic = 'tele/smartmeter/SENSOR' AND time >= TIMESTAMP '{end}' ORDER BY time LIMIT 1")
    energy2 = result[0]["energy"]
    print(energy2-energy1)


async def strom2():
    result = await pg.fetch(f"SELECT DATE_TRUNC('day', time) AS day, MIN((msg::json->'MT681'->>'Total_in')::numeric) AS energy_min, MAX((msg::json->'MT681'->>'Total_in')::numeric) AS energy_max FROM mqtt WHERE topic = 'tele/smartmeter/SENSOR' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' GROUP BY 1 ORDER BY 1")

    print("Strom:")
    for row in result:
        print(f"{row['day'].astimezone(ZoneInfo('localtime')).date()}\t{round(row['energy_max'] - row['energy_min'],3)}kWh")

async def strom_klima():
    result = await pg.fetch(f"SELECT DATE_TRUNC('day', time) AS day, MIN(msg::numeric) AS energy_min, MAX(msg::numeric) AS energy_max FROM mqtt WHERE topic = 'shellies/shellyem-klima/emeter/0/total' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' GROUP BY 1 ORDER BY 1")

    #print("Klima:")
    #for row in result:
    #    print(f"{row['day'].astimezone(ZoneInfo('localtime')).date()}\t{round((row['energy_max'] - row['energy_min'])/1000,3)}kWh")

    return [(row['day'].astimezone(ZoneInfo('localtime')).date(), row['energy_max'] - row['energy_min']) for row in result]

async def temp_outside():
    result = await pg.fetch(f"SELECT DATE_TRUNC('day', time) AS day, AVG((msg::json->>'temperature')::numeric) AS temperature, MIN((msg::json->>'temperature')::numeric) AS temperature_min, MAX((msg::json->>'temperature')::numeric) AS temperature_max FROM mqtt WHERE topic = 'zigbee2mqtt/Draussen/Garage/Thermometer/nr1' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' GROUP BY 1 ORDER BY 1")
    
    result = [(row['day'].astimezone(ZoneInfo('localtime')).date(), row['temperature'], row['temperature_min'], row['temperature_max']) for row in result]
    
    result2 = await pg.fetch(f"SELECT DATE_TRUNC('day', time) AS day, AVG((msg::json->>'temperature')::numeric) AS temperature, MIN((msg::json->>'temperature')::numeric) AS temperature_min, MAX((msg::json->>'temperature')::numeric) AS temperature_max FROM mqtt WHERE topic = 'zigbee2mqtt/Draussen/Klimaanlage/Temperatur' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' GROUP BY 1 ORDER BY 1")
    result2 = [(row['day'].astimezone(ZoneInfo('localtime')).date(), row['temperature'], row['temperature_min'], row['temperature_max']) for row in result2]
    
    print(result2[0])
    return result

async def run():
    global pg
    pg = await asyncpg.connect(user=config.POSTGRES_USER, password=config.POSTGRES_PASSWORD,
        database=config.POSTGRES_DATABASE, host=config.POSTGRES_HOST)

    #await strom2()
    klima = await strom_klima()
    temp = await temp_outside()
    #await avg_temp()

    #now = start
    result = await pg.fetch(f"SELECT time, msg FROM mqtt WHERE topic = 'shellies/shellyem-heizung/emeter/0/power' AND time >= TIMESTAMP '{start}' AND time < TIMESTAMP '{end}' ORDER BY time")
    last_change = None
    last_state = None
    states: List[OilState] = []
    #print(f"Rows: {len(result)}")
    for row in result:
        power = float(row["msg"])
        state = power > 145
        time = row["time"]

        if last_state != state:
            if last_change is not None:
                duration = time - last_change
                if last_state and duration > timedelta(minutes=1):
                    states.append(OilState(last_state, duration, last_change.astimezone(ZoneInfo('localtime')), time.astimezone(ZoneInfo('localtime'))))
                    #print("on: " if last_state else "off:", duration, "(", last_change.astimezone(ZoneInfo('localtime')), "->", time.astimezone(ZoneInfo('localtime')), ")")
            last_change = time
        if last_change is None:
            last_change = time
        last_state = state

    daily: List[OilState] = [OilState(True, timedelta(0), start, start)]
    for s in states:
        day_start = datetime(s.start.year, s.start.month, s.start.day)
        day_end = datetime(s.end.year, s.end.month, s.end.day)

        current = daily[-1]

        if day_start == day_end:
            if current.start == day_start:
                current.duration += s.duration
            else:
                daily.append(OilState(True, s.duration, day_start, day_start))
        else:
            duration1 = day_end - s.start
            duration2 = s.end - day_end
            if current.start == day_start:
                current.duration += duration1
            else:
                daily.append(OilState(True, duration1, day_start, day_start))
            daily.append(OilState(True, duration2, day_end, day_end))

    #for s in states:
    #    print(f"{s.start} {s.duration}")

    #for d in daily:
    #    print(f"{d.start.date()}\t{str(d.duration).split('.')[0]}\t{int(d.duration.total_seconds() / 3600.0 /24.0*100)}%\t{round(duration_to_oil(d.duration),2)}L\t{liter_to_euro(duration_to_oil(d.duration))}€")
    #total_duration = sum([s.duration for s in states], start=timedelta())
    #oil = duration_to_oil(total_duration)
    #print(f"On duration: {total_duration}")
    #print(f"Oil: {round(oil,1)}L")
    #print(f"Energy: {round(duration_to_energy(total_duration),1)}kWh")
    #print(f"Money: {liter_to_euro(oil)}€")
    
    days = dict([(d.start.date(), Day(d.duration,0,0,0,0)) for d in daily])
    for d in klima:
        if d[0] in days:
            days[d[0]].climate_energy = float(d[1]) / 1000
        else:
            days[d[0]] = Day(timedelta(seconds=0), float(d[1])/1000, 0,0,0)
    for t in temp:
        if t[0] in days:
            days[t[0]].temperature = float(t[1])
            days[t[0]].temperature_min = float(t[2])
            days[t[0]].temperature_max = float(t[3])
        else:
            days[t[0]] = Day(timedelta(seconds=0), 0, float(t[1]),float(t[2]),float(t[3]))

    for k, v in days.items():
        print(k, v)
    
    cop = sum([x.climate_heat() for x in days.values()]) / sum([x.climate_energy for x in days.values()])
    
    print(f"COP AVG: {cop}")
    
    return days

def main():
    global client, loop
    loop.run_until_complete(run())


if __name__ == "__main__":
    main()
