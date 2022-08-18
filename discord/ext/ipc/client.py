from __future__ import annotations

import asyncio
import logging
import time

from .errors import *

from typing import (
    Dict,
    Optional, 
    Union, 
    Any
)

from aiohttp import (
    ClientConnectorError,
    ClientConnectionError,
    ClientSession,
    WSCloseCode,
    WSMsgType,
)

class Client:
    """|class|
    
    Handles the web application side requests to the bot process 
    (intented to work as asynchronous context manager)

    Parameters:
    ----------
    host: :str:`str`
        The IP adress that hosts the server (the default is `127.0.0.1`).
    secret_key: :str:`str`
        The authentication that is used when creating the server (the default is `None`).
    standart_port: :str:`int`
        The port for the standart server (the default is `1025`)
    multicast_port: :int:`int`
        The port for the multicasting server (the default is `20000`)
    do_multicast: :bool:`bool`
        Should the client perform standart or multicast connection (the default is `True`)
        
        Please keep in mind that multicast clients cannot request routes that are only allowed for standart connections!
    """
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        host: str = "127.0.0.1",
        secret_key: Union[str, None] = None,
        standart_port: int = 1025,
        multicast_port: int = 20000,
        do_multicast: bool = True
    ) -> None:
        self.host = host
        self.standart_port = standart_port
        self.secret_key = secret_key
        self.multicast_port = multicast_port
        self.do_multicast = do_multicast

    @property
    def url(self) -> str:
        if self.do_multicast:
            return f"ws://{self.host}:{self.multicast_port}"
        return f"ws://{self.host}:{self.standart_port}"

    async def __aenter__(self) -> Client:
        self.session = ClientSession()
        await self.__init_socket__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session.close()
        await self.ws.close()

        self.session = None
        self.ws = None

    async def __init_socket__(self) -> None:
        self.logger.debug("Initiating websocket connection")

        try:
            self.ws = await self.session.ws_connect(self.url, autoping=False, autoclose=False)
        except (ClientConnectorError, ClientConnectionError):
            raise NotConnected("WebSocket connection failed, the server is unreachable.")

        if await self.is_alive():
            self.logger.debug(f"Client connected to {self.url!r}")
        else:
            await self.session.close()
            raise NotConnected("WebSocket connection failed, the server is unreachable.")

    async def __retry__(self, endpoint: str, **kwargs: Any) -> WSCloseCode:
        payload = {
            "endpoint": endpoint,
            "data": kwargs,
            "headers": {"Authorization": self.secret_key},
        }
        try:
            await self.ws.send_json(payload)
        except Exception as e:
            self.logger.error("Failed to send payload", exc_info=e)
            return WSCloseCode.INTERNAL_ERROR
        else:
            return WSCloseCode.OK

    async def is_alive(self) -> bool:
        """|coro|

        Performs a test to the connetion state
        
        """
        payload = {
            "connection_test": True
        }

        start = time.perf_counter()
        await self.ws.send_json(payload)
        r = await self.ws.receive()
        self.logger.debug(f"Connection to websocket took {time.perf_counter() - start:,} ms")
        
        if r.type in (WSMsgType.CLOSE, WSMsgType.CLOSED):
            return False
        return True

    async def request(self, endpoint: str, **kwargs: Any) -> Optional[Dict]:
        """|coro|

        Make a request to the IPC server process.

        Parameters
        ----------
        endpoint: `str`
            The endpoint to request on the server
        **kwargs
            The data to send to the endpoint
        """
        self.logger.debug(f"Sending request to {endpoint!r} with %r", kwargs)
        
        payload = {
            "endpoint": endpoint,
            "data": kwargs,
            "headers": {"Authorization": self.secret_key},
        }

        self.logger.debug("Sending playload: %r", payload)

        try:
            await self.ws.send_json(payload)
        except ConnectionResetError:
            self.logger.error("Cannot write to closing transport, restarting the connection in 3 seconds. (Could be raised if the client is on different machine that the server)")
            
            return await self.__retry__(endpoint, **kwargs)

        recv = await self.ws.receive()

        self.logger.debug("Receiving response: %r", recv)

        if recv.type is WSMsgType.CLOSED:
            self.logger.error("WebSocket connection unexpectedly closed, attempting to retry in 3 seconds.")
            await asyncio.sleep(3)

            if await self.__retry__(endpoint, **kwargs) == WSCloseCode.INTERNAL_ERROR:
                self.logger.error("Could not do perform the request after reattempt")
        
        elif recv.type is WSMsgType.ERROR:
            self.logger.error("Received WSMsgType of ERROR, instead of TEXT/BYTES!")

        else:
            data = recv.json()
            if int(data["code"]) != 200:
                self.logger.warning(f"Received code {data['code']!r} insted of usual 200")
            return data
