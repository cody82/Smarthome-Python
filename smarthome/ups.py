import asyncio
import subprocess

def get_ups_charge():
    process = subprocess.Popen(
        [
            "upsc",
            "eaton",
            "battery.charge"
        ],
        stdout=subprocess.PIPE,
        shell=False,
    )

    out = process.stdout.readline().decode().strip()
    return int(out)


async def get_ups_charge_async():
    process = await asyncio.create_subprocess_exec("upsc", "eaton", "battery.charge", stdout=asyncio.subprocess.PIPE)
    out = (await process.stdout.readline()).decode().strip()
    await process.wait()
    return int(out)


def get_ups_status():
    process = subprocess.Popen(
        [
            "upsc",
            "eaton",
            "ups.status"
        ],
        stdout=subprocess.PIPE,
        shell=False,
    )

    out = process.stdout.readline().decode().strip()
    return out

async def get_ups_status_async():
    process = await asyncio.create_subprocess_exec("upsc", "eaton", "ups.status", stdout=asyncio.subprocess.PIPE)
    out = (await process.stdout.readline()).decode().strip()
    await process.wait()
    return out

if __name__ == '__main__':
    ret = asyncio.run(get_ups_charge_async())
    print(ret)
    ret = asyncio.run(get_ups_status_async())
    print(ret)