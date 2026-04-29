import re

PHONE_PATTERN = re.compile(r"^\+?\d{10,15}$")


def normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Phone number must contain 10 to 15 digits")
    normalized = f"+{digits}"
    if not PHONE_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid phone number format")
    return normalized
