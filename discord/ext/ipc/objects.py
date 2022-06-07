from typing import Dict

class ServerRequest:
    def __init__(self, data: Dict):
        self._json = data
        self.length = len(data)
        self.endpoint = data["endpoint"]
        for key, value in data["data"].items():
            setattr(self, key, value)

    def to_json(self):
        return self._json

    def __repr__(self):
        return f"<ServerRequest length={self.length} endpoint={self.endpoint}>"

    def __str__(self):
        return self.__repr__()