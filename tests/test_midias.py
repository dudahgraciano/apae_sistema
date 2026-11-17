import io

import pytest

import routes.midias as midias
from utils.uploads import ErroUpload


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, *args, **kwargs):
        pass


class FakeDB:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def db_falso(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(midias, "get_db", lambda: db)
    monkeypatch.setattr(midias, "buscar_atividade", lambda cursor, id: {"id": id})
    monkeypatch.setattr(midias, "pode_alterar", lambda atividade: True)
    return db


def enviar(client, arquivos=1, autorizacao="1"):
    dados = {"arquivos": [(io.BytesIO(b"conteudo"), f"foto{i}.jpg") for i in range(arquivos)]}
    if autorizacao is not None:
        dados["autorizacao"] = autorizacao
    return client.post("/atividades/1/midias", data=dados,
                       content_type="multipart/form-data")


# ---------- Rotas protegidas (sem login) ----------

@pytest.mark.parametrize("url", ["/galeria", "/midias/1/arquivo",
                                 "/midias/1/miniatura", "/midias/1/baixar"])
def test_rotas_de_midia_exigem_login(client, url):
    resposta = client.get(url)
    assert resposta.status_code in (301, 302, 401, 403)


def test_envio_sem_login_e_bloqueado(client):
    resposta = enviar(client)
    assert resposta.status_code in (301, 302, 401, 403)


# ---------- Validações do envio ----------

def test_envio_exige_autorizacao_de_imagem(client_admin, db_falso):
    resposta = enviar(client_admin, autorizacao=None)
    assert resposta.status_code == 400
    assert "autorização" in resposta.get_json()["erro"]


def test_envio_sem_arquivos_retorna_400(client_admin, db_falso):
    resposta = client_admin.post("/atividades/1/midias", data={"autorizacao": "1"},
                                 content_type="multipart/form-data")
    assert resposta.status_code == 400
    assert "ao menos um arquivo" in resposta.get_json()["erro"]


def test_envio_acima_do_limite_de_arquivos(client_admin, db_falso):
    resposta = enviar(client_admin, arquivos=midias.MAX_ARQUIVOS_POR_ENVIO + 1)
    assert resposta.status_code == 400
    assert "no máximo" in resposta.get_json()["erro"]


def test_atividade_inexistente_retorna_404(client_admin, db_falso, monkeypatch):
    monkeypatch.setattr(midias, "buscar_atividade", lambda cursor, id: None)
    assert enviar(client_admin).status_code == 404


def test_usuario_sem_permissao_na_atividade_retorna_403(client_admin, db_falso, monkeypatch):
    monkeypatch.setattr(midias, "pode_alterar", lambda atividade: False)
    assert enviar(client_admin).status_code == 403


# ---------- Resultado do processamento ----------

def test_arquivo_rejeitado_aparece_nas_falhas(client_admin, db_falso, monkeypatch):
    def recusar(arquivo, config):
        raise ErroUpload("formato não permitido")

    monkeypatch.setattr(midias, "processar_arquivo", recusar)
    resposta = enviar(client_admin)
    corpo = resposta.get_json()
    assert resposta.status_code == 400
    assert corpo["enviados"] == []
    assert corpo["falhas"][0]["motivo"] == "formato não permitido"


def test_erro_inesperado_nao_expoe_detalhes(client_admin, db_falso, monkeypatch):
    def quebrar(arquivo, config):
        raise RuntimeError("detalhe interno secreto")

    monkeypatch.setattr(midias, "processar_arquivo", quebrar)
    resposta = enviar(client_admin)
    assert "secreto" not in resposta.get_data(as_text=True)
    assert resposta.status_code == 400


def test_envio_valido_registra_e_confirma_no_banco(client_admin, db_falso, monkeypatch):
    monkeypatch.setattr(midias, "processar_arquivo", lambda arquivo, config: {
        "nome_original": "foto0.jpg", "nome_arquivo": "abc123.jpg",
        "tipo": "foto", "mime_type": "image/jpeg", "tamanho_bytes": 8,
    })
    resposta = enviar(client_admin)
    corpo = resposta.get_json()
    assert resposta.status_code == 200
    assert corpo["enviados"] == ["foto0.jpg"]
    assert corpo["falhas"] == []
    assert db_falso.commits == 1


def test_falha_no_banco_faz_rollback_e_apaga_arquivo(client_admin, db_falso, monkeypatch):
    apagados = []
    monkeypatch.setattr(midias, "processar_arquivo", lambda arquivo, config: {
        "nome_original": "foto0.jpg", "nome_arquivo": "abc123.jpg",
        "tipo": "foto", "mime_type": "image/jpeg", "tamanho_bytes": 8,
    })
    monkeypatch.setattr(midias, "apagar_arquivos",
                        lambda config, nomes: apagados.extend(nomes))

    def falhar_commit():
        raise RuntimeError("banco fora do ar")

    db_falso.commit = falhar_commit
    resposta = enviar(client_admin)
    assert resposta.status_code == 400
    assert db_falso.rollbacks == 1
    assert apagados == ["abc123.jpg"]