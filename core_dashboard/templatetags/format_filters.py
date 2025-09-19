from django import template
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

register = template.Library()


@register.filter
def format_number(value):
    """Format a numeric value as integer with thousands separator and no decimals.

    Behavior:
    - None -> '0'
    - Numeric (int/float/Decimal or numeric string) -> rounded to nearest integer (ROUND_HALF_UP) and formatted with comma thousands separator
    - Non-numeric -> returned unchanged
    """
    try:
        if value is None:
            return '0'

        # If it's already an int, format directly
        if isinstance(value, int):
            return f"{value:,}"

        # Convert to Decimal for accurate rounding
        if isinstance(value, Decimal):
            d = value
        else:
            # Accept numeric strings like '12345.67'
            d = Decimal(str(value))

        # Round to nearest integer using ROUND_HALF_UP
        rounded = int(d.to_integral_value(rounding=ROUND_HALF_UP))
        return f"{rounded:,}"
    except (InvalidOperation, ValueError, TypeError):
        # If we can't parse it, return as-is to avoid hiding data
        return value
