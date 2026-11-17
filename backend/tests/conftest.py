"""
tests/conftest.py — Shared pytest fixtures.

Provides:
  • app     — Flask test app with SQLite in-memory DB
  • client  — Flask test client
  • seeded_user — a User with predictable avg_amount and home city
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import time

# Force in-memory SQLite and disable Redis for tests
os.environ["DATABASE_URL"] = ""   # → SQLite fallback
os.environ["REDIS_URL"]    = ""   # → in-memory dict fallback


@pytest.fixture(scope="session")
def app():
    from app import create_app
    _app = create_app()
    _app.config["TESTING"] = True
    _app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with _app.app_context():
        from models import db
        db.create_all()
        # Seed minimal test data
        from seed import seed_users
        seed_users()
    yield _app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def ctx(app):
    """Push an application context for tests that need db access."""
    with app.app_context():
        yield


@pytest.fixture()
def bengaluru_user(app):
    """Return the first user whose home city is Bengaluru."""
    with app.app_context():
        from models import User
        user = User.query.filter_by(home_city="Bengaluru").first()
        assert user is not None, "Seed data must include a Bengaluru user"
        return user.to_dict()   # dict so it survives outside the context


@pytest.fixture()
def default_rule_config(app):
    from config import Config
    return Config.RULE_CONFIG
