import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LOAD_DEMO_FIXTURES"] = "false"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.config import settings  # noqa: E402

@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    old_token = settings.admin_api_token
    settings.admin_api_token = "test-secret-token"
    with TestClient(app, headers={"Authorization": "Bearer test-secret-token"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.admin_api_token = old_token
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
