import os

# Configure the application before it is imported. Tests use a self-contained
# in-memory SQLite database; the real application still uses PostgreSQL.
os.environ["KEVIN_SECRET_KEY"] = "test-secret-key-for-tests-only"
os.environ["KEVIN_DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

import kevin.models  # noqa: E402,F401  # Register all SQLModel tables.


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
