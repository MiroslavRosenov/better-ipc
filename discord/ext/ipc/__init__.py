"""
Better IPC
~~~~~~
A high-performance inter-process communication 
library designed to work with the latest version of discord.py
:license: Apache License 2.0
"""

__version__ = "1.0.2"
__title__ = "better-ipc"
__author__ = "DaPandaOfficial"

from discord.ext.ipc.client import Client
from discord.ext.ipc.server import Server
from discord.ext.ipc.errors import *