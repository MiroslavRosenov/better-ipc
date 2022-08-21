import discord
from discord.ext import commands, ipc

class MyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()

        super().__init__(
            command_prefix="$.",
            intents=intents,
        )

        self.ipc = ipc.Server(self, secret_key="🐼")

    async def setup_hook(self) -> None:
        await self.load_extension("cog")
