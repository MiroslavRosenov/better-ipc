"""
Better IPC
~~~~~~~~~~

High-performance inter-process communication 
library designed to work with the latest version of discord.py

:copyright: (C) 2022 DaPandaOfficial
:license: GNU GENERAL PUBLIC LICENSE
"""
import discord

if discord.version_info.major < 2:
    raise RuntimeError("You must have discord.py (v2.0 or greater) to use this library.")

__title__ = "better-ipc"
__author__ = "DaPandaOfficial"
__license__ = "GNU GENERAL PUBLIC LICENSE"
__copyright__ = "Copyright (C) 2022 DaPandaOfficial"
__version__ = "2.0.1"


from .errors import BaseException, NoEndpointFoundError, MulticastFailure, InvalidReturn, ServerAlreadyStarted
from .client import Client
from .server import Server
from .objects import ClientPayload, ServerResponse


