def gas_price_check(gas_price: int) -> int:
    value = int(gas_price)

    if 5 <= int(gas_price) <= 1_000_000:
        return value
    
    raise ValueError


def gas_limit_check(gas_price: int) -> int:
    value = int(gas_price)

    if 1_000_000 <= int(gas_price) <= 30_000_000:
        return value
    
    raise ValueError


def slippage_check(slippage: float) -> float:
    if 0.1 <= float(slippage) <= 1000:
        return slippage
    
    raise ValueError


def price_impact_check(price_impact: float) -> float:
    if 0.1 <= float(price_impact) <= 100:
        return price_impact
    
    raise ValueError


def gas_delta_check(gas_delta: float) -> float:
    if 0.1 <= float(gas_delta) <= 1_000_000:
        return gas_delta
    
    raise ValueError
