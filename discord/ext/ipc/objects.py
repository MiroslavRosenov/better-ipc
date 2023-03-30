import json
import enum
from typing import Dict, Any, Optional, Union

class StatusEnum(enum.Enum):
    OK = 200
    FORBIDDEN = 403
    NOT_FOUND= 404
    INTERNAL_ERROR = 500
    
    def __str__(self) -> str:
        return str(self.value)

class ClientPayload:
    """
    The base class for the payload which is sent to the endpoint
    when the call is made. 
    
    This can be subclassed and custom payload
    can be used. If you do not Typehint the function with the custom
    payload then it will automatically use this base payload,
    but keys and values can be accessed like a dictionary or using `X.y`.

    Parameters:
    ----------
    payload: Dict`
        The payload to be converted.

    Attributes
    ----------
    length: `int`
        The length of the payload.
    endpoint: `str`
        The endpoint which was called.
    data: `Dict`
        The kwargs from the payload.
    """

    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.length: int = len(payload)
        self.endpoint: Optional[str] = payload.get("endpoint")
        self.data: Optional[Dict[str, Any]] = payload.get("kwargs")

    def __getitem__(self, __k: str):
        return self.data[__k] # type: ignore

    def __contains__(self, __o: object) -> bool:
        return __o in self.data or __o in self.data.values() # type: ignore

    def __getattribute__(self, __name: str) -> Any:
        try:
            return object.__getattribute__(self, __name)
        except AttributeError:
            try:
                return self.data[__name] # type: ignore
            except KeyError:
                raise AttributeError(__name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} length={self.length} endpoint={self.endpoint!r}>"

    @property
    def raw(self) -> Dict:
        return self.payload

    def items(self):
        """|method|

        Returns the payload in the form of dictionary items.
        """
        return self.payload.items()

class ServerResponse:
    """
    The class when getting response for the Server

    Parameters:
    ----------
    payload: `str`
        The payload to be converted.

    Attributes
    ----------
    response: `Dict | str`
        Decoded response that is ready for use..
    error: `Dict | None`
        Returns dict with exception information (if any).
    status: `StatusEnum`
        Raw status code converted to readable data.
    """
    def __init__(self, payload: str):
        self.data: Dict[str, Any] = json.loads(payload)
        self.decoding: str = self.data["decoding"]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} response={self.response} status={self.status.name}>"
    
    @property
    def response(self) -> Union[Dict, str]:
        """|property|
        
        Decoded response that is ready for use.

        """
        if self.decoding == "JSON":
            return json.loads(self.data["response"])
        return self.data["response"]

    @property
    def error(self) -> Optional[Dict[str, Any]]:
        """|property|

        Optionally returns any errors that from the server side.

        """
        if (error := self.data.get("error")):
            return {
                "error": error,
                "status": self.status,
                "details": self.data.get("error_details"),
            }

    @property
    def status(self) -> StatusEnum:
        """|property|
        
        The status code after being converted to `enum.Enum`

        """
        return StatusEnum(self.data.get("code"))
