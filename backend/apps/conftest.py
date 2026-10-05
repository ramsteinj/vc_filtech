import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

PASSWORD = "Str0ng-pass!23"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin2", password=PASSWORD, role=User.Role.ADMIN, display_name="관리자2"
    )


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        username="manager", password=PASSWORD, role=User.Role.BID_MANAGER, display_name="담당자"
    )


def _client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    return _client_for(admin_user)


@pytest.fixture
def manager_client(manager_user):
    return _client_for(manager_user)
