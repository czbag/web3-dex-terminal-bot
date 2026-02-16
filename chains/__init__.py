from chains.registery import ChainRegistry
from chains.ethereum import ethereum
from chains.base import base
from chains.bsc import bsc


registery = ChainRegistry([ethereum, base, bsc])
