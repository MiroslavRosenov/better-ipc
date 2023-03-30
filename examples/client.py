from quart import Quart
from discord.ext.ipc.client import Client

app = Quart(__name__)
ipc = Client(secret_key="🐼")

@app.route("/")
async def main():
    resp = await ipc.request("get_user", user_id=383946213629624322)
    return str(resp.response) # type: ignore

if __name__ == '__main__':
    app.run()