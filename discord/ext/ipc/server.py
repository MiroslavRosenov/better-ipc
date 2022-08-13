from __future__ import annotations

import asyncio
import logging
import warnings
from typing import (
    TYPE_CHECKING, 
    Optional,
    Callable,
    ClassVar,
    TypeVar,
    Dict,
    Union,
    Type,
)
from aiohttp import WSMessage

from aiohttp.web import (
    WebSocketResponse, 
    Application,
    AppRunner,
    TCPSite,
    Request,
)
from discord.ext.commands import Bot, AutoShardedBot
from discord.ext.ipc.errors import *
from discord.ext.ipc.objects import ServerPayload

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeAlias
    
    P = ParamSpec('P')
    T = TypeVar('T')
    
    RouteFunc: TypeAlias = Callable[P, T]

log = logging.getLogger(__name__)


def route(name: Optional[str] = None) -> Callable[[RouteFunc], RouteFunc]:
    """|method|

    Used to register a coroutine as an endpoint when you have
    access to an instance of :class:`~discord.ext.ipc.Server`

    Parameters
    ----------
    name: `str`
        The endpoint name. If not provided the method name will be used.
    """
    warnings.warn(
        "This function will be deprecated later "
        "in the future. Consider using `Server.route`."
    )

    def decorator(func: RouteFunc) -> RouteFunc:
        for cls in func.__annotations__.values():
            if isinstance(cls, ServerPayload):
                payload_cls = cls
                break
        else:
            payload_cls = ServerPayload

        Server.endpoints[name or func.__name__] = (func, payload_cls)
        return func

    return decorator


class Server:
    """|class|
    
    The IPC server. Usually used on the bot process for receiving
    requests from the client.
    Attributes
    ----------
    bot: :class:`~discord.ext.commands.Bot`
        Your bot instance
    host: :str:`str`
        The host to run the IPC Server on. Defaults to `127.0.0.1`.
    port: :str:`int`
        The port to run the IPC Server on. Defaults to `1025`.
    secret_key: :str:`str`
        A secret key. Used for authentication and should be the same as
        your client's secret key.
    do_multicast: :bool:`bool`
        Turn multicasting on/off. Defaults to False
    multicast_port: :int:`int`
        The port to run the multicasting server on. Defaults to 20000
    logger: `logging.Logger`
        A custom logger for all event. Default one is `discord.ext.ipc`
    """
    endpoints: ClassVar[Dict[str, Tuple[RouteFunc, Type[ServerPayload]]]] = {}
    _runner = None
    _server = None
    _multicast_server = None

    def __init__(
        self, 
        bot: Union[Bot, AutoShardedBot], 
        host: str = "127.0.0.1", 
        port: int = 1025,
        secret_key: str = None, 
        do_multicast: bool = False,
        multicast_port: int = 20000,
        logger: logging.Logger = log,
    ) -> None:
        self.bot = bot
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self.do_multicast = do_multicast
        self.multicast_port = multicast_port
        self.logger = logger
        self.loop = bot.loop 

    def _get_parent(self, func):
        cls = func.__qualname__.strip(f".{func.__name__}")
        return self.bot.cogs.get(cls)

    def start(self) -> None:
        """
        |method|
        
        Starts the IPC server

        """
        self._server = Application()
        self._server.router.add_route("GET", "/", self.accept_request)

        if self.do_multicast:
            self._multicast_server = Application()
            self._multicast_server.router.add_route("GET", "/", self.handle_multicast)
            self.loop.create_task(self.setup(self._multicast_server, self.multicast_port))
        
        self.loop.create_task(self.setup(self._server, self.port))
        
        if self.bot.is_ready():
            self.logger.info("The IPC server is ready")
            self.bot.dispatch("ipc_ready")
        else:
            self.loop.create_task(self.wait_bot_is_ready())

    @classmethod
    def route(cls, name: Optional[str] = None) -> Callable[[RouteFunc], RouteFunc]:
        """|method|

        Used to register a coroutine as an endpoint when you have
        access to an instance of :class:`~discord.ext.ipc.Server`

        Parameters
        ----------
        name: `str`
            The endpoint name. If not provided the method name will be used.
        """
        def decorator(func: RouteFunc) -> RouteFunc:
            for cls in func.__annotations__.values():
                if isinstance(cls, ServerPayload):
                    payload_cls = cls
                    break
            else:
                payload_cls = ServerPayload

            Server.endpoints[name or func.__name__] = (func, payload_cls)
            return func
        return decorator

    async def accept_request(self, original_request: Request) -> None:
        """|coro|

        Aceepts websocket requests from the client process

        Parameters
        ----------
        request: :class:`~aiohttp.web.Request`
            The request made by the client, parsed by aiohttp.
        """
        self.logger.debug("Handing new IPC request")

        websocket = WebSocketResponse()
        await websocket.prepare(original_request)

        async for message in websocket:
            asyncio.create_task(self.process_request(websocket, message))

    async def handle_multicast(self, request: Request) -> None:
        """|coro|

        Handles websocket requests at the same time
        
        Parameters
        ----------
        request: :class:`~aiohttp.web.Request`
            The request made by the client, parsed by aiohttp.
        """
        self.loop.create_task(self.process_request(request))

    async def process_request(self, websocket: WebSocketResponse, message: WSMessage) -> None:
        """|coro|

        Processes requests by the client

        Parameters
        ----------
        websocket: :class:`~aiohttp.web.WebSocketResponse`
            The socket from the request
        message: :class:`~aiohttp.WSMessage`
            The message that was send in the request
        """
        request = message.json()

        self.logger.debug("Receiving request: %r", request)

        endpoint = request.get("endpoint")
        headers = request.get("headers")

        if not (authorization := headers.get("Authorization")):
            self.bot.dispatch("ipc_error", endpoint, IPCError("Received unauthorized request (no token provided))"))
            response = {
                "error": "Received unauthorized request (no token provided)", 
                "code": 403
            }

        elif authorization != self.secret_key:
            self.bot.dispatch("ipc_error", endpoint, IPCError("Received unauthorized request (invalid token provided)"))
            response = {
                "error": "Received unauthorized request (invalid token provided)", 
                "code": 403
            }

        if not headers or headers.get("Authorization") != self.secret_key:
            self.bot.dispatch("ipc_error", endpoint, IPCError("Received unauthorized request (Invalid or no token provided)"))
            response = {
                "error": "Received unauthorized request (invalid or no token provided).", 
                "code": 403
            }
        else:
            if not endpoint:
                self.bot.dispatch("ipc_error", endpoint, IPCError("Received invalid request (no endpoint provided)"))
                response = {
                    "error": "Received invalid request (no endpoint provided)",
                    "code": 404
                }

            elif endpoint not in self.endpoints:
                self.bot.dispatch("ipc_error", endpoint, IPCError("Received invalid request (invalid endpoint provided)"))
                response = {
                    "error": "Received invalid request (invalid endpoint provided)",
                    "code": 404
                }
            else:
                endpoint, payload_cls = Server.endpoints.get(endpoint)
                attempted_cls = self._get_parent(endpoint)
                    
                if attempted_cls:
                    arguments = (attempted_cls, payload_cls(request))
                else:
                    # CLient support
                    arguments = (payload_cls(request),)

                self.logger.debug(arguments)

                try:
                    response = await endpoint(*arguments)
                except Exception as error:
                    self.logger.error(
                        "Received error while executing %r with %r", endpoint, request,
                        exc_info=error
                    )
                    self.bot.dispatch("ipc_error", endpoint, error)

                    response = {
                        "error": str(error),
                        "code": 500,
                    }

        try:
            response = response or {} 
                
            if not response.get("code"):
                response["code"] = 200

            await websocket.send_json(response)
            self.logger.debug("Sending response: %r", response)
        except TypeError as error:
            if str(error).startswith("Object of type") and str(error).endswith("is not JSON serializable"):
                error_response = (
                    "IPC route returned values which are not able to be sent over sockets."
                    "If you are trying to send a discord.py object,"
                    "please only send the data you need."
                )

                self.bot.dispatch("ipc_error", endpoint, IPCError(error_response))

                response = {
                    "error": error_response, 
                    "code": 500
                }

                await websocket.send_json(response)
                self.logger.debug("Sending Response: %r", response)

                raise JSONEncodeError(error_response)
        except Exception:
            raise IPCError("Could not send JSON data to websocket!")

    async def setup(self, application: Application, port: int) -> None:
        """|coro|

        This function stats the IPC runner and the IPC webserver
        
        Parameters
        ----------
        application: :class:`aiohttp.web.Application`
            The internal router's app
        port: :int:`int`
            The specific port to run the application (:class:`~aiohttp.web.Application`)
        """
        self.logger.debug('Starting the IPC runner')
        self._runner = AppRunner(application)
        await self._runner.setup()

        self.logger.debug('Starting the IPC webserver')
        _webserver = TCPSite(self._runner, self.host, port)
        await _webserver.start()

    async def stop(self) -> None:
        """|coro|

        Stops both the IPC webserver
        """
        self.logger.info('Stopping up the IPC webserver')
        self.logger.debug(self._runner.addresses)
        await self._runner.shutdown()
        await self._runner.cleanup()

    async def wait_bot_is_ready(self) -> None:
        await self.bot.wait_until_ready()
        self.logger.info("The IPC server is ready")
        self.bot.dispatch("ipc_ready")
