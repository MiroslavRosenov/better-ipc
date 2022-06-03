![](https://raw.githubusercontent.com/MiroslavRosenov/discord-ext-ipc/main/banner.png)

# Installation
```shell
python -m pip install -U git+https://github.com/MiroslavRosenov/discord-ext-ipc
```

## Inside your discord client
```python
import logging
import discord

from discord.ext import commands, ipc
from discord.ext.ipc.Server import route
from discord.ext.ipc.errors import IPCError

class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, host="127.0.0.1", port=2300, secret_key="your_secret_key_here")
            bot.ipc.start()

    @commands.Cog.listener()
    async def on_ipc_ready(self):
        logging.info("Ipc is ready.")

    @commands.Cog.listener()
    async def on_ipc_error(self, endpoint: str, error: IPCError):
        logging.error(endpoint, "raised", error, file=sys.stderr)
    
    @route()
    async def get_user_data(self, data):
        user = self.bot.get_user(data.user_id)
        return user._to_minimal_user_json() # THE OUTPUT MUST BE JSON SERIALIZABLE!

async def setup(bot):
    await bot.add_cog(Routes(bot))
```

## Inside your web application
```python
from discord.ext import ipc
from quart import Quart

app = Quart(__name__)
IPC = ipc.Client(
    host="127.0.0.1", 
    port=2300, 
    secret_key="your_secret_key_here"
) # These params must be the same as the ones in the client

@app.route('/')
async def main():
    data = await ipc_client.request("get_user_data", user_id=383946213629624322)
    return str(data)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        app.ipc = loop.run_until_complete(IPC.start(loop=loop))
        app.run(loop=loop)
    finally:
        loop.run_until_complete(app.ipc.close())
        loop.close()
```
