from quart import Quart
from discord.ext.ipc import Client

app = Quart(__name__)
ipc = Client(secret_key="🐼")

@app.route('/')
async def main():
    async with ipc as conn:
        return await conn.request("get_user_data", user_id=383946213629624322)

if __name__ == '__main__':
    app.run()