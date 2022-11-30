from __future__ import annotations

import logging
import json
import uuid

from typing import Optional, Union, Any, Dict
from websockets.client import connect, WebSocketClientProtocol 
from .objects import ServerResponse

class Client:
    """
    The client that connects to a Server and sends requests to it

    Parameters:
    ----------
    host: `str`
        The address for the server (the default host is 127.0.0.1 and you don't wanna change this in most cases).
    secret_key: `str`
        This string will be used as authentication password while making requests.
    standard_port: `int`
        The port to run the standard server (the default is 1025).
    multicast_port: `int`
        The port to run the multicasting server (the default is 20000).
    do_multicast: `bool`
        Should the client perform standard or multicast connection (this is enable by default)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        secret_key: Union[str, None] = None,
        standard_port: int = 1025,
        multicast_port: int = 20000,
        do_multicast: bool = True
    ) -> None:
        self.host = host
        self.standard_port = standard_port
        self.secret_key = secret_key
        self.multicast_port = multicast_port
        self.do_multicast = do_multicast

        self.id = uuid.uuid4()
        self.logger = logging.getLogger(__name__)
        self.connection: Optional[WebSocketClientProtocol] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} standard_port={self.standard_port!r} multicast_port={self.multicast_port!r} do_multicast={self.do_multicast}>"

    @property
    def url(self) -> str:
        if self.do_multicast:
            return f"ws://{self.host}:{self.multicast_port}"
        return f"ws://{self.host}:{self.standard_port}"

    async def request(self, endpoint: str, **kwargs: Any) -> ServerResponse:
        """|coro|
        
        Makes a request to the server URL.

        ----------
        endpoint: `str`
            The endpoint to request on the server
        **kwargs: `Any`
            The data for the endpoint
        """
        
        if not self.connection:
            self.connection = await connect(self.url, extra_headers={"ID": str(self.id)})
        
        await self.connection.send(json.dumps({
            "endpoint": endpoint,
            "secret": str(self.secret_key),
            "kwargs": {
                **kwargs
            },
        }))

        return ServerResponse(await self.connection.recv())
    
