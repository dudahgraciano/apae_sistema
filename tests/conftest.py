import pytest

from app import criar_app


@pytest.fixture
def app():
    app = criar_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def client_admin(app):
    """Cliente já 'logado' como administrador."""
    client = app.test_client()
    with client.session_transaction() as sessao:
        sessao["usuario_id"] = 1
        sessao["perfil"] = "administrador"
    return client