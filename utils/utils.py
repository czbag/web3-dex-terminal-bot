from decimal import Decimal


def smart_round(x: int | float) -> int | float:
    return int(x) if x.is_integer() else x


def convert_price(value: Decimal, price: Decimal):
    if value == 0:
        return Decimal("0")

    price_converted = value * price

    if price_converted < Decimal("0.001"):
        return "&lt;0.001"

    if price_converted >= 10000:
        return "{:,.0f}".format(price_converted)

    return f"{price_converted:.3f}".rstrip("0").rstrip(".")

def format_amount(value: Decimal) -> str:
    if value == 0:
        return "0"
    
    if value < Decimal("0.0001"):
        return "&lt;0.0001"
    
    if value > Decimal("1"):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    
    return f"{value:.4f}".rstrip("0").rstrip(".")

