from typing import Dict, Any, TypeVar

PT = TypeVar("PT")


class ServerPayload:
    """|class|

    The base class for the payload which is sent to the endpoint
    when the call is made. This can be subclassed and custom payload
    can be used. If you do not Typehint the function with the custom
    payload then it will automatically use this base payload,
    but keys and values can be accessed like a dictionary or using `X.y`.

    Attributes
    ----------
    `lenght`: :class:`int`
        The lenght of the payload.

    `endpoint`: :class:`str`
        The endpoint which was called.
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.lenght = len(data)
        self.endpoint = data["endpoint"]

    def __getitem__(self, __k: str):
        return self._data[__k]

    def __contains__(self, __o: object) -> bool:
        return __o in self._data or __o in self._data.values()

    def __getattribute__(self, __name: str) -> Any:
        try:
            return object.__getattribute__(self, __name)
        except AttributeError:
            return object.__getattribute__(self, "_data")[__name]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(lenght={self.lenght} endpoint='{self.endpoint}')"

    @property
    def data(self):
        return self._data

    def items(self):
        """|method|

        Returns the payload in the form of dictionary items.
        """
        return self._data.items()
