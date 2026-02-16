from networks.registery import NetworkRegistry
from networks.ethereum import ethereum, sepolia
from networks.base import base
from networks.bsc import bsc


registery = NetworkRegistry([ethereum, sepolia, base, bsc])
