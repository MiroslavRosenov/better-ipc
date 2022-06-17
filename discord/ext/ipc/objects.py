from typing import Dict, Any

class ServerRequest:
    def __init__(self, data: Dict[str, Any]):
        self._json = data
        self.length = len(data)
        self.endpoint = data["endpoint"]
        for key, value in data["data"].items():
            setattr(self, key, value)

    def to_json(self) -> Dict[str, Any]:
        return self._json

    def __repr__(self) -> str:
        return f"<ServerRequest length={self.length} endpoint={self.endpoint}>"
    
