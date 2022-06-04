from __future__ import annotations
import asyncio
import logging
import typing
import aiohttp

from typing import Optional, Union, Any
from aiohttp import ClientWebSocketResponse
from discord.ext.ipc.errors import *

log = logging.getLogger(__name__)

class Client:
    """
    |class|
    
    Handles webserver side requests to the bot process.

    Parameters
    ----------
    host: str
        The IP or host of the IPC server, defaults to `127.0.0.1`
    port: int
        The port of the IPC server. If not supplied the port will be found automatically, defaults to None
    secret_key: Union[str, bytes]
        The secret key for your IPC server. Must match the server secret_key or requests will not go ahead, defaults to None
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        multicast_port: int = 20000,
        secret_key: Union[str, bytes] = None
    ):
        """Constructor"""
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self.multicast_port = multicast_port
        self.lock = None
        self.loop = None
        self.logger = None
        self.session = None
        self.websocket = None
        self.multicast = None
        self.closed = False
        self.started = False

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port if self.port else self.multicast_port}"

    async def init_sock(self) -> ClientWebSocketResponse:
        """
        Attempts to connect to the server

        Returns
        -------
        :class: `~aiohttp.ClientWebSocketResponse`
            The websocket connection to the server
        """
        self.logger.info("Initiating WebSocket connection.")
        self.session = aiohttp.ClientSession()

        if not self.port:
            self.logger.debug("No port was provided - initiating multicast connection at %s.", self.url,)
            self.multicast = await self.session.ws_connect(self.url, autoping=False)

            payload = {"connect": True, "headers": {"Authorization": self.secret_key}}
            self.logger.debug("Multicast Server < %r", payload)

            await self.multicast.send_json(payload)
            recv = await self.multicast.receive()

            self.logger.debug("Multicast Server > %r", recv)

            if recv.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                self.logger.error("WebSocket connection unexpectedly closed. Multicast Server is unreachable.")
                raise NotConnected("Multicast server connection failed.")

            port_data = recv.json()
            self.port = port_data["port"]

        self.websocket = await self.session.ws_connect(self.url, autoping=False, autoclose=False)
        self.logger.info("Client connected to %s", self.url)

        return self.websocket

    async def request(
        self,
        endpoint: str, **kwargs
    ) -> Optional[Any]:
        """
        |coro|

        Make a request to the IPC server process.

        Parameters
        ----------
        endpoint: `str`
            The endpoint to request on the server
        **kwargs
            The data to send to the endpoint
        """
        if not self.started:
            raise RuntimeError("The IPC has not been started yet!")

        if self.closed:
            raise RuntimeError("The IPC is currently closed!")

        await self.init_sock()
        self.logger.info("Requesting IPC Server for %r with %r", endpoint, kwargs)
        
        payload = {
            "endpoint": endpoint,
            "data": kwargs,
            "headers": {"Authorization": self.secret_key},
        }

        try:
            await self.websocket.send_json(payload)
        except ConnectionResetError:
            self.logger.error("Cannot write to closing transport, attempting reconnection in 5 seconds.")
            await self.session.close()
            await asyncio.sleep(5)
            await self.init_sock()

            return await self.request(endpoint, **kwargs)

        self.logger.debug("Client > %r", payload)

        async with self.lock:
            recv = await self.websocket.receive()

        self.logger.debug("Client < %r", recv)

        if recv.type == aiohttp.WSMsgType.PING:
            self.logger.info("Received request to PING")
            await self.websocket.ping()
            return await self.request(endpoint, **kwargs)

        elif recv.type == aiohttp.WSMsgType.PONG:
            self.logger.info("Received PONG")
            return await self.request(endpoint, **kwargs)

        elif recv.type == aiohttp.WSMsgType.CLOSED:
            self.logger.error("WebSocket connection unexpectedly closed, attempting reconnection in 5 seconds.")
            await self.session.close()
            await asyncio.sleep(5)
            await self.init_sock()

            return await self.request(endpoint, **kwargs)
        
        else:
            return recv.json()

    async def start(
        self, 
        loop: Optional[asyncio.AbstractEventLoop] = None,
        logger: Optional[logging.Logger] = None
    ) -> Client:
        """
        |coro|

        Starts the IPC session

        Parameters
        ----------
        loop: `asyncio.AbstractEventLoop`
            Asyncio loop to create the server in, if None, take default one.
            If specified it is the caller's responsibility to close and cleanup the loop.
        logger: `logging.Logger`
            A custom logger for all event. Default on is `discord.ext.ipc`
        """
        if not loop:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if not logger:
            logger = log
        
        self.loop = loop
        self.logger = logger
        self.lock = asyncio.Lock()
        self.started = True

        return self
    
    async def close(self) -> None:
        """
        |coro|

        Stops the IPC session
        """
        if self.session:
            await self.session.close()
        self.closed = True
    
