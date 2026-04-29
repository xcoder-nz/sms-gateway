import pytest

from app.services.command_parser import parse_command


def test_parse_pay():
    cmd = parse_command("PAY 0799001100 120 PIN 1234")
    assert cmd == {"cmd": "PAY", "merchant_phone": "0799001100", "amount": 120, "pin": "1234"}


def test_parse_command_edge_cases():
    assert parse_command("  BAL  ") == {"cmd": "BAL"}
    assert parse_command("HELP") == {"cmd": "HELP"}
    assert parse_command("CASHIN 0700123456 10") == {"cmd": "CASHIN", "buyer_phone": "0700123456", "amount": 10}
    assert parse_command("CASHOUT 0700123456 10") == {"cmd": "CASHOUT", "buyer_phone": "0700123456", "amount": 10}


@pytest.mark.parametrize(
    "body",
    [
        "bal",
        "PAY 0799001100 -1 PIN 1234",
        "PAY 0799001100 12",
        "PAY 0799001100 1 PIN",
        "CASHIN 0700123456 -10",
        "NOPE",
    ],
)
def test_invalid(body: str):
    with pytest.raises(ValueError):
        parse_command(body)
