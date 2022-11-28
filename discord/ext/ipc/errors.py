from typing import Optional, Tuple

class BaseException(Exception):
    """Common base class for all exceptions"""
    __slots__: Tuple[str, ...] = ()
    details: Optional[str] = None

class NoEndpointFoundError(BaseException):
    """Raised when trying to request an unknown endpoint"""
    def __init__(self, name: str, *args: object) -> None:
        super().__init__(*args)
        self.name = name

class MulticastFailure(BaseException):
    """Raised when calling route that is not multicasted"""
    def __init__(self, name: str, *args: object) -> None:
        super().__init__(*args)
        self.name = name

class InvalidReturn(BaseException):
    """Raiseed when getting un-serializable objects as response from a route"""
    pass

class ServerAlreadyStarted(BaseException):
    """Raise trying to start already running server"""
    def __init__(self, name: str, *args: object) -> None:
        super().__init__(*args)
        self.name = name

