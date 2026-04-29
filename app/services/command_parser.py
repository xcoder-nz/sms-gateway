import re


def parse_command(body: str) -> dict:
    text = body.strip()
    if text == "BAL":
        return {"cmd": "BAL"}
    if text == "HELP":
        return {"cmd": "HELP"}
    m = re.match(r"^PAY\s+(\S+)\s+(\d+)\s+PIN\s+(\S+)$", text)
    if m:
        return {"cmd": "PAY", "merchant_phone": m.group(1), "amount": int(m.group(2)), "pin": m.group(3)}
    m = re.match(r"^CASHIN\s+(\S+)\s+(\d+)$", text)
    if m:
        return {"cmd": "CASHIN", "buyer_phone": m.group(1), "amount": int(m.group(2))}
    m = re.match(r"^CASHOUT\s+(\S+)\s+(\d+)$", text)
    if m:
        return {"cmd": "CASHOUT", "buyer_phone": m.group(1), "amount": int(m.group(2))}
    raise ValueError("Invalid command")
