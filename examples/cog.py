from typing import Dict
from discord.ext import commands, ipc
from discord.ext.ipc.server import route
from discord.ext.ipc.objects import ClientPayload

class Routes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "ipc"):
            bot.ipc = ipc.Server(self.bot, secret_key="🐼")
    
    @commands.Cog.listener()
    async def on_cog_load(self) -> None:
        await self.bot.ipc.start()

    @commands.Cog.listener()
    async def on_cog_unload(self) -> None:
        await self.bot.ipc.stop()
    
    @route()
    async def get_user_data(self, data: ClientPayload) -> Dict:
        user = self.bot.get_user(data.user_id)
        return user._to_minimal_user_json()