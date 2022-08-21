import aioconsole

def test_func():
    pass

async def start():
    while True:
        line = await aioconsole.ainput('>_ ')
        try:
            print(eval(line))
        except Exception as e:
            print(e)