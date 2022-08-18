from typing import Tuple

class IPCError(Exception):
    """Common base class for all IPC exceptions"""
    __slots__: Tuple[str, ...] = ()


class NoEndpointFoundError(IPCError):
    """Raised upon requesting an invalid endpoint"""
    pass


class ServerConnectionRefusedError(IPCError):
    """Raised upon a server refusing to connect / not being found"""
    pass


class JSONEncodeError(IPCError):
    """Raise upon un-serializable objects are given to the IPC"""
    pass


class NotConnected(IPCError):
    """Raised upon websocket not connected"""
    pass
