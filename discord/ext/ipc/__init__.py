"""
Better IPC
~~~~~~
A high-performance inter-process communication 
library designed to work with the latest version of discord.py
:license: Apache License 2.0
"""

try:
    import discord
except ImportError:
    raise RuntimeError("You must have discord.py installed!")
else:
    if not discord.__version__.startswith("2.0"):
        raise RuntimeError(
            "You must have discord.py 2.0 installed in order for Better IPC to work!"
        )


__version__ = "1.0.8"
__title__ = "better-ipc"
__author__ = "DaPandaOfficial"

from discord.ext.ipc.client import Client
from discord.ext.ipc.server import Server
from discord.ext.ipc.errors import *
