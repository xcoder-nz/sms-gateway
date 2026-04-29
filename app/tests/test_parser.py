from app.services.command_parser import parse_command


def test_parse_pay():
    cmd = parse_command("PAY 0799001100 120 PIN 1234")
    assert cmd["cmd"] == "PAY"
    assert cmd["amount"] == 120


def test_invalid():
    try:
        parse_command("NOPE")
        assert False
    except ValueError:
        assert True
