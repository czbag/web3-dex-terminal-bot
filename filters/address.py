from typing import Dict, Union
from aiogram import types
from aiogram.filters import BaseFilter
from eth_utils.address import is_address, to_checksum_address


class AddressFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> dict | bool:
        if not is_address(message.text):
            return False
        
        return {
            "address": to_checksum_address(message.text),
        }

