from typing import Dict
from discord.ext import commands
from discord.ext.ipc.server import Server
from discord.ext.ipc.objects import ClientPayload

class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = Server(self.bot, secret_key="🐼") # type: ignore
    
    async def cog_load(self) -> None:
        await self.bot.ipc.start() # type: ignore

    async def cog_unload(self) -> None:
        await self.bot.ipc.stop() # type: ignore
        del self.bot.ipc # type: ignore
    
    @Server.route()
    async def get_user_data(self, data: ClientPayload) -> Dict:
        user = self.bot.get_user(data.user_id)
        return user._to_minimal_user_json() # type: ignore