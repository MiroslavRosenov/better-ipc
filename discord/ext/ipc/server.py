from __future__ import annotations
import asyncio

import logging
import json
import contextlib
import inspect

from discord.ext.commands import Bot, Cog
from typing import TYPE_CHECKING, Optional, Callable, ClassVar, TypeVar, Union, Type, Awaitable, Tuple, Any, Dict

from websockets.exceptions import ConnectionClosedError, ConnectionClosed
from websockets.server import WebSocketServerProtocol, WebSocketServer, serve

from .errors import InvalidReturn, NoEndpointFound, MulticastFailure, ServerAlreadyStarted
from .objects import ClientPayload


if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeAlias
    
    P = ParamSpec("P")
    T = TypeVar("T")
    
    RouteFunc: TypeAlias = Callable[P, T]
    Handler = Callable[[WebSocketServerProtocol], Awaitable[Any]]

class Server:
    """
    The inter-process communication server that is connected with the bot.

    Parameters:
    ----------
    bot: `Bot`
        The bot instance.
    host: `str`
        The address for the server (the default host is 127.0.0.1 and you don't wanna change this in most cases).
    secret_key: `str`
        This string will be used as authentication password while taking requests.
    standard_port: `int`
        The port to run the standard server (the default is 1025).
    multicast_port: `int`
        The port to run the multicasting server (the default is 20000).
    do_multicast: `bool`
        Should the multicasting be allowed (this is enabled by default).
    logger: `Logger`
        You can specify the logger for logs related to the lib (the default is discord.ext.ipc.server)
    """

    endpoints: ClassVar[Dict[str, Tuple[RouteFunc, Type[ClientPayload]]]] = {}

    def __init__(
        self,
        bot: Bot,
        host: str = "127.0.0.1", 
        secret_key: Union[str, None] = None, 
        standard_port: int = 1025,
        multicast_port: int = 20000,
        do_multicast: bool = True,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.bot = bot
        self.host = host
        self.secret_key = secret_key
        self.standard_port = standard_port
        self.multicast_port = multicast_port
        self.do_multicast = do_multicast

        self.logger = logger or logging.getLogger(__name__)
        self.servers: Dict[str, WebSocketServer] = {}
        self.connection: Optional[Tuple[str, WebSocketServerProtocol]] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} endpoints={len(self.endpoints)} started={self.started} standard_port={self.standard_port!r} multicast_port={self.multicast_port!r} do_multicast={self.do_multicast}>"

    def get_cls(self, func: RouteFunc) -> Union[Cog, Bot]:
        for cog in self.bot.cogs.values():
            if func.__name__ in dir(cog):
                return cog
        return self.bot

    @classmethod
    def route(cls, name: Optional[str] = None, multicast: Optional[bool] = True) -> Callable[[RouteFunc], RouteFunc]:
        """|method|

        Used to register a coroutine as an endpoint

        Parameters
        ----------
        name: :class:`str`
            The endpoint name. If not provided the method name will be used.
        multicast :class:`bool`
            Should the enpoint be avaiable for multicast or not. If this is set to False only standard connection can access it.
        """
        def decorator(func: RouteFunc) -> RouteFunc:
            payload = ClientPayload
            for annotation in func.__annotations__.values():
                if inspect.isclass(annotation) and issubclass(annotation, ClientPayload):
                    payload = annotation
                    break

            func.__multicast__ = multicast

            cls.endpoints[name or func.__name__] = (func, payload)
            return func
        return decorator

    @property
    def started(self) -> bool:
        return len(self.servers) > 0

    def is_secure(self, message: Union[str, bytes]) -> bool:
        data: Dict[str, Any] = json.loads(message)

        if (key := data.get("secret")):
            return str(key) == str(self.secret_key)
        return bool(self.secret_key is None)
    

    async def handle_request(self, websocket: WebSocketServerProtocol, message: Union[str, bytes], multucast: bool = True) -> None:
        payload: Dict[str, Union[str, int, None]] = {
            "decoding": None,
            "code": 200,
            "response": None
        }
        
        if not self.is_secure(message):
            payload["code"] = 403
            payload["error"] = "Unauthorized"
            payload["error_details"] = "You're trying to connect with an invalid secret key!"
            return await websocket.send(json.dumps(payload))

        data: Dict[str, Any] = json.loads(message)
        endpoint: str = data["endpoint"]

        if not (coro := self.endpoints.get(endpoint)):
            payload["code"] = 404
            payload["error"] = "Unknown endpoint!"
            payload["error_details"] = "The route that you're trying to call doesn't exist!"
            self.bot.dispatch("ipc_error", None, NoEndpointFound(endpoint, "The route that you're trying to call doesn't exist!"))
            return await websocket.send(json.dumps(payload))
        
        try:
            func = coro[0]

            if multucast and not func.__getattribute__("__multicast__"):
                payload["code"] = 500
                payload["error"] = "The requested route is not available for multicast connections!"
                payload["error_details"] = "This route can only be called with standart client!"
                self.bot.dispatch("ipc_error", endpoint, MulticastFailure(endpoint, "This route can only be called with standart client!"))
                return await websocket.send(json.dumps(payload))

            resp: Optional[Union[Dict, str]] = await func(self.get_cls(func), coro[1](data))
        except Exception as exc:
            payload["code"] = 500
            payload["error"] = "Unexpected error occurred while calling the route!"
            payload["error_details"] = str(exc)

            self.bot.dispatch("ipc_error", endpoint, exc)
            return await websocket.send(json.dumps(payload))
        
        if resp and not (isinstance(resp, Dict) or isinstance(resp, str)):
            payload["error"] = f"Expected type Dict or string as response, got {resp.__class__.__name__!r} instead!"
            payload["code"] = 500
            self.bot.dispatch("ipc_error", endpoint, InvalidReturn(endpoint, f"Expected type Dict or string as response, got {resp.__class__.__name__} instead!"))
            return await websocket.send(json.dumps(payload))
        
        if isinstance(resp, Dict):
            payload["decoding"] = "JSON"
            payload["response"] = json.dumps(resp)
        else:
            payload["response"] = resp
        
        return await websocket.send(json.dumps(payload))

    async def create_server(self, name: str, port: int, ws_handler: Handler) -> None:
        if name in self.servers:
            raise ServerAlreadyStarted(name, f"{name!r} is already started!")
        
        self.servers[name] = await serve(ws_handler, self.host, port)
        self.logger.debug(f"{name.title()} is ready for use!")

    async def standart_handler(self, websocket: WebSocketServerProtocol) -> None:
        id = websocket.request_headers["ID"]
        
        try:
            if self.connection:
                if not self.connection[0] == id:
                    resp = json.dumps({
                        "error": "Connection already reserved!",
                        "details": self.connection[0],
                        "code": 422
                    })
                    
                    return await websocket.send(resp)
            else:
                self.logger.debug(f"New connection created: {id}")
                self.connection = id, websocket
        
            async for message in websocket:
                with contextlib.suppress(ConnectionClosedError, ConnectionClosed):
                    await asyncio.create_task(self.handle_request(websocket, message, False))
            
        except (ConnectionClosedError, ConnectionClosed):
            self.logger.debug(f"Connection closed by the client: {self.connection[0]}") # type: ignore
            self.connection = None
    
    async def multicast_handler(self, websocket: WebSocketServerProtocol) -> None:
        with contextlib.suppress(ConnectionClosedError, ConnectionClosed):
            async for message in websocket:
                await asyncio.create_task(self.handle_request(websocket, message, True))

    async def start(self) -> None:
        """|coro|
        
        Starts all necessary processes for the servers and runners to work properly

        """
        await self.create_server("standard", self.standard_port, self.standart_handler)

        if self.do_multicast:
            await self.create_server("mutlicast", self.multicast_port, self.multicast_handler)

        self.bot.dispatch("ipc_ready")
    
    async def stop(self) -> None:
        """|coro|

        Takes care of shutting down the server(s)

        """
        for name, server in self.servers.items():
            server.close()
            await server.wait_closed()
            self.logger.info(f"{name!r} server has been stopped!")
        
        self.servers = {}
