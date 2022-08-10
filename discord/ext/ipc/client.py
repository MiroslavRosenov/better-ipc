from __future__ import annotations

import asyncio
import logging

from discord.ext.ipc.errors import *

from typing import (
    Optional, 
    Union, 
    Any
)

from aiohttp import (
    ClientWebSocketResponse, 
    ClientConnectorError,
    ClientSession,
    WSCloseCode,
    WSMsgType,
)

log = logging.getLogger(__name__)

class Client:
    """|class|
    
    Handles webserver side requests to the bot process.

    Parameters
    ----------
    host: str
        The IP or host of the IPC server, defaults to `127.0.0.1`
    port: int
        The port of the IPC server. Defaults to 1025.
    secret_key: Union[str, bytes]
        The secret key for your IPC server. Must match the server secret_key or requests will not go ahead, defaults to None
    """
    lock = None
    loop = None
    logger = None
    session = None
    multicast = None
    closed = False
    started = False

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1025,
        # multicast_port: int = 20000,
        secret_key: Union[str, bytes, None] = None,
    ) -> None:
        self.host = host
        self.port = port
        # self.multicast_port = multicast_port
        self.secret_key = secret_key

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    async def init_sock(self) -> ClientWebSocketResponse:
        """|coro|

        Attempts to connect to the server

        Returns
        -------
        :class: `~aiohttp.ClientWebSocketResponse`
            The websocket connection to the server
        """
        self.logger.debug("Initiating WebSocket connection")

        #TODO: multicast
        # if not self.port:
        #     self.logger.debug("No port was provided - initiating multicast connection at %s.", self.url,)
        #     self.multicast = await self.session.ws_connect(self.url, autoping=False)

        #     payload = {
        #         "connect": True, 
        #         "headers": {"Authorization": self.secret_key}
        #     }
        #     self.logger.debug("Multicast Server < %r", payload)

        #     await self.multicast.send_json(payload)
        #     recv = await self.multicast.receive()

        #     self.logger.debug("Multicast server response: %r", recv)

        #     if recv.type in (WSMsgType.CLOSE, WSMsgType.CLOSED):
        #         self.logger.error("WebSocket connection unexpectedly closed. Multicast Server is unreachable.")
        #         raise NotConnected("Multicast server connection failed.")

        #     port_data = recv.json()
        #     self.port = port_data["port"]

        self.logger.debug("Client connected to %s", self.url)
        return await self.session.ws_connect(self.url, autoping=False, autoclose=False)

    async def retry(
        self,
        endpoint: str,
        **kwargs: Any,
    ) -> WSCloseCode:
        websocket = await self.init_sock()

        payload = {
            "endpoint": endpoint,
            "data": kwargs,
            "headers": {"Authorization": self.secret_key},
        }
        try:
            await websocket.send_json(payload)
        except Exception as e:
            self.logger.error("Failed to send payload", exc_info=e)
            return WSCloseCode.INTERNAL_ERROR
        else:
            await websocket.close(code=WSCloseCode.OK)
            return WSCloseCode.OK

    async def request(
        self,
        endpoint: str,
        **kwargs: Any,
    ) -> Optional[Any]:
        """|coro|

        Make a request to the IPC server process.

        Parameters
        ----------
        endpoint: `str`
            The endpoint to request on the server
        **kwargs
            The data to send to the endpoint
        """
        if not self.started:
            raise IPCError("Session not started yet!")

        if self.closed:
            raise IPCError("Session closed!")

        self.logger.debug("Sending request to %r with %r", endpoint, kwargs)
        websocket = await self.init_sock()
        
        payload = {
            "endpoint": endpoint,
            "data": kwargs,
            "headers": {"Authorization": self.secret_key},
        }

        self.logger.debug("Sending playload: %r", payload)

        try:
            await websocket.send_json(payload)
        except ConnectionResetError:
            self.logger.error("Cannot write to closing transport, restarting the connection in 3 seconds. (Could be raised if the client is on different machine that the server)")
            await websocket.close(code=WSCloseCode.INTERNAL_ERROR)
            
            await self.close()
            await self.start(self.loop, self.logger)

            return await self.request(endpoint, **kwargs)

        recv = await websocket.receive()

        self.logger.debug("Receiving response: %r", recv)

        if recv.type is WSMsgType.CLOSED:
            self.logger.error("WebSocket connection unexpectedly closed, attempting to retry in 3 seconds.")
            await asyncio.sleep(3)
            if await self.retry(endpoint, **kwargs) == WSCloseCode.INTERNAL_ERROR:
                self.logger.error("Could not do perform the rquest after reattempt")
        
        elif recv.type is WSMsgType.PING:
            self.logger.debug("Received request to PING")
            await websocket.ping()
            await self.retry(endpoint, **kwargs)

        elif recv.type is WSMsgType.PONG:
            self.logger.debug("Received PONG")
            await self.retry(endpoint, **kwargs)

        elif recv.type is WSMsgType.ERROR:
            self.logger.error("Received WSMsgType of ERROR, intead of TEXT/BYTES!")

        else:
            await websocket.close()
            data = recv.json()
            if data["code"] != 200:
                self.logger.warning("Received code %r insted of usual 200", data["code"])
            return data

    async def start(
        self, 
        loop: Optional[asyncio.AbstractEventLoop] = None,
        logger: Optional[logging.Logger] = None,
    ) -> Client:
        """|coro|

        Starts the IPC session

        Parameters
        ----------
        loop: `asyncio.AbstractEventLoop`
            Asyncio loop to create the server in, if None, take default one.
            If specified it is the caller's responsibility to close and cleanup the loop.
        logger: `logging.Logger`
            A custom logger for all event. Default on is `discord.ext.ipc`
        """
        self.loop = loop or asyncio.get_running_loop()
        self.logger = logger or log
        self.session = ClientSession()

        try:
            connection = await self.session.ws_connect(self.url, autoping=False)
        except ClientConnectorError as e:
            self.logger.critical(f"Failed to start the IPC, connection to {self.url!r} has failed!", exc_info=e)
            raise RuntimeError(f"Failed to start the IPC, connection to {self.url!r} has failed!")
        except Exception as e:
            self.logger.critical("Failed to start the IPC, unexpected error occured!", exc_info=e)
            raise RuntimeError(f"Failed to start the IPC, unexpected error occured!")
        else:
            await connection.close()
            self.closed = False
            self.started = True
            return self
    
    async def ping(
            self,
            loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> Client:
        self.loop = loop or asyncio.get_running_loop()
        if self.session:
            return True
        session = ClientSession()
        try:
            connection = await session.ws_connect(self.url, autoping=False)
        except ClientConnectorError:
            await session.close()
            return False
        except Exception:
            await session.close()
            return False
        else:
            await session.close()
            await connection.close()
            return True
    
    async def close(self) -> None:
        """|coro|

        Stops the IPC session
        """
        if self.session:
            await self.session.close()
        self.closed = True
