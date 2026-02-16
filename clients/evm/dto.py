from typing import Any
from dataclasses import dataclass


@dataclass
class TokenMeta:
    address: str
    name: str
    ticker: str
    decimals: int
    supply: int

@dataclass
class TraceResult:
    success: bool
    gas_used: int | None = None
    error_message: str | None = None
    raw_trace: dict[str, Any] | None = None
