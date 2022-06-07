# Better IPC

<a href="https://pypi.org/project/better-ipc/" target="_blank"><img src="https://img.shields.io/pypi/v/better-ipc"></a>
<img src="https://img.shields.io/pypi/pyversions/better-ipc">
<img src="https://img.shields.io/github/last-commit/MiroslavRosenov/better-ipc">
<img src="https://img.shields.io/github/license/MiroslavRosenov/better-ipc">
<a href="https://discord.gg/Rpg7zjFYsh" target="_blank"><img src="https://img.shields.io/discord/875005644594372638?label=discord"></a>

<img src="https://raw.githubusercontent.com/MiroslavRosenov/better-ipc/main/banner.png">

A high-performance inter-process communication library designed to work with the latest version of [discord.py](https://github.com/Rapptz/discord.py)

This library is heavily based on [discod-ext-ipc](https://github.com/Ext-Creators/discord-ext-ipc), which is no longer maintained.

# Installation
> ### Stable version
```shell
python -m pip install -U better-ipc
```
> ### Development version
```shell
python -m pip install -U git+https://github.com/MiroslavRosenov/better-ipc
```
# Support

You can join the support server [here](https://discord.gg/Rpg7zjFYsh)

# Examples

### **For best performance run both the server and the client on the same machine**

### Inside your Discord client (with decorator)
```python
import sys
import logging
import discord

from discord.ext import commands, ipc
from discord.ext.ipc.server import route
from discord.ext.ipc.errors import IPCError

class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, host="127.0.0.1", port=2300, secret_key="your_secret_key_here")
            bot.ipc.start(self)

    @commands.Cog.listener()
    async def on_ipc_ready(self):
        logging.info("Ipc is ready")
    
    @commands.Cog.listener()
    async def on_ipc_error(self, endpoint: str, error: IPCError):
        logging.error(endpoint, "raised", error, file=sys.stderr)
    
    @route
    async def get_user_data(self, data):
        user = self.bot.get_user(data.user_id)
        return user._to_minimal_user_json() # THE OUTPUT MUST BE JSON SERIALIZABLE!

async def setup(bot):
    await bot.add_cog(Routes(bot))
```

### Inside your Discord client (with manual endpoint register)
```python
import sys
import logging
import discord

from discord.ext import commands, ipc
from discord.ext.ipc.server import route
from discord.ext.ipc.errors import IPCError

class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, host="127.0.0.1", port=2300, secret_key="your_secret_key_here")
            bot.ipc.start(self)
        for name, function in inspect.getmembers(self):
            if name.startswith("get_"): # ATTENTION: Every function that stats with `get_` will be registered as endpoint
                bot.ipc.endpoints[name] = function
    
    @commands.Cog.listener()
    async def on_ipc_ready(self):
        logging.info("Ipc is ready")
    
    @commands.Cog.listener()
    async def on_ipc_error(self, endpoint: str, error: IPCError):
        logging.error(endpoint, "raised", error, file=sys.stderr)

    async def get_user_data(self, data):
        user = self.bot.get_user(data.user_id)
        return user._to_minimal_user_json() # THE OUTPUT MUST BE JSON SERIALIZABLE!

async def setup(bot):
    await bot.add_cog(Routes(bot))
```

### Inside your web application
```python
from quart import Quart
from discord.ext.ipc import Client

app = Quart(__name__)
IPC = Client(
    host="127.0.0.1", 
    port=2300, 
    secret_key="your_secret_key_here"
) # These params must be the same as the ones in the client

@app.route('/')
async def main():
    return await app.ipc.request("get_user_data", user_id=383946213629624322)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        app.ipc = loop.run_until_complete(IPC.start(loop=loop)) # `Client.start()` returns new Client instance or None if it fails to start
        app.run(loop=loop)
    finally:
        loop.run_until_complete(app.ipc.close()) # Closes the session, doesn't close the loop
        loop.close()
```