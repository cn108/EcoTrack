from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CO2E_QUANTUM = Decimal("0.000001")


def calculate_co2e(quantity: Decimal, factor: Decimal) -> Decimal:
    """Multiply exact decimal inputs and round to the database's six-place scale."""
    if not isinstance(quantity, Decimal) or not isinstance(factor, Decimal):
        raise TypeError("quantity and factor must be Decimal values")
    if not quantity.is_finite() or not factor.is_finite():
        raise ValueError("quantity and factor must be finite")
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    if factor < 0:
        raise ValueError("emission factor must not be negative")

    try:
        result = (quantity * factor).quantize(CO2E_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise ValueError("calculated CO2e is outside the supported precision") from error

    return Decimal("0.000000") if result.is_zero() else result