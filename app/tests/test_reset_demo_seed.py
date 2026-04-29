from app.models import User, Wallet
from app.seed.demo_seed import seed_for_session


def test_reset_demo_reseeds_deterministically(db_session):
    users_before = db_session.query(User).order_by(User.phone_number).all()
    balances_before = {w.user_id: float(w.balance) for w in db_session.query(Wallet).all()}

    seed_for_session(db_session, reset=True, pin_hasher=lambda value: value)

    users_after = db_session.query(User).order_by(User.phone_number).all()
    balances_after = {w.user_id: float(w.balance) for w in db_session.query(Wallet).all()}

    assert [u.phone_number for u in users_before] == [u.phone_number for u in users_after]
    assert sorted([u.role for u in users_after]) == ["agent", "buyer", "merchant"]
    assert sorted(balances_after.values()) == [0.0, 0.0, 1000.0]
    assert sorted(balances_before.values()) == sorted(balances_after.values())
