from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app, pwd
from app.seed.demo_seed import seed_for_session


@pytest.fixture(autouse=True)
def stub_pin_verify():
    original_verify = pwd.verify
    pwd.verify = lambda plain, stored: plain == stored
    try:
        yield
    finally:
        pwd.verify = original_verify


@pytest.fixture()
def db_session(tmp_path) -> Generator:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_for_session(db, reset=True, pin_hasher=lambda value: value)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: sessionmaker) -> Generator:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
