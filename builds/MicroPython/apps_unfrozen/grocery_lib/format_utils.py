from grocery_lib.config import get_config
from grocery_lib.ui_utils import EURO_SYMBOL

def format_price(amount, sep=None):
    """Formats a float to string using global decimal separator and currency symbol."""
    if sep is None:
        sep = get_config("decimal_separator")
    currency = get_config("currency")
    symbol = EURO_SYMBOL if currency == "euro" else "$"
    
    formatted = "{:.2f}".format(amount).replace(".", sep)
    if currency == "euro":
        return formatted + " " + symbol
    return symbol + formatted

def parse_price(price_str):
    """Parses a string (with . or ,) back to float."""
    try:
        s = price_str.replace(",", ".")
        if not s: return 0.0
        return float(s)
    except Exception:
        return 0.0

def get_tax_info():
    """Returns tax multiplier/label based on region."""
    region = get_config("tax_region")
    if region == "US":
        return 0.07, "Sales Tax" # Example average
    else:
        return 0.19, "MwSt" # Germany standard
