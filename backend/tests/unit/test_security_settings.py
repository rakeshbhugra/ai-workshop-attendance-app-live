import pytest

from attendance.config.settings import Settings
from attendance.main import create_app


@pytest.mark.parametrize(
    "overrides",
    [
        {"auth_dev_login": True},
        {"cookie_secure": False},
        {"session_secret": "dev-session-secret"},
        {"google_client_id": "google", "allowed_staff_emails": [], "allowed_email_domains": []},
    ],
)
def test_production_rejects_insecure_auth(overrides):
    values = {
        "environment": "prod",
        "auth_dev_login": False,
        "cookie_secure": True,
        "session_secret": "strong-production-test-secret",
        "google_client_id": "",
        "allowed_staff_emails": ["admin@example.com"],
    } | overrides
    with pytest.raises(RuntimeError):
        create_app(Settings(**values))
