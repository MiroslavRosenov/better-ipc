import collections

from discord.ext.ipc.client import Client
from discord.ext.ipc.server import Server
from discord.ext.ipc.errors import *


_VersionInfo = collections.namedtuple("_VersionInfo", "major minor micro release serial")

version = "1.0.1"
version_info = _VersionInfo(1, 0, 0, "final", 0)
