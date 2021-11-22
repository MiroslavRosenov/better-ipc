## Installation
```shell
python3.9 -m pip install -U git+https://github.com/Daishiky/discord-ext-ipc
```

## Usage

# Inside a cog
```python
import inspect
import discord
from discord.ext import commands, ipc

class IpcRoutes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, secret_key="your_secret_key_here")
            bot.ipc.start()
        
        
        for n,f in inspect.getmembers(self):
            if n.startswith("get_"):
                bot.ipc.endpoints[n] = f.__call__

    @commands.Cog.listener()
    async def on_ipc_ready(self):
        """Called upon the IPC Server being ready"""
        print("Ipc is ready.")

    @commands.Cog.listener()
    async def on_ipc_error(self, endpoint, error):
        """Called upon an error being raised within an IPC route"""
        print(endpoint, "raised", error, file=sys.stderr)

    async def get_member_count(self, data):
      guild = self.bot.get_guild(data.guild_id)  # get the guild object using parsed guild_id

      return guild.member_count  # return the member count to the client

def setup(bot):
  bot.add_cog(IpcRoutes(bot))
```

# FastAPI App
```python
from discord.ext import ipc
from fastapi import FastAPI

ipc_client = ipc.Client(secret_key="your_secret_key", port=8765)

app = FastAPI

@app.route('/')
async def main():
    data = await ipc_client.request("get_member_count")
    return data

if __name__ == '__main__':
    app.run()
```
