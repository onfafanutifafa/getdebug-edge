from decimal import Decimal

def add_vat(price_minor: int, rate: Decimal) -> int:
    if price_minor < 0:
        raise ValueError("price must be non-negative")
    return int(Decimal(price_minor) * (1 + rate))
